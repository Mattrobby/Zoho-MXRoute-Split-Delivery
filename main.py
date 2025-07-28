import os
import sys
import logging
from typing import Set, Optional
from dotenv import load_dotenv
import zoho
import mxroute

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
  level=getattr(logging, log_level, logging.INFO),
  format='%(asctime)s - %(levelname)s - %(message)s',
  handlers=[
    logging.FileHandler('email_sync.log'),
    logging.StreamHandler()
  ]
)
logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
  """Custom exception for configuration-related errors."""
  pass

class EmailSyncError(Exception):
  """Custom exception for email synchronization errors."""
  pass

def validate_environment() -> dict:
  """Validate that all required environment variables are present."""
  required_vars = {
    'CLIENT_ID': 'Zoho client ID',
    'CLIENT_SECRET': 'Zoho client secret', 
    'ORGANIZATION_ID': 'Zoho organization ID',
    'USER_ID': 'MXRoute user ID',
    'PASSWORD': 'MXRoute password',
    'SERVER': 'MXRoute server URL'
  }
  
  config = {}
  missing_vars = []
  
  for var, description in required_vars.items():
    value = os.getenv(var)
    if not value:
      missing_vars.append(f"{var} ({description})")
    else:
      config[var] = value
  
  if missing_vars:
    raise ConfigurationError(
      f"Missing required environment variables: {', '.join(missing_vars)}"
    )
  
  logger.info("Environment configuration validated successfully")
  return config

def get_zoho_emails(config: dict) -> Set[str]:
  """Retrieve all emails from Zoho (users and groups)."""
  try:
    logger.info("Connecting to Zoho...")
    zoho_client = zoho.Zoho(
      config['CLIENT_ID'], 
      config['CLIENT_SECRET'], 
      config['ORGANIZATION_ID']
    )
    
    logger.info("Fetching user emails from Zoho...")
    user_emails = zoho_client.get_user_emails()
    logger.info(f"Found {len(user_emails)} user emails")
    
    logger.info("Fetching group emails from Zoho...")
    group_emails = zoho_client.get_group_emails()
    logger.info(f"Found {len(group_emails)} group emails")
    
    zoho_emails = user_emails | group_emails
    logger.info(f"Total Zoho emails: {len(zoho_emails)}")
    
    return zoho_emails
    
  except Exception as e:
    logger.error(f"Failed to retrieve emails from Zoho: {str(e)}")
    raise EmailSyncError(f"Zoho API error: {str(e)}") from e

def get_mxroute_info(config: dict) -> tuple[Set[str], Set[str]]:
  """Retrieve domains and forwarders from MXRoute."""
  try:
    logger.info("Connecting to MXRoute...")
    mxroute_client = mxroute.MXroute(
      config['USER_ID'], 
      config['PASSWORD'], 
      config['SERVER']
    )
    
    logger.info("Fetching domains from MXRoute...")
    domains = mxroute_client.list_domains()
    logger.info(f"Found {len(domains)} domains")
    
    logger.info("Fetching forwarders from MXRoute...")
    forwarders = set()
    for domain in domains:
      try:
        domain_forwarders = mxroute_client.list_forwarders(domain)
        forwarders.update(domain_forwarders)
        logger.debug(f"Found {len(domain_forwarders)} forwarders for domain {domain}")
      except Exception as e:
        logger.warning(f"Failed to get forwarders for domain {domain}: {str(e)}")
        continue
    
    logger.info(f"Total forwarders found: {len(forwarders)}")
    return domains, forwarders
    
  except Exception as e:
    logger.error(f"Failed to retrieve information from MXRoute: {str(e)}")
    raise EmailSyncError(f"MXRoute API error: {str(e)}") from e

def create_expected_forwarders(zoho_emails: Set[str], available_domains: Set[str]) -> Set[str]:
  """Create the set of expected forwarder destinations based on Zoho emails."""
  expected_forwarders = set()
  skipped_emails = []
  
  for zoho_email in zoho_emails:
    try:
      if '@' not in zoho_email:
        logger.warning(f"Invalid email format: {zoho_email}")
        continue
        
      user, domain = zoho_email.split('@', 1)
      dest = f'{user}@zoho.{domain}'
      
      if domain not in available_domains:
        skipped_emails.append(zoho_email)
        logger.info(f'Skipping {zoho_email} - domain "{domain}" not available in MXRoute')
        continue
      
      expected_forwarders.add(dest)
      
    except ValueError as e:
      logger.warning(f"Failed to process email {zoho_email}: {str(e)}")
      continue
  
  if skipped_emails:
    logger.info(f"Skipped {len(skipped_emails)} emails due to unavailable domains")
  
  return expected_forwarders

