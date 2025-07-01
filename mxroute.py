import requests

class MXroute:
    def __init__(self, username, password, server):
        self.username = username
        self.password = password
        self.server = server

    def make_call(self, function):
        pass

    def list_domains(self):
        url = f'{self.server}//CMD_API_SHOW_DOMAINS?json=yes'
        resp = requests.get(url, auth=(self.username, self.password))

        return resp.json()

    def list_forwarders(self, email_domain):
        url = f'{self.server}/CMD_API_EMAIL_FORWARDERS?domain={email_domain}&json=yes'
        resp = requests.get(url, auth=(self.username, self.password))

        emails = set()
        for value in resp.json().values():
            for email in value:
                emails.add(email)

        return emails

    def delete_forwarder(self, email_from, email_to):
        pass
