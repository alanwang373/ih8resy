"""
NiceGUI dashboard for Resy availability polling.
Redesigned to match Resy's UI aesthetic.
"""

from dotenv import load_dotenv
load_dotenv()

from nicegui import ui
from datetime import date
from filters import SearchFilters, SEATING_TYPES, TIME_SLOTS
from poller import AvailabilityPoller
from resy_client import Venue


class ResyDashboard:
    """Main dashboard application."""
    
    def __init__(self):
        self.filters = SearchFilters()
        self.poller = None
        self.venues_with_availability = []
        
        self.status_label = None
        self.stats_label = None
        self.start_button = None
        self.stop_button = None
        self.results_container = None
        self.stats_timer = None
        self.event_timer = None
        self.time_label = None
    
    def process_events(self):
        """Process events from the poller queue."""
        if not self.poller:
            return
        
        for _ in range(10):
            event = self.poller.get_event()
            if not event:
                break
            
            if event.type == "venues":
                self._handle_venues(event.data)
            elif event.type == "status":
                self._handle_status(event.data)
            elif event.type == "error":
                self._handle_error(event.data)
    
    def _handle_venues(self, venues: list[Venue]):
        """Handle venue availability update."""
        self.venues_with_availability = venues
        self.refresh_results()
    
    def _handle_status(self, status: str):
        """Handle status update."""
        if self.status_label:
            self.status_label.set_text(status)
    
    def _handle_error(self, error: str):
        """Handle error."""
        ui.notify(f"Error: {error}", type="negative")
    
    def refresh_stats(self):
        """Update statistics display."""
        if self.poller and self.stats_label:
            stats = self.poller.get_stats()
            self.stats_label.set_text(
                f"Venues: {stats['venues']} | "
                f"Polls: {stats['polls']} | "
                f"Tables: {stats['matches']} | "
                f"Errors: {stats['errors']}"
            )
    
    def refresh_results(self):
        """Refresh results display with Resy-style cards."""
        if not self.results_container:
            return
        
        self.results_container.clear()
        
        with self.results_container:
            if not self.venues_with_availability:
                with ui.card().classes("w-full p-8 text-center"):
                    ui.label("No tables available yet...").classes("text-gray-500 text-lg")
                    ui.label("Try adjusting your filters or wait for availability").classes("text-gray-400 text-sm")
                return
            
            for venue in self.venues_with_availability:
                self._render_venue_card(venue)
    
    def _render_venue_card(self, venue: Venue):
        """Render a single venue card with Resy styling."""
        with ui.card().classes("w-full mb-4 hover:shadow-lg transition-shadow"):
            # Header: Restaurant name, rating, price
            with ui.row().classes("w-full items-center justify-between mb-3"):
                with ui.column().classes("gap-1"):
                    ui.link(venue.name, venue.to_resy_url(), new_tab=True).classes(
                        "text-xl font-bold text-gray-900 no-underline hover:text-primary"
                    )
                    
                    with ui.row().classes("gap-3 items-center"):
                        ui.label(venue.cuisine).classes("text-sm text-gray-600")
                        ui.label("•").classes("text-gray-400")
                        ui.label(venue.neighborhood).classes("text-sm text-gray-600")
                
                with ui.row().classes("gap-2 items-center"):
                    if venue.rating:
                        ui.label(venue.star_display()).classes("text-sm font-semibold text-gray-700")
                    if venue.price_tier:
                        ui.label(venue.price_display()).classes("text-sm font-semibold text-gray-700")
            
            # Table count
            ui.label(f"{len(venue.available_slots)} tables available").classes(
                "text-sm font-medium text-green-600 mb-3"
            )
            
            # Time slots grid
            with ui.row().classes("gap-2 flex-wrap"):
                # Group by seating type
                slots_by_type = {}
                for slot in venue.available_slots:
                    seating = slot.seating_type or "Indoor"
                    if seating not in slots_by_type:
                        slots_by_type[seating] = []
                    slots_by_type[seating].append(slot)
                
                # Render slots
                for slot in sorted(venue.available_slots, key=lambda s: s.time):
                    self._render_time_slot(slot)
    
    def _render_time_slot(self, slot):
        """Render a clickable time slot button."""
        # Convert to 12-hour format
        hour, minute = map(int, slot.time.split(":"))
        period = "PM" if hour >= 12 else "AM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        time_display = f"{display_hour}:{minute:02d} {period}"
        
        # Seating icon
        seating_icon = ""
        if slot.seating_type == "Outdoor":
            seating_icon = "🌳 "
        elif slot.seating_type == "Bar":
            seating_icon = "🍸 "
        
        with ui.button(
            on_click=lambda s=slot: ui.open(s.to_booking_url(), new_tab=True)
        ).props("outline").classes("px-4 py-2"):
            with ui.column().classes("items-center gap-0"):
                ui.label(f"{seating_icon}{time_display}").classes("text-sm font-medium")
                if slot.seating_type and slot.seating_type != "Indoor":
                    ui.label(slot.seating_type).classes("text-xs text-gray-500")
    
    async def start_polling(self):
        """Start the poller."""
        is_valid, error = self.filters.validate()
        if not is_valid:
            ui.notify(f"Invalid filters: {error}", type="negative")
            return
        
        self.venues_with_availability.clear()
        self.refresh_results()
        
        self.poller = AvailabilityPoller(filters=self.filters)
        await self.poller.start()
        
        if self.start_button and self.stop_button:
            self.start_button.disable()
            self.stop_button.enable()
        
        if not self.stats_timer:
            self.stats_timer = ui.timer(2.0, self.refresh_stats)
        if not self.event_timer:
            self.event_timer = ui.timer(0.1, self.process_events)
    
    async def stop_polling(self):
        """Stop the poller."""
        if self.poller:
            await self.poller.stop()
            self.poller = None
        
        if self.start_button and self.stop_button:
            self.start_button.enable()
            self.stop_button.disable()
        
        if self.stats_timer:
            self.stats_timer.cancel()
            self.stats_timer = None
        
        if self.event_timer:
            self.event_timer.cancel()
            self.event_timer = None
        
        if self.status_label:
            self.status_label.set_text("Stopped")


