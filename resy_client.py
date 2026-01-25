"""
Resy API client for venue discovery and availability polling.
"""

import httpx
from typing import Optional, Any
from datetime import date, time
from dataclasses import dataclass, field
from config import get_config


@dataclass
class TimeSlot:
    """Represents an available reservation slot."""
    venue_id: str
    venue_name: str
    date: str
    time: str
    party_size: int
    config_id: str
    seating_type: Optional[str] = None
    
    def to_booking_url(self) -> str:
        """Generate direct Resy booking URL with config token."""
        return f"https://resy.com/checkout?config_id={self.config_id}&date={self.date}&party_size={self.party_size}"


@dataclass
class Venue:
    """Restaurant venue metadata."""
    id: str
    name: str
    cuisine: str
    neighborhood: str
    rating: Optional[float] = None
    price_tier: Optional[int] = None  # 1-4 for $-$$$$
    available_slots: list[TimeSlot] = field(default_factory=list)
    
    def to_resy_url(self) -> str:
        """Generate restaurant page URL."""
        slug = self.name.lower().replace(' ', '-').replace("'", '').replace('.', '')
        return f"https://resy.com/cities/ny/{slug}"
    
    def price_display(self) -> str:
        """Convert price tier to $$$$."""
        if not self.price_tier:
            return ""
        return "$" * min(self.price_tier, 4)
    
    def star_display(self) -> str:
        """Format rating as stars."""
        if not self.rating:
            return ""
        return f"★ {self.rating:.1f}"


class GeocodingService:
    """Geocode locations using Nominatim (OpenStreetMap)."""
    
    @staticmethod
    async def geocode(location: str) -> Optional[tuple[float, float]]:
        """Convert location string to lat/lon coordinates."""
        async with httpx.AsyncClient() as client:
            try:
                if location.isdigit() and len(location) == 5:
                    location = f"{location}, New York, NY"
                elif "," not in location and not any(c.isdigit() for c in location):
                    location = f"{location}, New York, NY"
                
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location, "format": "json", "limit": 1},
                    headers={"User-Agent": "ResyDashboard/1.0"}
                )
                
                data = response.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    print(f"✓ Geocoded '{location}' to ({lat:.4f}, {lon:.4f})")
                    return (lat, lon)
                
                return None
            
            except Exception as e:
                print(f"Geocoding failed: {e}")
                return None


class ResyClient:
    """HTTP client for Resy API with auth headers."""
    
    def __init__(self):
        self.config = get_config()
        self.client = httpx.AsyncClient(
            headers=self.config.get_headers(),
            timeout=30.0,
            follow_redirects=True
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make authenticated request to Resy API."""
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            
            if response.status_code in (401, 403):
                raise AuthenticationError("Resy auth token expired or invalid")
            
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            raise ResyAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise ResyAPIError(f"Request failed: {str(e)}")
    
    async def search_venues(
        self,
        location: str,
        cuisines: Optional[list[str]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None
    ) -> list[Venue]:
        """Discover venues matching location filters."""
        if not lat or not lon:
            coords = await GeocodingService.geocode(location)
            if coords:
                lat, lon = coords
        
        # The Smith locations with full metadata
        smith_venues = [
            Venue(
                id="86507",
                name="The Smith",
                cuisine="American",
                neighborhood="Midtown West",
                rating=4.5,
                price_tier=2
            ),
            Venue(
                id="87193",
                name="The Smith",
                cuisine="American",
                neighborhood="NoMad",
                rating=4.6,
                price_tier=2
            ),
            Venue(
                id="87191",
                name="The Smith",
                cuisine="American",
                neighborhood="Lincoln Square",
                rating=4.5,
                price_tier=2
            ),
            Venue(
                id="87192",
                name="The Smith",
                cuisine="American",
                neighborhood="East Village",
                rating=4.7,
                price_tier=2
            ),
        ]
        
        print(f"✓ Monitoring {len(smith_venues)} venues")
        return smith_venues
    
    async def get_availability(
        self,
        venue_id: str,
        date: str,
        party_size: int,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        seating_types: Optional[list[str]] = None
    ) -> list[TimeSlot]:
        """Check availability for a specific venue."""
        params = {
            "venue_id": venue_id,
            "day": date,
            "party_size": party_size,
            "lat": 40.7128,
            "long": -74.0060
        }
        
        try:
            data = await self._request("GET", "/4/find", params=params)
            
            venues_data = data.get("results", {}).get("venues", [])
            if not venues_data:
                return []
            
            venue_data = venues_data[0]
            venue_name = venue_data.get("venue", {}).get("name", "Unknown")
            raw_slots = venue_data.get("slots", [])
            
            slots = []
            for slot in raw_slots:
                slot_datetime = slot["date"]["start"]
                slot_time = slot_datetime.split(" ")[1][:5]
                
                # Filter by time window
                if time_start and slot_time < time_start:
                    continue
                if time_end and slot_time > time_end:
                    continue
                
                # Extract seating type
                seating_type = "Indoor"
                config = slot.get("config", {})
                table_type = config.get("type", "").lower()
                
                if "outdoor" in table_type or "patio" in table_type:
                    seating_type = "Outdoor"
                elif "bar" in table_type or "counter" in table_type:
                    seating_type = "Bar"
                
                # Filter by seating type if specified
                if seating_types and seating_type not in seating_types:
                    continue
                
                slots.append(TimeSlot(
                    venue_id=venue_id,
                    venue_name=venue_name,
                    date=date,
                    time=slot_time,
                    party_size=party_size,
                    config_id=config["token"],
                    seating_type=seating_type
                ))
            
            return slots
        
        except Exception as e:
            print(f"Error checking venue {venue_id}: {e}")
            return []


class ResyAPIError(Exception):
    """General Resy API error."""
    pass


class AuthenticationError(ResyAPIError):
    """Auth token expired or invalid."""
    pass