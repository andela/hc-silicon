from django.test.utils import override_settings

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


@override_settings(PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="url")
class AddChannelTestCase(BaseTestCase):
    """Class to test add_channel feature"""
    def test_it_adds_email(self):
        url = "/integrations/add/"
        form = {"kind": "email", "value": "alice@example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, form)

        self.assertRedirects(r, "/integrations/")
        assert Channel.objects.count() == 1

    def test_it_trims_whitespace(self):
        """ Leading and trailing whitespace should get trimmed. """

        url = "/integrations/add/"
        form = {"kind": "email", "value": "   alice@example.org   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(url, form)

        q = Channel.objects.filter(value="alice@example.org")
        self.assertEqual(q.count(), 1)

    def test_instructions_work(self):
        """Test that kinds work"""
        self.client.login(username="alice@example.org", password="password")
        kinds = ("email", "webhook", "pd", "pushover", "hipchat", "victorops")
        for frag in kinds:
            url = "/integrations/add_%s/" % frag
            r = self.client.get(url)
            self.assertContains(r, "Integration Settings", status_code=200)

    def test_team_access_works(self):
        """Test that a team access works well""" 
        url = "/checks/add/"
        # Bob who is in Alice's team logs in and creates a check
        self.client.login(username="bob@example.org", password="password")
        self.client.post(url)
        bob_check = Check.objects.get()
        # Alice owns the team, so any check Bob creates is under Alice's account
        self.assertEqual(bob_check.user, self.alice)

    def test_bad_kinds_do_not_work(self):
        """Test that bad kinds will not work"""
        self.client.login(username="alice@example.org", password="password")
        # Add a bad kind - one that does not exist
        bad_kinds = ("gitter", "facebook")
        for frag in bad_kinds:
            url = "/integrations/add_%s/" % frag
            response = self.client.get(url)
            # Test the status code of the bad kind
            self.assertEqual(response.status_code, 404)

    ### Test that the team access works
    ### Test that bad kinds don't work
