from collections import Counter
from datetime import timedelta as td
from itertools import tee
import re
import json
from uuid import uuid4
from django.core.validators import validate_email

import requests
import github
from github import Github
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.six.moves.urllib.parse import urlencode
from hc.api.decorators import uuid_or_400
from hc.api.models import DEFAULT_GRACE, DEFAULT_TIMEOUT, Channel, Check, Ping, Blog, BlogCategories
from hc.accounts.models import Member, Department
from hc.api.models import Platforms
from hc.front.forms import (AddChannelForm, AddWebhookForm, NameTagsForm, EscalationForm, PriorityForm,
                            TimeoutForm, AddGitWebhookForm, BlogForm, BlogCategoriesForm,
                            EmailTaskForm, BackupTaskForm)
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from hc.lib import emails
from hc.front.backup import checks_summary, check_log

# from itertools recipes:
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

@login_required
def my_checks(request):
    q = Check.objects.filter(user=request.team.user).order_by("priority").reverse()
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if dept != None:
            q = q.filter(department=dept)
    checks = list(q)
 
    if request.team == request.user.profile:
        owner = Check.objects.filter(user=request.team.user).order_by("created")
        checks = list(owner)
    else:
        member_checks = Check.objects.filter(user=request.team.user, 
                        membership_access=True, member_id=request.user.id).\
                            order_by("created")    
        checks = list(member_checks)

    counter = Counter()
    down_tags, grace_tags = set(), set()
    for check in checks:
        status = check.get_status()
        for tag in check.tags_list():
            if tag == "":
                continue

            counter[tag] += 1

            if status == "down":
                down_tags.add(tag)
            elif check.in_grace_period():
                grace_tags.add(tag)

    ctx = {
        "page": "checks",
        "checks": checks,
        "now": timezone.now(),
        "department": dept,
        "tags": counter.most_common(),
        "down_tags": down_tags,
        "grace_tags": grace_tags,
        "ping_endpoint": settings.PING_ENDPOINT
    }

    return render(request, "front/my_checks.html", ctx)


def _welcome_check(request):
    check = None
    if "welcome_code" in request.session:
        code = request.session["welcome_code"]
        check = Check.objects.filter(code=code).first()

    if check is None:
        check = Check()
        check.save()
        request.session["welcome_code"] = str(check.code)

    return check


def index(request):
    if request.user.is_authenticated:
        return redirect("hc-checks")

    check = _welcome_check(request)

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url(),
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None
    }

    return render(request, "front/welcome.html", ctx)


def docs(request):
    check = _welcome_check(request)

    ctx = {
        "page": "docs",
        "section": "home",
        "ping_endpoint": settings.PING_ENDPOINT,
        "check": check,
        "ping_url": check.url()
    }

    return render(request, "front/docs.html", ctx)


def docs_api(request):
    ctx = {
        "page": "docs",
        "section": "api",
        "SITE_ROOT": settings.SITE_ROOT,
        "PING_ENDPOINT": settings.PING_ENDPOINT,
        "default_timeout": int(DEFAULT_TIMEOUT.total_seconds()),
        "default_grace": int(DEFAULT_GRACE.total_seconds())
    }

    return render(request, "front/docs_api.html", ctx)


def about(request):
    return render(request, "front/about.html", {"page": "about"})

def tasks(request):
    q = Check.objects.filter(user=request.team.user).order_by("priority").reverse()
    checks = list(q)
    ctx = {
        "checks":checks
    }
    return render(request, "front/tasks.html",  ctx)

def faq(request):
    return render(request, "front/faq.html", {"page": "faq"})


