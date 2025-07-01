import os
import zoho
import mxroute

def main():
  # Zoho Vars
  client_id = os.getenv('CLIENT_ID')
  client_secret = os.getenv('CLIENT_SECRET')
  org_id = os.getenv('ORGANIZATION_ID')

  # MXRoute Vars
  user_id = os.getenv('USER_ID')
  password = os.getenv('PASSWORD')
  server = os.getenv('SERVER')

  # Getting zoho users
  # NOTE: As of now there is not a way to get shared inboxes via
  # the api. Those will have to be manually entered.
  zoho_client = zoho.Zoho(client_id, client_secret, org_id)
  user_emails = zoho_client.get_user_emails()
  group_emails = zoho_client.get_group_emails()
  zoho_emails = user_emails | group_emails

  # Getting forwarders from mxroute
  mxroute_client = mxroute.MXroute(user_id, password, server)
  domains = mxroute_client.list_domains()

  forwarders = set()
  for domain in domains:
    forwarders = forwarders | mxroute_client.list_forwarders(domain)

  print(forwarders)

  # Create expected forwarder destinations
  expected_forwarders = set()
  for zoho_email in zoho_emails:
    split = zoho_email.split('@')
    user = split[0]
    domain = split[1]
    dest = f'{user}@zoho.{domain}'
    expected_forwarders.add(dest)

    # Add missing forwarders
    if dest not in forwarders:
      print(f'Adding forwarder {user}@{domain} --> {dest} to MXRoute')
      mxroute_client.add_forwarder(domain, user, dest)

  # Remove forwarders that are no longer needed
  for forwarder in forwarders:
    if '@zoho.' in forwarder and forwarder not in expected_forwarders:
      # Extract the original domain and user from the forwarder destination
      parts = forwarder.replace('@zoho.', '@').split('@')
      original_user = parts[0]
      original_domain = parts[1]
      print(f'Removing forwarder {original_user}@{original_domain} --> {forwarder} from MXRoute')
      mxroute_client.delete_forwarder(original_domain, original_user)

if __name__ == '__main__':
  main()