def sync_forwarders(config: dict, zoho_emails: Set[str], domains: Set[str], 
                   existing_forwarders: Set[str]) -> tuple[int, int, int]:
  """Synchronize forwarders between Zoho and MXRoute."""
  mxroute_client = mxroute.MXroute(
    config['USER_ID'], 
    config['PASSWORD'], 
    config['SERVER']
  )
  
  expected_forwarders = create_expected_forwarders(zoho_emails, domains)
  
  added_count = 0
  skipped_count = 0
  removed_count = 0
  
  # Add missing forwarders
  logger.info("Adding missing forwarders...")
  for zoho_email in zoho_emails:
    try:
      if '@' not in zoho_email:
        continue
        
      user, domain = zoho_email.split('@', 1)
      dest = f'{user}@zoho.{domain}'
      
      if domain not in domains:
        continue
      
      if dest not in existing_forwarders:
        logger.info(f'Adding forwarder {user}@{domain} --> {dest}')
        try:
          result = mxroute_client.add_forwarder(domain, user, dest)
          logger.debug(f"Add forwarder result: {result}")
          added_count += 1
        except Exception as e:
          logger.error(f"Failed to add forwarder {user}@{domain} --> {dest}: {str(e)}")
          continue
      else:
        logger.debug(f'Forwarder {user}@{domain} --> {dest} already exists')
        skipped_count += 1
        
    except Exception as e:
      logger.error(f"Error processing email {zoho_email}: {str(e)}")
      continue
  
  # Remove obsolete forwarders
  logger.info("Removing obsolete forwarders...")
  for forwarder in existing_forwarders:
    try:
      if '@zoho.' in forwarder and forwarder not in expected_forwarders:
        # Extract the original domain and user from the forwarder destination
        parts = forwarder.replace('@zoho.', '@').split('@')
        if len(parts) >= 2:
          original_user = parts[0]
          original_domain = parts[1]
          logger.info(f'Removing forwarder {original_user}@{original_domain} --> {forwarder}')
          try:
            result = mxroute_client.delete_forwarder(original_domain, original_user)
            logger.debug(f"Delete forwarder result: {result}")
            removed_count += 1
          except Exception as e:
            logger.error(f"Failed to remove forwarder {original_user}@{original_domain}: {str(e)}")
            continue
    except Exception as e:
      logger.error(f"Error processing forwarder {forwarder}: {str(e)}")
      continue
  
  return added_count, skipped_count, removed_count

def print_summary(zoho_emails: Set[str], forwarders: Set[str], 
                 added: int, skipped: int, removed: int):
  """Print a summary of the synchronization results."""
  print("\n" + "="*60)
  print("EMAIL SYNCHRONIZATION SUMMARY")
  print("="*60)
  
  print(f"\nZoho emails found: {len(zoho_emails)}")
  for email in sorted(zoho_emails):
    print(f"  - {email}")
  
  print(f"\nMXRoute forwarders found: {len(forwarders)}")
  for email in sorted(forwarders):
    print(f"  - {email}")
  
  print(f"\nSynchronization results:")
  print(f"  - Forwarders added: {added}")
  print(f"  - Forwarders skipped (already exist): {skipped}")
  print(f"  - Forwarders removed: {removed}")
  print("="*60)

def main():
  """Main function to orchestrate the email synchronization process."""
  try:
    logger.info("Starting email synchronization process...")
    
    # Validate configuration
    config = validate_environment()
    
    # Get Zoho emails
    zoho_emails = get_zoho_emails(config)
    if not zoho_emails:
      logger.warning("No emails found in Zoho. Nothing to synchronize.")
      return
    
    # Get MXRoute information  
    domains, forwarders = get_mxroute_info(config)
    if not domains:
      logger.warning("No domains found in MXRoute. Cannot create forwarders.")
      return
    
    # Synchronize forwarders
    added, skipped, removed = sync_forwarders(config, zoho_emails, domains, forwarders)
    
    # Print summary
    print_summary(zoho_emails, forwarders, added, skipped, removed)
    
    logger.info("Email synchronization completed successfully")
    logger.info(f"Summary: {added} added, {skipped} skipped, {removed} removed")
    
  except ConfigurationError as e:
    logger.error(f"Configuration error: {str(e)}")
    print(f"Error: {str(e)}")
    sys.exit(1)
    
  except EmailSyncError as e:
    logger.error(f"Synchronization error: {str(e)}")
    print(f"Error: {str(e)}")
    sys.exit(1)
    
  except KeyboardInterrupt:
    logger.info("Process interrupted by user")
    print("\nProcess interrupted by user")
    sys.exit(0)
    
  except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    print(f"Unexpected error occurred. Check the log file for details.")
    sys.exit(1)

if __name__ == '__main__':
  main()