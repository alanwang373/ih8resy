"""
Async polling engine for Resy availability.
"""

import asyncio
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from queue import Queue
from collections import defaultdict

from resy_client import ResyClient, Venue, TimeSlot, AuthenticationError
from filters import SearchFilters
from config import get_config


@dataclass
class PollerEvent:
    """Event emitted by the poller."""
    type: str  # "venues", "status", "error"
    data: any


@dataclass
class PollerStats:
    """Runtime statistics for the poller."""
    started_at: Optional[datetime] = None
    venues_discovered: int = 0
    total_polls: int = 0
    matches_found: int = 0
    errors: int = 0
    last_error: Optional[str] = None
    is_running: bool = False


class AvailabilityPoller:
    """
    Async poller that discovers venues and continuously checks availability.
    Groups results by venue instead of individual time slots.
    """
    
    def __init__(self, filters: SearchFilters):
        self.filters = filters
        self.event_queue = Queue()
        
        self.client = ResyClient()
        self.config = get_config()
        self.stats = PollerStats()
        
        self._venues: list[Venue] = []
        self._venue_slots: dict[str, list[TimeSlot]] = defaultdict(list)
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    def get_event(self) -> Optional[PollerEvent]:
        """Get next event from queue (non-blocking)."""
        if not self.event_queue.empty():
            return self.event_queue.get_nowait()
        return None
    
    def _emit_event(self, event_type: str, data: any):
        """Emit an event to the queue."""
        self.event_queue.put(PollerEvent(type=event_type, data=data))
    
    async def start(self):
        """Start the polling loop."""
        if self.stats.is_running:
            return
        
        self.stats.is_running = True
        self.stats.started_at = datetime.now()
        self._stop_event.clear()
        
        self._task = asyncio.create_task(self._poll_loop())
    
    async def stop(self):
        """Stop the polling loop gracefully."""
        if not self.stats.is_running:
            return
        
        self.stats.is_running = False
        self._stop_event.set()
        
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        
        await self.client.close()
    
    async def _poll_loop(self):
        """Main polling loop."""
        try:
            self._emit_event("status", "Discovering restaurants...")
            await self._discover_venues()
            
            if not self._venues:
                self._emit_event("status", "No restaurants found")
                self.stats.is_running = False
                return
            
            self._emit_event("status", f"Polling {len(self._venues)} restaurants...")
            
            while not self._stop_event.is_set():
                await self._poll_all_venues()
                await asyncio.sleep(self.config.poll_interval_seconds)
        
        except AuthenticationError as e:
            self.stats.last_error = str(e)
            self.stats.errors += 1
            self._emit_event("status", "⚠️ Auth expired - refresh tokens")
            self.stats.is_running = False
        
        except Exception as e:
            self.stats.last_error = str(e)
            self.stats.errors += 1
            self._emit_event("error", str(e))
            self.stats.is_running = False
            import traceback
            traceback.print_exc()
    
    async def _discover_venues(self):
        """Run venue discovery based on filters."""
        try:
            venues = await self.client.search_venues(
                location=self.filters.location,
                cuisines=self.filters.cuisines if self.filters.cuisines else None,
                lat=self.filters.lat,
                lon=self.filters.lon,
                radius=self.filters.radius
            )
            
            self._venues = venues
            self.stats.venues_discovered = len(venues)
        
        except Exception as e:
            print(f"Venue discovery failed: {e}")
            self.stats.last_error = str(e)
            self.stats.errors += 1
    
    async def _poll_all_venues(self):
        """Poll availability for all venues and emit grouped results."""
        delay_between_requests = 1.0 / self.config.requests_per_second
        
        # Clear previous slots
        self._venue_slots.clear()
        
        for venue in self._venues:
            if self._stop_event.is_set():
                break
            
            try:
                slots = await self.client.get_availability(
                    venue_id=venue.id,
                    date=self.filters.date,
                    party_size=self.filters.party_size,
                    time_start=self.filters.time_start,
                    time_end=self.filters.time_end,
                    seating_types=self.filters.seating_types if self.filters.seating_types else None
                )
                
                self.stats.total_polls += 1
                
                if slots:
                    self._venue_slots[venue.id] = slots
                    venue.available_slots = slots
                    self.stats.matches_found = sum(len(s) for s in self._venue_slots.values())
            
            except Exception as e:
                print(f"Poll failed for venue {venue.id}: {e}")
                self.stats.errors += 1
            
            await asyncio.sleep(delay_between_requests)
        
        # Emit complete venue list with availability
        venues_with_slots = [v for v in self._venues if v.available_slots]
        self._emit_event("venues", venues_with_slots)
    
    def get_stats(self) -> dict:
        """Get current poller statistics."""
        return {
            "running": self.stats.is_running,
            "venues": self.stats.venues_discovered,
            "polls": self.stats.total_polls,
            "matches": self.stats.matches_found,
            "errors": self.stats.errors,
            "last_error": self.stats.last_error,
            "uptime": (
                str(datetime.now() - self.stats.started_at).split(".")[0]
                if self.stats.started_at else "N/A"
            )
        }