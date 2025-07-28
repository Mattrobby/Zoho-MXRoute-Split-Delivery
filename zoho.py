import requests
import logging
from typing import Set, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class ZohoError(Exception):
  """Custom exception for Zoho API errors."""
  pass

class ZohoAuthError(ZohoError):
  """Custom exception for Zoho authentication errors."""
  pass

class Zoho:
  def __init__(self, client_id: str, client_secret: str, org_id: str, 
               host: str = 'zoho.com', timeout: int = 30):
    if not all([client_id, client_secret, org_id]):
      raise ValueError("Client ID, client secret, and organization ID are required")
    
    self.client_id = client_id
    self.client_secret = client_secret
    self.org_id = org_id
    self.host = host
    self.timeout = timeout
    
    self.scope = 'ZohoMail.organization.accounts.READ,ZohoMail.organization.groups.READ'
    self.redirect_url = 'localhost'
    self.access_type = 'online'
    
    # Configure session with retry strategy
    self.session = requests.Session()
    retry_strategy = Retry(
      total=3,
      status_forcelist=[429, 500, 502, 503, 504],
      allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
      backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    self.session.mount("http://", adapter)
    self.session.mount("https://", adapter)
    
    self.access_token: Optional[str] = None
    self._authenticate()
    
    logger.info(f"Initialized Zoho client for organization: {self.org_id}")

  def _authenticate(self) -> None:
    """Authenticate with Zoho and get access token."""
    try:
      logger.info("Authenticating with Zoho...")
      
      # Using Zoho Self-Client credential flow auth
      grant_type = 'client_credentials'
      soid = f'ZohoMail.{self.org_id}'
      
      url = f'https://accounts.{self.host}/oauth/v2/token'
      params = {
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'grant_type': grant_type,
        'scope': self.scope,
        'soid': soid
      }
      
      logger.debug("Making authentication request to Zoho...")
      response = self.session.post(url, params=params, timeout=self.timeout)
      
      if response.status_code == 400:
        error_data = response.json()
        error_msg = error_data.get('error', 'Unknown error')
        raise ZohoAuthError(f"Authentication failed: {error_msg}")
      elif response.status_code == 401:
        raise ZohoAuthError("Invalid client credentials")
      elif not response.ok:
        raise ZohoAuthError(f"Authentication failed with status {response.status_code}: {response.text}")
      
      try:
        auth_data = response.json()
      except ValueError as e:
        raise ZohoAuthError(f"Invalid JSON response from auth endpoint: {str(e)}")
      
      if 'access_token' not in auth_data:
        error_msg = auth_data.get('error', 'No access token in response')
        raise ZohoAuthError(f"Authentication failed: {error_msg}")
      
      self.access_token = auth_data['access_token']
      logger.info("Successfully authenticated with Zoho")
      
    except requests.exceptions.Timeout:
      raise ZohoAuthError(f"Authentication request timed out after {self.timeout} seconds")
    except requests.exceptions.ConnectionError as e:
      raise ZohoAuthError(f"Connection error during authentication: {str(e)}")
    except requests.exceptions.RequestException as e:
      raise ZohoAuthError(f"Request failed during authentication: {str(e)}")

  def _make_api_call(self, path: str) -> Dict[str, Any]:
    """Make an authenticated API call to Zoho."""
    if not self.access_token:
      raise ZohoError("Not authenticated. Access token is missing.")
    
    try:
      url = f'https://mail.{self.host}/{path}'
      headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Zoho-oauthtoken {self.access_token}',
      }
      
      logger.debug(f"Making API call to: {url}")
      response = self.session.get(url, headers=headers, timeout=self.timeout)
      
      if response.status_code == 401:
        raise ZohoError("Authentication expired or invalid. Please re-authenticate.")
      elif response.status_code == 403:
        raise ZohoError("Access forbidden. Check API permissions and organization ID.")
      elif response.status_code == 404:
        raise ZohoError("Resource not found. Check the API endpoint and organization ID.")
      elif response.status_code == 429:
        raise ZohoError("Rate limit exceeded. Please try again later.")
      elif not response.ok:
        raise ZohoError(f"API call failed with status {response.status_code}: {response.text}")
      
      try:
        return response.json()
      except ValueError as e:
        logger.error(f"Failed to parse JSON response: {response.text}")
        raise ZohoError(f"Invalid JSON response: {str(e)}")
        
    except requests.exceptions.Timeout:
      raise ZohoError(f"API request timed out after {self.timeout} seconds")
    except requests.exceptions.ConnectionError as e:
      raise ZohoError(f"Connection error: {str(e)}")
    except requests.exceptions.RequestException as e:
      raise ZohoError(f"Request failed: {str(e)}")

  def get_user_emails(self) -> Set[str]:
    """Retrieve all user email addresses from the organization."""
    try:
      logger.info("Fetching user emails from Zoho...")
      
      path = f'api/organization/{self.org_id}/accounts'
      data = self._make_api_call(path)
      
      if 'data' not in data:
        logger.warning("No user data found in response")
        return set()
      
      emails = set()
      users = data['data']
      
      if not isinstance(users, list):
        logger.warning(f"Expected list of users, got: {type(users)}")
        return set()
      
      for user in users:
        if not isinstance(user, dict):
          logger.warning(f"Expected user dict, got: {type(user)}")
          continue
        
        email_addresses = user.get('emailAddress', [])
        if not isinstance(email_addresses, list):
          logger.warning(f"Expected list of email addresses, got: {type(email_addresses)}")
          continue
        
        for email_obj in email_addresses:
          if isinstance(email_obj, dict) and 'mailId' in email_obj:
            email = email_obj['mailId']
            if email and '@' in email:
              emails.add(email.lower().strip())
            else:
              logger.warning(f"Invalid email format: {email}")
          else:
            logger.warning(f"Unexpected email object format: {email_obj}")
      
      logger.info(f"Retrieved {len(emails)} user emails from Zoho")
      return emails
      
    except Exception as e:
      logger.error(f"Failed to retrieve user emails: {str(e)}")
      raise ZohoError(f"Failed to get user emails: {str(e)}") from e

  def get_group_emails(self) -> Set[str]:
    """Retrieve all group email addresses from the organization."""
    try:
      logger.info("Fetching group emails from Zoho...")
      
      path = f'api/organization/{self.org_id}/groups'
      data = self._make_api_call(path)
      
      if 'data' not in data:
        logger.warning("No group data found in response")
        return set()
      
      groups_data = data['data']
      if not isinstance(groups_data, dict) or 'groups' not in groups_data:
        logger.warning("Expected groups data structure not found")
        return set()
      
      groups = groups_data['groups']
      if not isinstance(groups, list):
        logger.warning(f"Expected list of groups, got: {type(groups)}")
        return set()
      
      emails = set()
      
      for group in groups:
        if not isinstance(group, dict):
          logger.warning(f"Expected group dict, got: {type(group)}")
          continue
        
        # Add main group email
        group_email = group.get('emailId')
        if group_email and '@' in group_email:
          emails.add(group_email.lower().strip())
        else:
          logger.warning(f"Invalid group email: {group_email}")
        
        # Add alias emails
        alias_list = group.get('aliasList', [])
        if isinstance(alias_list, list):
          for alias in alias_list:
            if isinstance(alias, dict) and 'mailId' in alias:
              alias_email = alias['mailId']
              if alias_email and '@' in alias_email:
                emails.add(alias_email.lower().strip())
              else:
                logger.warning(f"Invalid alias email: {alias_email}")
            else:
              logger.warning(f"Unexpected alias format: {alias}")
        else:
          logger.warning(f"Expected list of aliases, got: {type(alias_list)}")
      
      logger.info(f"Retrieved {len(emails)} group emails from Zoho")
      return emails
      
    except Exception as e:
      logger.error(f"Failed to retrieve group emails: {str(e)}")
      raise ZohoError(f"Failed to get group emails: {str(e)}") from e

  def test_connection(self) -> bool:
    """Test the connection to Zoho API."""
    try:
      self.get_user_emails()
      logger.info("Zoho connection test successful")
      return True
    except Exception as e:
      logger.error(f"Zoho connection test failed: {str(e)}")
      return False

  def get_organization_info(self) -> Dict[str, Any]:
    """Get organization information for debugging purposes."""
    try:
      path = f'api/organization/{self.org_id}'
      return self._make_api_call(path)
    except Exception as e:
      logger.error(f"Failed to get organization info: {str(e)}")
      raise ZohoError(f"Failed to get organization info: {str(e)}") from e