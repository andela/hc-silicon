import base64
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core import signing
from django.db import models
from django.urls import reverse
from django.utils import timezone
from hc.lib import emails


class Profile(models.Model):
    # Owner:
    user = models.OneToOneField(User, blank=True, null=True)
    team_name = models.CharField(max_length=200, blank=True)
    team_access_allowed = models.BooleanField(default=False)
    next_report_date = models.DateTimeField(null=True, blank=True)
    reports_allowed = models.BooleanField(default=True)
    reports_frequency = models.CharField(max_length=200, default="Monthly")
    alert_mode = models.CharField(max_length=200, default="Email")
    phone_number = models.CharField(max_length=200, null=True)
    ping_log_limit = models.IntegerField(default=100)
    token = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=128, blank=True)
    current_team = models.ForeignKey("self", null=True)

    def __str__(self):
        return self.team_name or self.user.email

    def send_instant_login_link(self, inviting_profile=None, department=None):
        token = str(uuid.uuid4())
        self.token = make_password(token)
        self.save()
        
        path = reverse("hc-check-token", args=[self.user.username, token])
        ctx = {
            "login_link": settings.SITE_ROOT + path,
            "inviting_profile": inviting_profile,
            "department": department
        }
        emails.login(self.user.email, ctx)

    def department(self,user):
        try:
            member = Member.objects.get(team=self, user=user)
            return member.department
        except Member.DoesNotExist:
            return None

    def send_set_password_link(self):
        token = str(uuid.uuid4())
        self.token = make_password(token)
        self.save()

        path = reverse("hc-set-password", args=[token])
        ctx = {"set_password_link": settings.SITE_ROOT + path}
        emails.set_password(self.user.email, ctx)

    def set_api_key(self):
        self.api_key = base64.urlsafe_b64encode(os.urandom(24))
        self.save()

    def send_report(self):
        # reset next report date first:
        day = timezone.timedelta(days=0)
        if self.reports_frequency == 'Disabled':
            self.reports_allowed = False
            self.reports_frequency = 'Disabled'

        if self.reports_frequency == 'Daily':
            day = timezone.timedelta(days=1)

        elif self.reports_frequency == 'Weekly':
            day = timezone.timedelta(days=7)

        elif self.reports_frequency == 'Monthly':
            day = timezone.timedelta(days=30)

        now = timezone.now()
        self.next_report_date = now + day
        self.save()

        token = signing.Signer().sign(uuid.uuid4())
        path = reverse("hc-unsubscribe-reports", args=[self.user.username])
        unsub_link = "%s%s?token=%s" % (settings.SITE_ROOT, path, token)

        ctx = {
            "checks": self.user.check_set.order_by("created"),
            "now": now,
            "Duration": self.reports_frequency,
            "unsub_link": unsub_link
        }

        emails.report(self.user.email, ctx)

    def invite(self, user, department):
        member = Member(team=self, user=user, department=department)
        member.save()
        
        # Switch the invited user over to the new team so they
        # notice the new team on next visit:
        user.profile.current_team = self
        user.profile.save()
        if department != None:
            department = department.name
        user.profile.send_instant_login_link(self,department=department)



class Department(models.Model):
    team = models.ForeignKey(Profile)
    name = models.CharField(max_length=128, null=True, blank=True)
    
    def __str__(self):
        return self.name

class Member(models.Model):
    class Meta:
        ordering = ['priority']
    team = models.ForeignKey(Profile)
    user = models.ForeignKey(User)
    department = models.ForeignKey(Department)
    priority = models.CharField(max_length=4, default="LOW")