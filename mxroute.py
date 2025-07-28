import requests
import logging
from typing import Set, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class MXRouteError(Exception):
  """Custom exception for MXRoute API errors."""
  pass

class MXroute:
  def __init__(self, username: str, password: str, server: str, timeout: int = 30):
    if not all([username, password, server]):
      raise ValueError("Username, password, and server are required")
    
    self.username = username
    self.password = password
    self.server = server.rstrip('/')  # Remove trailing slash if present
    self.timeout = timeout
    
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
    
    logger.info(f"Initialized MXRoute client for server: {self.server}")

  def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with error handling and logging."""
    try:
      logger.debug(f"Making {method} request to: {url}")
      
      response = self.session.request(
        method=method,
        url=url,
        auth=(self.username, self.password),
        timeout=self.timeout,
        **kwargs
      )
      
      logger.debug(f"Response status: {response.status_code}")
      
      if response.status_code == 401:
        raise MXRouteError("Authentication failed. Check username and password.")
      elif response.status_code == 403:
        raise MXRouteError("Access forbidden. Check permissions.")
      elif response.status_code == 404:
        raise MXRouteError("Resource not found. Check server URL and endpoint.")
      elif not response.ok:
        raise MXRouteError(f"HTTP {response.status_code}: {response.text}")
      
      return response
      
    except requests.exceptions.Timeout:
      raise MXRouteError(f"Request timed out after {self.timeout} seconds")
    except requests.exceptions.ConnectionError as e:
      raise MXRouteError(f"Connection error: {str(e)}")
    except requests.exceptions.RequestException as e:
      raise MXRouteError(f"Request failed: {str(e)}")

  def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
    """Parse JSON response with error handling."""
    try:
      return response.json()
    except ValueError as e:
      logger.error(f"Failed to parse JSON response: {response.text}")
      raise MXRouteError(f"Invalid JSON response: {str(e)}")

  def list_domains(self) -> Set[str]:
    """List all domains available in the account."""
    try:
      url = f'{self.server}/CMD_API_SHOW_DOMAINS?json=yes'
      response = self._make_request('GET', url)
      data = self._parse_json_response(response)
      
      # Handle different possible response formats
      if isinstance(data, list):
        domains = set(data)
      elif isinstance(data, dict):
        # Some APIs return domains in different keys
        domains = set()
        for key, value in data.items():
          if isinstance(value, list):
            domains.update(value)
          elif isinstance(value, str):
            domains.add(value)
      else:
        logger.warning(f"Unexpected response format: {type(data)}")
        domains = set()
      
      logger.info(f"Retrieved {len(domains)} domains from MXRoute")
      return domains
      
    except Exception as e:
      logger.error(f"Failed to list domains: {str(e)}")
      raise MXRouteError(f"Failed to retrieve domains: {str(e)}") from e

  def list_forwarders(self, email_domain: str) -> Set[str]:
    """List all forwarders for a specific domain."""
    if not email_domain:
      raise ValueError("Domain is required")
    
    try:
      url = f'{self.server}/CMD_API_EMAIL_FORWARDERS?domain={email_domain}&json=yes'
      response = self._make_request('GET', url)
      data = self._parse_json_response(response)
      
      emails = set()
      
      # Handle different response formats
      if isinstance(data, dict):
        for key, value in data.items():
          if isinstance(value, list):
            emails.update(value)
          elif isinstance(value, str):
            emails.add(value)
      elif isinstance(data, list):
        emails.update(data)
      
      logger.debug(f"Retrieved {len(emails)} forwarders for domain {email_domain}")
      return emails
      
    except Exception as e:
      logger.error(f"Failed to list forwarders for domain {email_domain}: {str(e)}")
      raise MXRouteError(f"Failed to retrieve forwarders for domain {email_domain}: {str(e)}") from e

  def add_forwarder(self, domain: str, user: str, email: str) -> Dict[str, Any]:
    """Add a new email forwarder."""
    if not all([domain, user, email]):
      raise ValueError("Domain, user, and email are required")
    
    if '@' not in email:
      raise ValueError("Invalid email format")
    
    try:
      url = f'{self.server}/CMD_EMAIL_FORWARDER?json=yes'
      headers = {'Content-Type': 'application/json'}
      payload = {
        'action': 'create',
        'domain': domain,
        'user': user,
        'email': email,
        'create': 'Create'
      }
      
      logger.debug(f"Adding forwarder: {user}@{domain} -> {email}")
      response = self._make_request('POST', url, headers=headers, json=payload)
      result = self._parse_json_response(response)
      
      # Check if the operation was successful
      if isinstance(result, dict):
        if result.get('error') == '0' or result.get('success'):
          logger.info(f"Successfully added forwarder: {user}@{domain} -> {email}")
        else:
          error_msg = result.get('text', 'Unknown error')
          raise MXRouteError(f"Failed to add forwarder: {error_msg}")
      
      return result
      
    except Exception as e:
      if isinstance(e, MXRouteError):
        raise
      logger.error(f"Failed to add forwarder {user}@{domain} -> {email}: {str(e)}")
      raise MXRouteError(f"Failed to add forwarder: {str(e)}") from e

  def delete_forwarder(self, domain: str, user: str) -> Dict[str, Any]:
    """Delete an email forwarder."""
    if not all([domain, user]):
      raise ValueError("Domain and user are required")
    
    try:
      url = f'{self.server}/CMD_EMAIL_FORWARDER?json=yes'
      headers = {'Content-Type': 'application/json'}
      payload = {
        'action': 'delete',
        'domain': domain,
        'user': user,
        'delete': 'Delete'
      }
      
      logger.debug(f"Deleting forwarder: {user}@{domain}")
      response = self._make_request('POST', url, headers=headers, json=payload)
      result = self._parse_json_response(response)
      
      # Check if the operation was successful
      if isinstance(result, dict):
        if result.get('error') == '0' or result.get('success'):
          logger.info(f"Successfully deleted forwarder: {user}@{domain}")
        else:
          error_msg = result.get('text', 'Unknown error')
          raise MXRouteError(f"Failed to delete forwarder: {error_msg}")
      
      return result
      
    except Exception as e:
      if isinstance(e, MXRouteError):
        raise
      logger.error(f"Failed to delete forwarder {user}@{domain}: {str(e)}")
      raise MXRouteError(f"Failed to delete forwarder: {str(e)}") from e

  def test_connection(self) -> bool:
    """Test the connection to MXRoute API."""
    try:
      self.list_domains()
      logger.info("MXRoute connection test successful")
      return True
    except Exception as e:
      logger.error(f"MXRoute connection test failed: {str(e)}")
      return False