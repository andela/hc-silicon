from hc.api.models import Check
from hc.test import BaseTestCase


class RemoveCheckTestCase(BaseTestCase):

    def setUp(self):
        super(RemoveCheckTestCase, self).setUp()
        self.check = Check(user=self.alice, department=self.department)
        self.check.save()

        # Create an another check with different department (2 checks in DB)
        self.check_dep = Check(user=self.alice, department=None)
        self.check_dep.save()

    def test_it_works(self):
        url = "/checks/%s/remove/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertRedirects(r, "/checks/")

        # 2 checks minus deleted one we'll left with 1
        assert Check.objects.count() == 1

    def test_team_access_works(self):
        url = "/checks/%s/remove/" % self.check.code

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(url)
        # 2 checks minus deleted one we'll left with 1
        assert Check.objects.count() == 1
    
    def test_team_dept_access_works(self):
        url = "/checks/%s/remove/" % self.check_dep.code

        # log in bob
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 400

    def test_it_checks_owner(self):
        url = "/checks/%s/remove/" % self.check.code

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 403

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 404
