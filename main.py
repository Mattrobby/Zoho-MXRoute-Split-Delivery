import zoho
import os

def main():
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    org_id = os.getenv('ORGANIZATION_ID')

    zoho_client = zoho.Zoho(client_id, client_secret, org_id)
    emails = zoho_client.get_user_emails()
    print(emails)

if __name__ == '__main__':
    main()
