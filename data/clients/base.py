"""Base HTTP client with retry and error handling."""

import requests
from typing import Optional, Dict, Any
import time
from utils.logging import log

class BaseAPIClient:
    """Base class for API clients with retry logic."""
    
    def __init__(self, base_url: str, default_timeout: int = 10):
        self.base_url = base_url
        self.default_timeout = default_timeout
        self.session = requests.Session()
    
    def get(
        self,
        endpoint: str,
        params: Dict = None,
        headers: Dict = None,
        timeout: int = None,
        retries: int = 2,
        url_override: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make GET request with retry logic.
        
        Args:
            endpoint: API endpoint path (appended to base_url)
            params: Query parameters
            headers: Custom headers
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            url_override: Full URL to use instead of base_url + endpoint
            
        Returns:
            JSON response as dict, or None on failure.
        """
        if url_override:
            url = url_override
        else:
            # Handle slash logic
            base = self.base_url.rstrip('/')
            path = endpoint.lstrip('/')
            url = f"{base}/{path}"
            
        timeout = timeout or self.default_timeout
        
        for attempt in range(retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
                
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = int(response.headers.get('Retry-After', 60))
                    log("WARN", f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    log("WARN", f"API returned {response.status_code}: {url}")
                    return None
                
                return response.json()
                
            except requests.exceptions.Timeout:
                log("WARN", f"Timeout on attempt {attempt + 1}: {url}")
                if attempt < retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            except Exception as e:
                log("ERROR", f"Request failed: {url} - {e}")
                return None
        
        return None
