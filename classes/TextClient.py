from app import app
from app.helpers import get_db_conn_and_cursor
import logging
import os
import re
import sendgrid
from sendgrid.helpers.mail import *


class TextClient:
    def __init__(self, debug=False):
        self.debug = debug
        if debug:
            self.sg = None
        else:
            self.sg = sendgrid.SendGridAPIClient(
                apikey = os.environ.get('SENDGRID_API_KEY'))
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
            response = str(mail.get())
            logging.debug(response)
        else:
            response = self.sg.client.mail.send.post(request_body=mail.get())

        return response

    @staticmethod
    def from_email_address(phone, provider):
        """
        http://www.howtogeek.com/howto/27051/use-email-to-send-text-messages-sms-to-mobile-phones-for-free/

        Params:
            phone: (str) format is 2225559999
            provider: (str) mobile provider

        Returns: (str) email address as phone_number@sms.provider.com
        """

        if phone[:2] == '+1':
            phone = phone[2:]
        assert len(phone) == 10
        assert re.match('\d{10}', phone)

        conn, cur = get_db_conn_and_cursor(app.config)
        cur.execute('SELECT gateway FROM smsgateways WHERE name = %s;', [provider])

        # Is this really the best behavior I can come up with?
        try:
            gateway_address = cur.fetchone()[0]
        except TypeError:
            gateway_address = 'invalidprovider.com'

        try:
            email = phone + '@' + gateway_address
            return email
        except KeyError:
            logging.error({'func': 'TextClient:from_email_address',
                           'msg': 'KeyError: %r is not a valid mobile provider' % provider})
            return 'blackhole@nowhere.com' # TODO Setup email address for error



