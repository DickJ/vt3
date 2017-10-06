import unittest

from utils.classes.TextClient import TextClient


class TextClientTestCase(unittest.TestCase):
    def setUp(self):
        self.tc = TextClient()

    def tearDown(self):
        pass

    def test_send_message(self):
        pass

    def test_from_email_address(self):
        self.assertEqual(self.tc.from_email_address('8885551111', 'alltel'), '8885551111@text.wireless.alltel.com')
        self.assertEqual(self.tc.from_email_address('8885552222', 'att'), '8885552222@txt.att.net')
        self.assertEqual(self.tc.from_email_address('8885553333', 'boost'), '8885553333@myboostmobile.com')
        self.assertEqual(self.tc.from_email_address('8885554444', 'cricket'), '8885554444@sms.mycricket.com')
        self.assertEqual(self.tc.from_email_address('8885555555', 'metropcs'), '8885555555@mymetropcs.com')
        self.assertEqual(self.tc.from_email_address('8885556666', 'projectfi'), '8885556666@msg.fi.google.com')
        self.assertEqual(self.tc.from_email_address('8885557777', 'sprint'), '8885557777@messaging.sprintpcs.com')
        self.assertEqual(self.tc.from_email_address('8885558888', 'straighttalk'), '8885558888@VTEXT.COM')
        self.assertEqual(self.tc.from_email_address('8885559999', 'tmobile'), '8885559999@tmomail.net')
        self.assertEqual(self.tc.from_email_address('8885550000', 'uscellular'), '8885550000@email.uscc.net')
        self.assertEqual(self.tc.from_email_address('8886661111', 'verizon'), '8886661111@vtext.com')
        self.assertEqual(self.tc.from_email_address('8886662222', 'virgin'), '8886662222@vmobl.com')

        self.assertEqual(self.tc.from_email_address('+18886662222', 'virgin'), '8886662222@vmobl.com')

        self.assertEqual(self.tc.from_email_address('+18886662222', 'fakeprovider'), '8886662222@invalidprovider.com')

        self.assertRaises(AssertionError, lambda: self.tc.from_email_address('123', 'fakeprovider'))
        self.assertRaises(AssertionError, lambda: self.tc.from_email_address('aaabbbcccc', 'fakeprovider'))
        self.assertRaises(AssertionError, lambda: self.tc.from_email_address('+1aaabbbcccc', 'fakeprovider'))
