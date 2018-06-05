from hc.api.models import Check
from hc.test import BaseTestCase


class AddCheckTestCase(BaseTestCase):

    def test_it_works(self):
        """Test user can add a check"""
        url = "/checks/add/"
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertRedirects(r, "/checks/")
        assert Check.objects.count() == 1

    def test_team_access(self):
        """ Test if the team owner can access checks created by another team member"""
        url = "/checks/add/"
        self.client.login(username="bob@example.org", password="password")
        self.client.post(url)
        r = Check.objects.get()

        self.assertEqual(r.user, self.alice)

    ### Test that team access works
