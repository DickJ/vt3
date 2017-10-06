from pprint import pprint as pp


class TwilioRestClient:
    def __init__(self, account_sid, auth_token):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.messages = TwilioMessage()

class TwilioMessage:
    def __init__(self):
        pass

    def create(self, body=None, to=None, from_=None):
        pp((body, to))
        return True
