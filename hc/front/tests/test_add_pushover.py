from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="url")
class AddPushoverTestCase(BaseTestCase):
    def test_push_over(self):
        """
            Test pushover integration
        """
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=n&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 302

        channels = list(Channel.objects.all())
        assert len(channels) == 1
        assert channels[0].value == "a|0"

    @override_settings(PUSHOVER_API_TOKEN=None)
    def test_it_requires_api_token(self):
        """
            Test page not found if pushover api token doesn't exist
        """
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_pushover/")
        self.assertEqual(r.status_code, 404)

    def test_it_validates_nonce(self):
        """
            Test pushover integration with invalid data
        """
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=INVALID&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 403

    @override_settings(PUSHOVER_API_TOKEN='dummy_token')
    def test_if_pushover_works(self):
        """
            Test if pushover integration is working with a token exist
        """
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_pushover/")
        self.assertEqual(r.status_code, 200)

    def test_validates_params(self):
        """
            Test adding pushover integration with invalid param
        """
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&INVALID=n&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 400

    def test_validates_session(self):
        """
            Test pushover integration with no session
        """
        self.client.login(username="alice@example.org", password="password")

        params = "pushover_user_key=a&nonce=n&prio=0"

        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 403
        
    def test_validates_priority(self):
        """
            Test adding pushover validates priority
        """
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=n&prio=Invalid"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 400
    ### Test that pushover validates priority
