import requests

class MXroute:
  def __init__(self, username, password, server):
    self.username = username
    self.password = password
    self.server = server

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

  def add_forwarder(self, domain, user, email):
    url = f'{self.server}/CMD_EMAIL_FORWARDER?json=yes'
    headers = {'Content-Type': 'application/json'}
    payload = {
      'action': 'create',
      'domain': domain,
      'user': user,
      'email': email,
      'create': 'Create'
    }
    resp = requests.post(url, auth=(self.username, self.password), 
              headers=headers, json=payload)
    return resp.json() if resp.status_code == 200 else resp.text

  def delete_forwarder(self, domain, user):
    url = f'{self.server}/CMD_EMAIL_FORWARDER?json=yes'
    headers = {'Content-Type': 'application/json'}
    payload = {
      'action': 'delete',
      'domain': domain,
      'user': user,
      'delete': 'Delete'
    }
    resp = requests.post(url, auth=(self.username, self.password), 
              headers=headers, json=payload)
    return resp.json() if resp.status_code == 200 else resp.text
