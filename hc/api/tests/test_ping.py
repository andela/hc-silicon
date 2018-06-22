from django.test import Client, TestCase
from django.core import mail

from hc.api.models import Check, Ping, User
from hc.accounts.models import Profile


class PingTestCase(TestCase):

    def setUp(self):
        super(PingTestCase, self).setUp()
        user = User(username="ned", email="ned@example.org")
        user.set_password("password")
        user.save()
        check = Check(user=user)
        check.save()

        # Create user profile
        profile = Profile(user=user, api_key="abc", department=None)
        profile.save()

        self.check = check

    def test_it_works(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        assert r.status_code == 200

        self.check.refresh_from_db()
        assert self.check.status == "up"

        ping = Ping.objects.latest("id")
        assert ping.scheme == "http"

    def test_it_handles_bad_uuid(self):
        r = self.client.get("/ping/not-uuid/")
        assert r.status_code == 400

    def test_it_handles_120_char_ua(self):
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/44.0.2403.89 Safari/537.36")

        r = self.client.get("/ping/%s/" % self.check.code, HTTP_USER_AGENT=ua)
        assert r.status_code == 200

        ping = Ping.objects.latest("id")
        assert ping.ua == ua

    def test_it_truncates_long_ua(self):
        ua = "01234567890" * 30

        r = self.client.get("/ping/%s/" % self.check.code, HTTP_USER_AGENT=ua)
        assert r.status_code == 200

        ping = Ping.objects.latest("id")
        assert len(ping.ua) == 200
        assert ua.startswith(ping.ua)

    def test_it_reads_forwarded_ip(self):
        ip = "1.1.1.1"
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)
        ping = Ping.objects.latest("id")
        self.assertEqual(ping.remote_addr, ip)
        self.assertEqual(r.status_code, 200)
        ### Assert the expected response status code and ping's remote address

        ip = "1.1.1.1, 2.2.2.2"
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip, REMOTE_ADDR="3.3.3.3")
        ping = Ping.objects.latest("id")
        assert r.status_code == 200
        assert ping.remote_addr == "1.1.1.1"

    def test_it_reads_forwarded_protocol(self):
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_PROTO="https")
        ping = Ping.objects.latest("id")

        self.assertEqual(ping.scheme, 'https')
        self.assertEqual(r.status_code, 200)
        ### Assert the expected response status code and ping's scheme

    def test_it_never_caches(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        assert "no-cache" in r.get("Cache-Control")

    def test_change_status_when_paused_check_is_pinged(self):
        """Test that when a ping is made a check with a paused status changes status"""
        self.check.status = "paused"
        self.check.save()
        ip ='1.1.1.1'
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)
        self.check.refresh_from_db()                
        
        self.assertEqual(self.check.status, 'up')

    def test_post_to_ping(self):
        """Test that a post to a ping works"""
        ip ='1.1.1.1'
        r = self.client.post("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)

        self.assertEqual(r.status_code, 200)

    def test_csrf_client_works(self):
       client=Client(enforce_csrf_checks=True)
       r = client.head("/ping/%s/" % self.check.code)
       self.assertEqual(r.status_code, 200)

    ### Test that when a ping is made a check with a paused status changes status
    ### Test that a post to a ping works
    ### Test that the csrf_client head works

    def test_it_sends_notification(self):
        # Run a job often by pinging twice
        ip = "1.1.1.1"
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)

        # Assert that the a warning email was sent the user
        self.assertEqual(len(mail.outbox), 1)
        check_code = str(self.check.code)
        self.assertEqual(mail.outbox[0].subject, check_code+" is too often")
        self.assertIn("The check \"{}\" has gone too often.".format(check_code), mail.outbox[0].body)