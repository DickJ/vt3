import logging
import os
import sendgrid
from sendgrid.helpers.mail import *


class TextClient():
    def __init__(self, debug=False):
        self.debug = debug
        self.sg = sendgrid.SendGridAPIClient(
            apikey=os.environ.get('SENDGRID_API_KEY'))
        self.from_email = Email('vt3@herokuapp.com')

    def send_message(self, phone, provider, date, msg):
        assert phone[0] == '+' and phone[1] == '1', \
            'TextClient:send_message() - Invalid phone number %r' % phone
        phone = phone[2:]
        subject = date
        to_email = Email(self.from_email_address(phone, provider))
        content = Content("text/plain", msg)
        mail = Mail(self.from_email, subject, to_email, content)

        if self.debug:
            logging.debug(str(mail.get()))
            response = 'Debug'
        else:
            response = self.sg.client.mail.send.post(request_body=mail.get())

        return response

    def from_email_address(self, phone, provider):
        """
        http://www.howtogeek.com/howto/27051/use-email-to-send-text-messages-sms-to-mobile-phones-for-free/

        Params:
            phone: (str) e.164 format; ex. +12225555555
            provider: (str)

        Returns:

        """
        sms_domains = {'alltell': 'text.wireless.alltel.com',
                       'att': 'txt.att.net',
                       'boost': 'myboostmobile.com',
                       'cricket': 'sms.mycricket.com',
                       'metropcs': 'mymetropcs.com',
                       'sprint': 'messaging.sprintpcs.com',
                       'straighttalk': 'VTEXT.COM',
                       'tmobile': 'tmomail.net',
                       'uscellular': 'email.uscc.net',
                       'verizon': 'vtext.com',
                       'virgin': 'vmobl.com',
                       }

        try:
            email = phone + '@' + sms_domains[provider]
            return email
        except KeyError:
            logging.error({'func': 'TextClient:from_email_address',
                           'msg': 'KeyError: %r is not a valid mobile provider' % provider})
            return 'blackhole@nowhere.com' # TODO Setup email address for error



