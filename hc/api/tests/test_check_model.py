from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from hc.api.models import Check


class CheckModelTestCase(TestCase):

    def test_it_strips_tags(self):
        """ Test input is stripped of uneccessary whitespaces"""
        check = Check()

        check.tags = " foo  bar "
        self.assertEquals(check.tags_list(), ["foo", "bar"])


    ### Repeat above test for when check is an empty string
    def test_it_strips_an_empty_tag_string(self):
        """ Test empty string is stripped thus passing no data"""
        check = Check()

        check.tags = "   "
        self.assertEquals(check.tags_list(), [])
        
    
    def test_status_works_with_grace_period(self):
        check = Check()

        check.status = "up"                                                                                                                                        
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)

        self.assertTrue(check.in_grace_period())
        self.assertEqual(check.get_status(), "up")
        ### The above 2 asserts fail. Make them pass        

    def test_paused_check_is_not_in_grace_period(self):
        check = Check()

        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)
        self.assertTrue(check.in_grace_period())

        check.status = "paused"
        self.assertFalse(check.in_grace_period())

    def test_new_check_is_not_in_grace_period(self):
        """Test that when a new check is created, it is not in the grace period"""
        check = Check()

        check.status = "new"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)
        self.assertFalse(check.in_grace_period())


    ### Test that when a new check is created, it is not in the grace period
