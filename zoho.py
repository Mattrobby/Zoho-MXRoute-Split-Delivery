import requests
from rich import print

class Zoho:

    def __init__(self, client_id, client_secret, org_id):
        self.client_id = client_id
        self.client_secret = client_secret

        self.scope = 'ZohoMail.organization.accounts.READ,ZohoMail.organization.groups.READ'
        self.host = 'zoho.com'
        self.redirect_url = 'localhost'
        self.access_type = 'online'
        self.org_id = org_id

        self.access_token = self.auth()

    def auth(self):
        # Using Zoho Self-Client credential flow auth. Docs can be found here:
        # - https://www.zoho.com/accounts/protocol/oauth/self-client/overview.html
        # - https://www.zoho.com/accounts/protocol/oauth/self-client/client-credentials-flow.html
        grant_type = 'client_credentials'
        soid = 'ZohoMail' + '.' + self.org_id
        path = f'oauth/v2/token?client_id={self.client_id}&client_secret={self.client_secret}&grant_type={grant_type}&scope={self.scope}&soid={soid}'
        url = 'https://accounts.' + self.host + '/' + path

        resp = requests.post(url)

        return resp.json()['access_token']

    def make_call(self, path):
        url = 'https://mail.' + self.host + '/' + path
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Zoho-oauthtoken ' + self.access_token,
        }

        print(url)
        resp = requests.get(url, headers=headers)
        return resp.json()

    def get_user_emails(self):
        path = f'api/organization/{self.org_id}/accounts'
        data = self.make_call(path)

        emails = set()
        print(data)
        for user in data['data']:
            print(user)
            for email in user['emailAddress']:
                emails.add(email['mailId'])

        return emails

    def get_group_emails(self):
        pass
