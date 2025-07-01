import os
import zoho
import mxroute

def main():
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    org_id = os.getenv('ORGANIZATION_ID')

    zoho_client = zoho.Zoho(client_id, client_secret, org_id)
    user_emails = zoho_client.get_user_emails()
    group_emails = zoho_client.get_group_emails()
    zoho_emails = user_emails | group_emails

    user_id = os.getenv('USER_ID')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')

    mxroute_client = mxroute.MXroute(user_id, password, server)
    domains = mxroute_client.list_domains()
    forwarders = set()
    for domain in domains:
        forwarders = forwarders | mxroute_client.list_forwarders(domain)
    print(forwarders)

if __name__ == '__main__':
    main()