dashboard = ResyDashboard()


@ui.page("/")
def index():
    """Main page route."""
    ui.add_head_html('<style>.nicegui-content { max-width: 100% !important; }</style>')
    
    with ui.row().classes("w-full min-h-screen bg-gray-50"):
        # Left sidebar - filters
        with ui.column().classes("w-96 bg-white border-r border-gray-200 p-6 gap-4"):
            ui.label("🍽️ Resy Finder").classes("text-2xl font-bold mb-4")
            
            # Date
            today = date.today()
            ui.label("Date").classes("text-sm font-semibold text-gray-700")
            ui.date(
                value=today.isoformat(),
                on_change=lambda e: setattr(dashboard.filters, "date", e.value)
            ).classes("w-full")
            
            # Party size
            ui.label("Party Size").classes("text-sm font-semibold text-gray-700 mt-4")
            ui.number(
                value=dashboard.filters.party_size,
                min=1,
                max=20,
                on_change=lambda e: setattr(dashboard.filters, "party_size", int(e.value))
            ).classes("w-full")
            
            # Time slider
            ui.label("Start Time").classes("text-sm font-semibold text-gray-700 mt-4")
            start_idx = TIME_SLOTS.index("18:00")
            
            dashboard.time_label = ui.label("6:00 PM").classes("text-lg font-semibold text-primary mb-2")
            
            time_slider = ui.slider(
                min=0,
                max=len(TIME_SLOTS) - 1,
                value=start_idx,
                step=1
            ).props('label-always').classes("w-full")
            
            def update_time(e):
                idx = int(e.value)
                time_val = TIME_SLOTS[idx]
                hour, minute = map(int, time_val.split(":"))
                period = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                dashboard.time_label.set_text(f"{display_hour}:{minute:02d} {period}")
                setattr(dashboard.filters, "time_start", time_val)
                # Set end time to 3 hours later
                end_idx = min(idx + 12, len(TIME_SLOTS) - 1)
                setattr(dashboard.filters, "time_end", TIME_SLOTS[end_idx])
            
            time_slider.on_value_change(update_time)
            
            # Location
            ui.label("Address or Neighborhood").classes("text-sm font-semibold text-gray-700 mt-4")
            ui.input(
                value=dashboard.filters.location,
                placeholder="ZIP, neighborhood, or address",
                on_change=lambda e: setattr(dashboard.filters, "location", e.value)
            ).classes("w-full")
            
            # Seating type
            ui.label("Seating Type").classes("text-sm font-semibold text-gray-700 mt-4")
            ui.select(
                options=["Any"] + SEATING_TYPES,
                value="Any",
                on_change=lambda e: setattr(
                    dashboard.filters, 
                    "seating_types", 
                    [] if e.value == "Any" else [e.value]
                )
            ).classes("w-full")
            
            ui.separator().classes("my-4")
            
            # Control buttons
            with ui.row().classes("w-full gap-2"):
                dashboard.start_button = ui.button(
                    "Find Tables",
                    on_click=dashboard.start_polling
                ).props("color=primary").classes("flex-1")
                
                dashboard.stop_button = ui.button(
                    "Stop",
                    on_click=dashboard.stop_polling
                ).props("outline").classes("flex-1")
                dashboard.stop_button.disable()
            
            # Status
            with ui.card().classes("w-full mt-4 bg-gray-50"):
                dashboard.status_label = ui.label("Ready").classes("text-sm font-medium")
                dashboard.stats_label = ui.label("").classes("text-xs text-gray-600")
        
        # Main content - results
        with ui.column().classes("flex-1 p-8 gap-4 overflow-y-auto"):
            ui.label("Available Restaurants").classes("text-2xl font-bold mb-4")
            
            dashboard.results_container = ui.column().classes("w-full gap-4 max-w-5xl")
            with dashboard.results_container:
                with ui.card().classes("w-full p-8 text-center"):
                    ui.label("Click 'Find Tables' to start searching").classes("text-gray-500 text-lg")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Resy Finder",
        port=8080,
        reload=False,
        show=True
    )