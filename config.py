"""
Configuration and secrets management for Resy dashboard.
Reads from environment variables (injected from GitHub secrets or GCP Secret Manager).
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResyConfig:
    """Resy API configuration."""
    
    api_key: str
    auth_token: str
    universal_auth: str
    
    # Rate limiting
    requests_per_second: float = 0.5  # Conservative: 1 req every 2 seconds
    max_concurrent_venues: int = 5
    
    # Polling behavior
    poll_interval_seconds: int = 30  # Check each venue every 30s
    discovery_cache_minutes: int = 60  # Re-discover venues hourly
    
    # API endpoints
    base_url: str = "https://api.resy.com"
    
    @classmethod
    def from_env(cls) -> "ResyConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("RESY_API_KEY")
        auth_token = os.getenv("X_RESY_AUTH_TOKEN")
        universal_auth = os.getenv("X_RESY_UNIVERSAL_AUTH")
        
        if not api_key:
            raise ValueError("RESY_API_KEY environment variable is required")
        if not auth_token:
            raise ValueError("X_RESY_AUTH_TOKEN environment variable is required")
        if not universal_auth:
            raise ValueError("X_RESY_UNIVERSAL_AUTH environment variable is required")
        
        return cls(
            api_key=api_key,
            auth_token=auth_token,
            universal_auth=universal_auth
        )
    
    def get_headers(self) -> dict[str, str]:
        """Generate HTTP headers for Resy API calls."""
        return {
            "authorization": f'ResyAPI api_key="{self.api_key}"',
            "x-resy-auth-token": self.auth_token,
            "x-resy-universal-auth": self.universal_auth,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "accept": "application/json, text/plain, */*",
            "origin": "https://resy.com",
            "referer": "https://resy.com/",
        }


# Global config instance (lazy-loaded)
_config: Optional[ResyConfig] = None


def get_config() -> ResyConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = ResyConfig.from_env()
    return _config