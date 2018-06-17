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


def alert(to, ctx):
    user = User.objects.get(email=to)
    if user.profile.alert_mode == "Phone":
        to = [user.profile.phone_number]
        sms_body = "The check {} is running {}".format(
            ctx['check'].name_then_code(), ctx['check'].status)
        send_sms(to, sms_body)
    send("alert", to, ctx)


def verify_email(to, ctx):
    send("verify-email", to, ctx)


def report(to, ctx):
    send("report", to, ctx)
