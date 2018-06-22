from django.conf import settings
from djmail.template_mail import InlineCSSTemplateMail
from hc.lib.sms import send_sms
from django.contrib.auth.models import User


def send(name, to, ctx):
    o = InlineCSSTemplateMail(name)
    ctx["SITE_ROOT"] = settings.SITE_ROOT
    o.send(to, ctx)


def login(to, ctx):
    send("login", to, ctx)


def set_password(to, ctx):
    send("set-password", to, ctx)

def escalate(to, ctx):
    send("escalation", to, ctx)

def alert(to, ctx):
    user = User.objects.get(email=to)
    if user.profile.alert_mode == "Phone":
        to = [user.profile.phone_number]
        verb = "is running" if ctx['check'].status =="too often" else "is"
        sms_body = "The check {} {} {}".format(
            ctx['check'].name_then_code(), verb, ctx['check'].status)
        send_sms(to, sms_body)
    send("alert", to, ctx)


def verify_email(to, ctx):
    send("verify-email", to, ctx)


def report(to, ctx):
    send("report", to, ctx)

def send_task(to, ctx):
    send("tasks", to, ctx)