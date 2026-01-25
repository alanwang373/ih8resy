"""
Filter models and validation for restaurant search.
"""

from dataclasses import dataclass, field
from datetime import date, time as datetime_time
from typing import Optional


@dataclass
class SearchFilters:
    """User-defined filters for restaurant availability search."""
    
    # Location
    location: str = "New York"
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius: Optional[int] = 2  # Miles
    
    # Cuisine preferences
    cuisines: list[str] = field(default_factory=list)
    
    # Date and time
    date: str = ""
    time_start: str = "18:00"
    time_end: str = "21:00"
    
    # Party details
    party_size: int = 2
    
    # Seating preferences
    seating_types: list[str] = field(default_factory=list)  # indoor, outdoor, bar
    
    # Optional vibes/tags
    vibes: list[str] = field(default_factory=list)
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate filter configuration."""
        if not self.date:
            return False, "Date is required"
        
        if self.party_size < 1 or self.party_size > 20:
            return False, "Party size must be between 1 and 20"
        
        try:
            start_h, start_m = map(int, self.time_start.split(":"))
            end_h, end_m = map(int, self.time_end.split(":"))
            
            if not (0 <= start_h < 24 and 0 <= start_m < 60):
                return False, "Invalid start time format"
            if not (0 <= end_h < 24 and 0 <= end_m < 60):
                return False, "Invalid end time format"
            
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            
            if start_minutes >= end_minutes:
                return False, "End time must be after start time"
        
        except (ValueError, IndexError):
            return False, "Time must be in HH:MM format"
        
        return True, None
    
    def __str__(self) -> str:
        """Human-readable summary of filters."""
        parts = [
            f"Location: {self.location}",
            f"Date: {self.date}",
            f"Time: {self.time_start} - {self.time_end}",
            f"Party size: {self.party_size}"
        ]
        
        if self.cuisines:
            parts.append(f"Cuisines: {', '.join(self.cuisines)}")
        
        if self.seating_types:
            parts.append(f"Seating: {', '.join(self.seating_types)}")
        
        if self.vibes:
            parts.append(f"Vibes: {', '.join(self.vibes)}")
        
        return " | ".join(parts)


# Common cuisine types for UI dropdowns
COMMON_CUISINES = [
    "Italian",
    "Japanese",
    "French",
    "American",
    "Mexican",
    "Chinese",
    "Indian",
    "Thai",
    "Mediterranean",
    "Steakhouse",
    "Seafood",
    "Korean",
    "Spanish",
    "Vietnamese",
    "Contemporary",
    "Farm-to-Table"
]

# Seating types
SEATING_TYPES = [
    "Indoor",
    "Outdoor",
    "Bar"
]

# Vibe tags
COMMON_VIBES = [
    "Romantic",
    "Lively",
    "Quiet",
    "Tasting Menu",
    "Date Night",
    "Special Occasion",
    "Casual",
    "Upscale"
]

# Time slots for slider (15-min increments from 10 AM to 10 PM)
TIME_SLOTS = []
for hour in range(10, 22):
    for minute in [0, 15, 30, 45]:
        TIME_SLOTS.append(f"{hour:02d}:{minute:02d}")
TIME_SLOTS.append("22:00")