@login_required
def add_check(request):
    assert request.method == "POST"
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
    check = Check(user=request.team.user, department=dept)
    check.save()

    check.assign_all_channels()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def update_name(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if check.department != dept:
            return HttpResponseForbidden()
    
    if (check.user_id != request.team.user.id):
        return HttpResponseForbidden()
    
    form = NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.tags = form.cleaned_data["tags"]
        check.save()

    return redirect("hc-checks")

@login_required
def send_email(request):
    assert request.method == "POST"

    profile = request.user.profile
    form = EmailTaskForm(request.POST)
    if form.is_valid():
        recipient = form.cleaned_data['recipient_email']
        subject = form.cleaned_data['email_subject']
        body= form.cleaned_data['email_body']
        ctx = {
            "username": profile.user.username,
            "email": profile.user.email,
            "subject":subject,
            "body":body
        }
        emails.send_task(recipient, ctx)

        messages.success(request, "Email sent")

    return redirect("hc-tasks")

@login_required
def backup(request):
    assert request.method == "POST"

    profile = request.user.profile
    checks = Check.objects.filter(user=profile.user)
    form = BackupTaskForm(request.POST)
    if form.is_valid():
        fileName = form.cleaned_data['file_name']
        check_name = form.cleaned_data['check_name']
        if check_name == "All Checks":
            return checks_summary(request, fileName, checks)
        check = get_object_or_404(Check, name=check_name)
        pings = Ping.objects.filter(owner=check).order_by("-id")
        return check_log(request, fileName, pings)

    return redirect("hc-tasks")


@login_required
@uuid_or_400
def update_priority(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    form = PriorityForm(request.POST)
    if form.is_valid():
        check.priority = form.cleaned_data["priority"]
        # check.tags = form.cleaned_data["tags"]
        check.save()

    return redirect("hc-checks")

@login_required
@uuid_or_400
def update_escalation(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    form = EscalationForm(request.POST)

    if form.is_valid():
        e_list = form.cleaned_data["escalation_list"]

        SEPARATOR_RE = re.compile(r'[;]+')
        emails = SEPARATOR_RE.split(e_list)
        valid_emails = list()
        for email in emails:
            try:
                validate_email(email)
                valid_emails.append(email)
            except:
                messages.warning(request, "Invalid Email, kindly fill in a valid email format i.e kzy@gmail.com and seperate each email by a semicollon")
        check.escalation_list = ';'.join(map(str, valid_emails))
        check.escalation_interval = td(seconds=form.cleaned_data["escalation_interval"])
        check.save()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def update_timeout(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if check.department != dept:
            return HttpResponseForbidden()
    
    if (check.user_id != request.team.user.id):
        return HttpResponseForbidden()

    form = TimeoutForm(request.POST)
    if form.is_valid():
        check.timeout = td(seconds=form.cleaned_data["timeout"])
        check.grace = td(seconds=form.cleaned_data["grace"])
        check.nag = td(seconds=form.cleaned_data["nag"])
        check.save()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def pause(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if check.department != dept:
            return HttpResponseForbidden()
    
    if (check.user_id != request.team.user.id):
        return HttpResponseForbidden()

    check.status = "paused"
    check.save()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def remove_check(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if check.department != dept:
            return HttpResponseForbidden()
    
    if (check.user_id != request.team.user.id):
        return HttpResponseForbidden()

    check.delete()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def log(request, code):
    check = get_object_or_404(Check, code=code)
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if check.department != dept:
            return HttpResponseForbidden()

    if (check.user_id != request.team.user.id):
        return HttpResponseForbidden()

    limit = request.team.ping_log_limit
    pings = Ping.objects.filter(owner=check).order_by("-id")[:limit]

    pings = list(pings.iterator())
    # oldest-to-newest order will be more convenient for adding
    # "not received" placeholders:
    pings.reverse()

    # Add a dummy ping object at the end. We iterate over *pairs* of pings
    # and don't want to handle a special case of a check with a single ping.
    pings.append(Ping(created=timezone.now()))

    # Now go throuGithub pings, calculate time gaps, and decorate
    # the pings list for convenient use in template
    wrapped = []

    early = False
    for older, newer in pairwise(pings):
        wrapped.append({"ping": older, "early": early})

        # Fill in "missed ping" placeholders:
        expected_date = older.created + check.timeout
        n_blanks = 0
        while expected_date + check.grace < newer.created and n_blanks < 10:
            wrapped.append({"placeholder_date": expected_date})
            expected_date = expected_date + check.timeout
            n_blanks += 1

        # Prepare early flag for next ping to come
        early = older.created + check.timeout > newer.created + check.grace

    reached_limit = len(pings) > limit

    wrapped.reverse()
    ctx = {
        "check": check,
        "pings": wrapped,
        "num_pings": len(pings),
        "limit": limit,
        "show_limit_notice": reached_limit and settings.USE_PAYMENTS
    }

    return render(request, "front/log.html", ctx)


@login_required
def channels(request):
    if request.method == "POST":
        code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.user_id != request.team.user.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.user_id != request.team.user.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks = new_checks
        return redirect("hc-channels")

    channels = Channel.objects.filter(user=request.team.user).order_by("created")
    channels = channels.annotate(n_checks=Count("checks"))

    num_checks = Check.objects.filter(user=request.team.user).count()

    ctx = {
        "page": "channels",
        "channels": channels,
        "num_checks": num_checks,
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None
    }
    return render(request, "front/channels.html", ctx)


def do_add_channel(request, data):
    form = AddChannelForm(data)
    if form.is_valid():
        channel = form.save(commit=False)
        channel.user = request.team.user
        channel.save()

        channel.assign_all_checks()

        if channel.kind == "email":
            channel.send_verify_link()

        return redirect("hc-channels")
    else:
        return HttpResponseBadRequest()


@login_required
def add_channel(request):
    assert request.method == "POST"
    return do_add_channel(request, request.POST)


@login_required
@uuid_or_400
def channel_checks(request, code):
    channel = get_object_or_404(Channel, code=code)
    if channel.user_id != request.team.user.id:
        return HttpResponseForbidden()

    assigned = set(channel.checks.values_list('code', flat=True).distinct())
    checks = Check.objects.filter(user=request.team.user).order_by("created")

    ctx = {
        "checks": checks,
        "assigned": assigned,
        "channel": channel
    }

    return render(request, "front/channel_checks.html", ctx)


@uuid_or_400
def verify_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@login_required
@uuid_or_400
def remove_channel(request, code):
    assert request.method == "POST"

    # user may refresh the page during POST and cause two deletion attempts
    channel = Channel.objects.filter(code=code).first()
    if channel:
        if channel.user != request.team.user:
            return HttpResponseForbidden()
        channel.delete()

    return redirect("hc-channels")


@login_required
def add_email(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_email.html", ctx)


@login_required
def add_webhook(request):
    if request.method == "POST":
        form = AddWebhookForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="webhook")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddWebhookForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_webhook.html", ctx)


@login_required
def add_pd(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pd.html", ctx)


def add_slack(request):
    if not settings.SLACK_CLIENT_ID and not request.user.is_authenticated:
        return redirect("hc-login")

    ctx = {
        "page": "channels",
        "slack_client_id": settings.SLACK_CLIENT_ID
    }
    return render(request, "integrations/add_slack.html", ctx)


@login_required
def add_slack_btn(request):
    code = request.GET.get("code", "")
    if len(code) < 8:
        return HttpResponseBadRequest()

    result = requests.post("https://slack.com/api/oauth.access", {
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "code": code
    })

    doc = result.json()
    if doc.get("ok"):
        channel = Channel()
        channel.user = request.team.user
        channel.kind = "slack"
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Slack integration has been added!")
    else:
        s = doc.get("error")
        messages.warning(request, "Error message from slack: %s" % s)

    return redirect("hc-channels")


@login_required
def add_hipchat(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_hipchat.html", ctx)


@login_required
def add_pushbullet(request):
    if settings.PUSHBULLET_CLIENT_ID is None:
        raise Http404("pushbullet integration is not available")

    if "code" in request.GET:
        code = request.GET.get("code", "")
        if len(code) < 8:
            return HttpResponseBadRequest()

        result = requests.post("https://api.pushbullet.com/oauth2/token", {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "client_secret": settings.PUSHBULLET_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        })

        doc = result.json()
        if "access_token" in doc:
            channel = Channel(kind="pushbullet")
            channel.user = request.team.user
            channel.value = doc["access_token"]
            channel.save()
            channel.assign_all_checks()
            messages.success(request,
                             "The Pushbullet integration has been added!")
        else:
            messages.debug(request, "Something went wrong")

        return redirect("hc-channels")

    redirect_uri = settings.SITE_ROOT + reverse("hc-add-pushbullet")
    authorize_url = "https://www.pushbullet.com/authorize?" + urlencode({
        "client_id": settings.PUSHBULLET_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code"
    })

    ctx = {
        "page": "channels",
        "authorize_url": authorize_url
    }
    return render(request, "integrations/add_pushbullet.html", ctx)


@login_required
def add_pushover(request):
    if settings.PUSHOVER_API_TOKEN is None or settings.PUSHOVER_SUBSCRIPTION_URL is None:
        raise Http404("pushover integration is not available")

    if request.method == "POST":
        # Initiate the subscription
        nonce = get_random_string()
        request.session["po_nonce"] = nonce

        failure_url = settings.SITE_ROOT + reverse("hc-channels")
        success_url = settings.SITE_ROOT + reverse("hc-add-pushover") + "?" + urlencode({
            "nonce": nonce,
            "prio": request.POST.get("po_priority", "0"),
        })
        subscription_url = settings.PUSHOVER_SUBSCRIPTION_URL + "?" + urlencode({
            "success": success_url,
            "failure": failure_url,
        })

        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        if "nonce" not in request.GET or "prio" not in request.GET:
            return HttpResponseBadRequest()

        # Validate nonce
        if request.GET["nonce"] != request.session.get("po_nonce"):
            return HttpResponseForbidden()

        # Validate priority
        if request.GET["prio"] not in ("-2", "-1", "0", "1", "2"):
            return HttpResponseBadRequest()

        # All looks well--
        del request.session["po_nonce"]

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this user
            Channel.objects.filter(user=request.user, kind="po").delete()
            return redirect("hc-channels")
        else:
            # Subscription
            user_key = request.GET["pushover_user_key"]
            priority = int(request.GET["prio"])

            return do_add_channel(request, {
                "kind": "po",
                "value": "%s|%d" % (user_key, priority),
            })

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "integrations/add_pushover.html", ctx)


@login_required
def add_victorops(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_victorops.html", ctx)


def privacy(request):
    return render(request, "front/privacy.html", {})


def terms(request):
    return render(request, "front/terms.html", {})

@login_required
def unresolved_issues(request):
    ''' Handle unresolved issues '''
    assert request.method == "GET"
    q = Check.objects.filter(user=request.team.user).order_by("created")
    dept=None
    if request.team.user.id != request.user.id:
        member = Member.objects.get(team=request.team,user=request.user)
        dept =  member.department
        if dept != None:
            q = q.filter(department=dept)

    checks = [ check for check in q if check.get_status() is "down"]
    

    ctx = {
        "page": "issues",
        "checks": checks,
        "department": dept,
        "ping_endpoint": settings.PING_ENDPOINT,
    }
    return render(request, "front/issues.html", ctx)

@login_required
def checks_platforms(request):
    ''' Third party programs '''
    assert request.method == "GET"
    user = request.team.user
    try:
        api = Platforms.objects.get(name="github", user=user)
        if api.granted:
            repos = api.entities or list()
            github_integration = True
        else:
            repos = list()
            github_integration = False
    except Platforms.DoesNotExist:
        repos = list()
        github_integration = False
    ctx = {
        "page": "third-party-checks",
        "repos": repos,
        "github": github_integration,
    }
    return render(request, "front/platforms_checks.html", ctx)

@login_required
def check_github(request):
    ''' Third party programs '''
    assert request.method == "GET"
    user = request.team.user
    link = 'https://github.com/login/oauth/authorize?client_id={}&redirect_uri&scope=repo,write:repo_hook&state={}'
    client_id = settings.GITHUB_OAUTH_APP_ID
    client_secret = settings.GITHUB_OAUTH_APP_SECRET
    state_code = uuid4().hex
    code = request.GET.get("code")
    state = request.GET.get("state")
    if code and state and len(code) > 2 and len(code) > 2:
        try:
            api = Platforms.objects.get(name="github", user=user, state=state)
            redirect_uri = '{}/checks/platforms/github/'.format(settings.SITE_ROOT)
            print(redirect_uri)
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'state': state,
            }
            try:
                r = requests.post("https://github.com/login/oauth/access_token",
                                 data=payload, headers={'Accept': 'application/json'})
                response = r.json()
                print(r.json())
                if r.status_code == 200 and 'access_token' in response:
                    print(r.json())
                    api.code = code
                    api.access_token = response['access_token']
                    api.token_type = response['token_type']
                    api.scopes = response['scope']
                    api.granted = True
                    print(api.access_token)
                    api.save()
                return redirect('hc-platforms')
            except requests.HTTPError:
                pass
            api.code = code
            api.save()
        except Platforms.DoesNotExist:
            return HttpResponseBadRequest()
    try:
        api = Platforms.objects.get(name="github", user=user)
        api.state = state_code
    except Platforms.DoesNotExist:
        api = Platforms(name='github', state=state_code, user=user)
        
    api.save()

    link = link.format(client_id, state_code)
    return redirect(link)

@login_required
def create_github_webhook(request):
    ''' Create a github webhook '''
    assert request.method == "POST"
    user = request.team.user
    form = AddGitWebhookForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()
    try:
        api = Platforms.objects.get(name="github", user=user)
        if api.granted:
            try:
                g = Github(api.access_token)
                repos = g.get_user().get_repos()
                github_integration = True
                dept=None
                if request.team.user.id != request.user.id:
                    member = Member.objects.get(team=request.team,user=request.user)
                    dept =  member.department
                repo_name = form.cleaned_data["repo_name"]
                check_repo_name = 'Github-{}'.format(repo_name)
                check = Check(name=check_repo_name, user=request.team.user, department=dept)
                check.save()
                check.assign_all_channels()

                user_repo = g.get_user().get_repo(repo_name)
                ping_url = settings.PING_ENDPOINT+str(check.code)
                user_repo.create_hook("web", {"url": ping_url})
                all_entities = api.entities or list()
                all_entities.append(repo_name)
                api.entities = all_entities
                api.save()
            except github.GithubException as e:
                print(e)
                pass
    except Platforms.DoesNotExist:
        return HttpResponseBadRequest()
    return redirect('hc-platforms')

@login_required
def github_repos(request):
    ''' Return repositories'''
    user = request.team.user
    try:
        api = Platforms.objects.get(name="github", user=user)
        if api.granted:
            try:
                g = Github(api.access_token)
                repos = g.get_user().get_repos()
                github_integration = True
            except github.GithubException as e:
                print(e)
                api.granted = False
                api.access_token = None
                api.code = None
                api.save()
                repos = list()
                github_integration = False
        else:
            repos = list()
            github_integration = False
    except Platforms.DoesNotExist:
        repos = list()
        github_integration = False
    repositories = list()
    entities = api.entities or list()
    for repo in repos:
        if repo.name in entities:
            continue
        else:
            repositories.append(repo.name)
    response = {
        "repos": repositories,
        "github": github_integration,
    }

    return HttpResponse(json.dumps(response), content_type="application/json")

def blog(request):

    blog = Blog.objects.order_by("-created").all()
    blogs = list(blog)
    ctx = {
        "blogs": blogs
    }
    return render(request, "front/blog.html", ctx)

def add_blog(request):
    cat =  BlogCategories.objects.all()
    categories = list(cat)
    return render(request, "front/add_blog.html", {"categories": categories})


@login_required
def create_blogpost(request):
    user=request.team.user.id

    form = BlogForm(request.POST)

    if form.is_valid():
        title = form.cleaned_data["title"]
        category = form.cleaned_data["category"]
        content = form.cleaned_data["content"]

        blog = Blog(title=title, category=category, content=content)

        try:
            blog.save()
            messages.info(request, "Blogpost published successfully")
        except:
            messages.warning(request, "Blogpost not published, kindly try again")

    return redirect("hc-add-blog")

@login_required
def add_category(request):
    user=request.team.user.id

    form = BlogCategoriesForm(request.POST)

    if form.is_valid():
        category = form.cleaned_data["category"]

        cat = [c for c in BlogCategories.objects.all() if c.category.lower()==category.lower()]

        if cat:
            messages.warning(request, "That category already exists.")
        else:

            blogcategory = BlogCategories(category=category)

            try:
                blogcategory.save()
                messages.info(request, "Category added successfully")
            except:
                messages.warning(request, "Category not added, kindly try again")

    return redirect("hc-add-blog")

def read_blogpost(request, id):
    blog = Blog.objects.get(id=int(id))
    return render(request, "front/read_blog.html", {'blog': blog, 'siteroot': settings.SITE_ROOT, 'msg':'Read more about the blog:' })

@login_required
def remove_blogpost(request, id):
    blog = Blog.objects.get(id=int(id))
   
    try:
        blog.delete()
        messages.info(request, "Blogpost deleted successfully")
    except:
        messages.warning(request, "Blogpost not deleted, kindly try again")

    return redirect("hc-blog")

@login_required
def edit_blogpost(request, id):
    user=request.team.user.id
    blog = Blog.objects.get(id=int(id))
    categories = BlogCategories.objects.all()

    if request.method == "GET":
        form = BlogForm()
        return render(request, "front/edit_blog.html", {'blog': blog, 'form': form, 'categories':categories})

    elif request.method == "POST":
        form = BlogForm(request.POST)
        if form.is_valid():
            blog.title = form.cleaned_data['title']
            blog.category = form.cleaned_data['category']
            blog.content = form.cleaned_data['content']

            try:
                blog.save()
                messages.success(request, "Blogpost edited successfully")
                return render(request, "front/read_blog.html", {'blog': blog})
            except:
                messages.warning(request, "Blogpost not edited, kindly try again")
                return redirect("hc-blog")

    return render(request, "front/edit_blog.html", {'blog': blog, 'form': form, 'categories':categories})
