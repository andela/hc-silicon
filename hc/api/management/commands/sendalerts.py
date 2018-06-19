import logging
import time

from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from hc.api.models import Check, Channel
from hc.accounts.models import Member
from datetime import timedelta as td
from hc.lib import emails

executor = ThreadPoolExecutor(max_workers=10)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle_many(self):
        """ Send alerts for many checks simultaneously. """
        query = Check.objects.filter(user__isnull=False).select_related("user")

        now = timezone.now()

        # Escalation email
        for check in query:
            if check.get_status() == "down":
                if check.priority > 0:
                    if not check.escalation_down:
                        if not check.escalation_time:
                            check.escalation_time = now + check.escalation_interval
                            check.save()
                        if check.escalation_time <= now:
                            self.stdout.write(check.name+" is "+check.get_status())
                            check.escalation_down = True
                            check.escalation_up = False
                            check.save()
                            executor.submit(self.escalate_one(check, now))

            elif check.get_status() == "up":
                if check.priority > 0 and not check.escalation_up:
                    check.escalation_down = False
                    check.escalation_up = True
                    check.escalation_time = None
                    check.save()
                    executor.submit(self.escalate_one(check, now))


        going_down = query.filter(alert_after__lt=now, status="up")
        going_up = query.filter(alert_after__gt=now, status="down")
        going_down_from_often = query.filter(
            alert_after__lt=now, status="too often")
        nag_on = query.filter(
            nag_after__lt=now, nag_status=True, status="down")
        # Don't combine this in one query so Postgres can query using index:
        checks = list(going_down.iterator()) + list(going_up.iterator()) + \
            list(nag_on.iterator()) + list(going_down_from_often.iterator())
        if not checks:
            return False

        futures = [executor.submit(self.handle_one, check) for check in checks]
        for future in futures:
            future.result()

        return True

    def handle_one(self, check):
        """ Send an alert for a single check.
        Return True if an appropriate check was selected and processed.
        Return False if no checks need to be processed.
        """

        # Save the new status. If sendalerts crashes,
        # it won't process this check again.
        now = timezone.now()
        check.status = check.get_status()

        if check.status in ("down", "too often"):
            check.nag_after = timezone.now() + check.nag
            check.nag_status = True
            self.handles_priority(check)

        check.save()
        self.send_alert(check)
        connection.close()
        return True

    def escalate_one(self, check, now):
        ctx = {
            "check": check,
            "now": now
          }
        emails.escalate(check.escalation_list, ctx)


    def send_alert(self, check):
        """Helper method to notify user"""
        tmpl = "\nSending alert, status=%s, code=%s\n"
        self.stdout.write(tmpl % (check.status, check.code))
        errors = check.send_alert()
        if errors is not None:
            for ch, error in errors:
                self.stdout.write("ERROR: %s %s %s\n" %
                                  (ch.kind, ch.value, error))

        connection.close()
        return True

    def handle(self, *args, **options):
        self.stdout.write("sendalerts is now running")

        ticks = 0
        while True:
            if self.handle_many():
                ticks = 1
            else:
                ticks += 1

            time.sleep(1)
            if ticks % 60 == 0:
                formatted = timezone.now().isoformat()
                self.stdout.write("-- MARK %s --" % formatted)

    def handles_priority(self, check):
        members = Member.objects.filter(team=check.user.profile).all().order_by("priority")

        for member in members:
            if member.priority == "LOW" or (member.priority == "HIGH" and not check.is_alerted):
                channel = Channel.objects.filter(value=member.user.email).first()
                check.is_alerted = True
                check.save()
                error = channel.notify(check)

                if error not in ("", "no-op"):
                    print("%s, %s" % (channel, error))
