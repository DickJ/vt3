import logging
import os
import re

import sendgrid
from sendgrid.helpers.mail import *
from twilio.rest import Client

from utils import u_db


class TextClient:
    def __init__(self, msg_svc='sendgrid', debug=False):
        self.debug = debug
        self.msg_svc = msg_svc

        self.twilio_client = Client(os.environ.get('TWILIO_SID'),
                                    os.environ.get('TWILIO_AUTH_TOKEN'))
        self.phone = os.environ.get('TWILIO_PHONE_NUMBER')

        self.sendgrid_client = sendgrid.SendGridAPIClient(
            apikey=os.environ.get('SENDGRID_API_KEY'))
        self.from_email = Email(os.environ.get('SENDGRID_FROM_EMAIL'))

    def send_message(self, phone, date, msg, provider=None):
        """
        Send a message via SMS
        :param phone: (str) Phonen umber in E.164 format
        :param date: (str) MMM DD
        :param msg: (str) the message to send
        :param provider: (str) Wireless provider; needed for use with sendgrid
        :return: message response
        """
        assert phone[0] == '+' and phone[1] == '1', \
            'TextClient:send_message() - Invalid phone number %r' % phone

        if self.msg_svc == 'sendgrid':
            assert provider is not None, 'No wireless provider given'
            phone = phone[2:]
            subject = date
            to_email = Email(self.from_email_address(phone, provider))
            content = Content("text/plain", msg)
            mail = Mail(self.from_email, subject, to_email, content)

            if self.debug:
                response = str(mail.get())
                logging.debug(response)
            else:
                response = self.sendgrid_client.client.mail.send.post(
                    request_body=mail.get())
        elif self.msg_svc == 'twilio':
            message = '({}) {}'.format(date, msg)
            if self.debug:
                logging.debug('{} {}'.format(phone, message))
                response = 0
            else:
                message = self.twilio_client.messages.create(
                    to=phone, from_=self.phone, body=message)
                response = message.sid
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
        assert len(phone) == 10, 'phone is not lenght 10'
        assert re.match('\d{10}', phone), 'phone is not all digits'
        assert provider is not None, 'No wireless provider given'

        conn, cur = u_db.get_db_conn_and_cursor()
        cur.execute('SELECT gateway FROM smsgateways WHERE name = %s;', [provider])

        #TODO Is this really the best behavior I can come up with?
        # A better solution might be to force usage with Twilio, however if
        # Twilio is setup, then why don't I just use twilio for everything in
        # the first place? For now, I am simply going to leave this as the state
        # of things until I complete the implementation of Twilio. At that point
        # This entire function should be removed.
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
