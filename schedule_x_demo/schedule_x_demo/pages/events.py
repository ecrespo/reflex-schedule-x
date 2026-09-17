"""Events page: create / update / delete events from Python and log every callback."""

from __future__ import annotations

import datetime as dt
import random
from typing import Any

import reflex as rx

from reflex_schedule_x import (
    calendar_event,
    parse_sx_datetime,
    schedule_x,
    schedule_x_date_picker,
    schedule_x_time_picker,
    to_sx_datetime,
)

from ..data import CALENDARS, TODAY, sample_events
from ..layout import card, code, labeled, log_panel, page

TITLES = ["Design review", "Customer call", "Focus time", "Team lunch", "Workshop", "Pairing", "Interview", "Yoga"]


class EventsState(rx.State):
    """State of the events page."""

    events: list[dict[str, Any]] = sample_events()
    log: list[str] = []
    selected: dict[str, Any] = {}
    counter: int = 100

    # form
    title: str = "New meeting"
    calendar_id: str = "work"
    date: str = TODAY.isoformat()
    start_time: str = "10:00"
    end_time: str = "11:00"
    all_day: bool = False
    location: str = ""
    description: str = ""

    # lazy loading
    backend_loading: bool = False
    loaded_ranges: int = 0
    current_range: dict[str, str] = {}

    def _log(self, name: str, payload: Any) -> None:
        stamp = dt.datetime.now().strftime("%H:%M:%S")
        self.log = [f"{stamp}  {name}: {payload}", *self.log][:60]

    @rx.var
    def has_selection(self) -> bool:
        return bool(self.selected)

    @rx.var
    def selected_people(self) -> str:
        return ", ".join(self.selected.get("people", []) or []) or "—"

    @rx.var
    def event_count(self) -> int:
        return len(self.events)

    # ---- form setters --------------------------------------------------
    @rx.event
    def set_title(self, value: str):
        self.title = value

    @rx.event
    def set_calendar_id(self, value: str):
        self.calendar_id = value

    @rx.event
    def set_date(self, value: str):
        self.date = value

    @rx.event
    def set_start_time(self, value: str):
        self.start_time = value

    @rx.event
    def set_end_time(self, value: str):
        self.end_time = value

    @rx.event
    def set_all_day(self, value: bool):
        self.all_day = value

    @rx.event
    def set_location(self, value: str):
        self.location = value

    @rx.event
    def set_description(self, value: str):
        self.description = value

    @rx.event
    def set_backend_loading(self, value: bool):
        self.backend_loading = value
        if not value:
            self.events = sample_events()
        elif self.current_range:
            self.events = self._fake_backend(self.current_range["start"], self.current_range["end"])
            self.loaded_ranges += 1

    # ---- CRUD ----------------------------------------------------------
    @rx.event
    def add_event(self):
        """Add the event described by the form."""
        self.counter += 1
        if self.all_day:
            start: Any = dt.date.fromisoformat(self.date)
            end: Any = start
        else:
            start = dt.datetime.fromisoformat(f"{self.date}T{self.start_time}")
            end = dt.datetime.fromisoformat(f"{self.date}T{self.end_time}")
            if end <= start:
                return rx.toast.error("The end time must be after the start time.")
        event = calendar_event(
            f"n{self.counter}", start, end, self.title or "Untitled",
            calendar_id=self.calendar_id,
            location=self.location or None,
            description=self.description or None,
        )  # fmt: skip
        self.events = [*self.events, event]
        self._log("add_event (state)", event["title"])
        return rx.toast.success(f"Added “{event['title']}”")

    @rx.event
    def delete_selected(self):
        """Remove the selected event."""
        event_id = self.selected.get("id")
        self.events = [e for e in self.events if e["id"] != event_id]
        self._log("delete (state)", event_id)
        self.selected = {}

    @rx.event
    def shift_selected(self, days: int = 0, hours: int = 0):
        """Move the selected event."""
        event_id = self.selected.get("id")
        updated: list[dict[str, Any]] = []
        for event in self.events:
            if event["id"] == event_id:
                event = dict(event)
                for key in ("start", "end"):
                    value = parse_sx_datetime(event[key])
                    delta = dt.timedelta(days=days, hours=hours if isinstance(value, dt.datetime) else 0)
                    event[key] = to_sx_datetime(value + delta)
                self.selected = {**self.selected, "start": event["start"], "end": event["end"]}
            updated.append(event)
        self.events = updated
        self._log("shift (state)", f"{event_id} {days:+d}d {hours:+d}h")

    @rx.event
    def recolor_selected(self, calendar_id: str):
        """Move the selected event to another calendar."""
        event_id = self.selected.get("id")
        self.events = [{**e, "calendarId": calendar_id} if e["id"] == event_id else e for e in self.events]
        self.selected = {**self.selected, "calendarId": calendar_id}

    @rx.event
    def clear_log(self):
        self.log = []

    # ---- calendar callbacks --------------------------------------------
    @rx.event
    def on_event_click(self, event: dict[str, Any]):
        self.selected = event
        self._log("on_event_click", f"{event.get('title')} ({event.get('start')} → {event.get('end')})")

    @rx.event
    def on_double_click_event(self, event: dict[str, Any]):
        self._log("on_double_click_event", event.get("title"))

    def _prefill(self, value: str) -> None:
        date, time = value.split(" ")
        hour = int(time[:2])
        self.date, self.all_day = date, False
        self.start_time, self.end_time = f"{hour:02d}:00", f"{min(hour + 1, 23):02d}:{'00' if hour < 23 else '59'}"

    @rx.event
    def on_click_date_time(self, value: str):
        self._log("on_click_date_time", value)
        self._prefill(value)

    @rx.event
    def on_double_click_date_time(self, value: str):
        self._log("on_double_click_date_time", value)
        self._prefill(value)
        return EventsState.add_event

    @rx.event
    def on_click_date(self, value: str):
        self._log("on_click_date", value)
        self.date, self.all_day = value, True

    @rx.event
    def on_double_click_date(self, value: str):
        self._log("on_double_click_date", value)

    @rx.event
    def on_click_agenda_date(self, value: str):
        self._log("on_click_agenda_date", value)

    @rx.event
    def on_click_plus_events(self, value: str):
        self._log("on_click_plus_events", value)

    @rx.event
    def on_selected_date_update(self, value: str):
        self._log("on_selected_date_update", value)

    @rx.event
    def on_view_change(self, value: str):
        self._log("on_view_change", value)

    @rx.event
    def on_calendar_render(self, info: dict[str, Any]):
        self._log("on_calendar_render", info)
        if info.get("range"):
            self.current_range = info["range"]

    @rx.event
    def on_range_update(self, date_range: dict[str, str]):
        self._log("on_range_update", f"{date_range['start']} → {date_range['end']}")
        self.current_range = date_range
        if self.backend_loading:
            self.events = self._fake_backend(date_range["start"], date_range["end"])
            self.loaded_ranges += 1

    def _fake_backend(self, start: str, end: str) -> list[dict[str, Any]]:
        """Pretend to query a database for the visible range."""
        first = parse_sx_datetime(start[:10])
        last = parse_sx_datetime(end[:10])
        rng = random.Random(f"{first}{last}")
        events: list[dict[str, Any]] = []
        current = first
        while current <= last:
            for n in range(rng.randint(0, 3)):
                hour = rng.randint(7, 18)
                begin = dt.datetime(current.year, current.month, current.day, hour, rng.choice([0, 30]))
                events.append(calendar_event(
                    f"db-{current}-{n}", begin, begin + dt.timedelta(minutes=rng.choice([30, 60, 90])),
                    f"{rng.choice(TITLES)} (from backend)", calendar_id=rng.choice(list(CALENDARS)),
                ))  # fmt: skip
            current += dt.timedelta(days=1)
        return events


def form() -> rx.Component:
    return card(
        rx.vstack(
            rx.hstack(rx.icon("calendar-plus", size=18), rx.heading("Create an event", size="3"), align="center"),
            rx.text("Tip: click the time grid (or a month-grid day) to pre-fill the date and time. "
                    "Double-click the time grid to create instantly.", size="1", color_scheme="gray"),
            labeled("Title", rx.input(value=EventsState.title, on_change=EventsState.set_title, width="100%"), width="100%"),
            rx.hstack(
                labeled(
                    "Calendar",
                    rx.select.root(
                        rx.select.trigger(),
                        rx.select.content(*[rx.select.item(c["label"], value=k) for k, c in CALENDARS.items()]),
                        value=EventsState.calendar_id,
                        on_change=EventsState.set_calendar_id,
                    ),
                ),
                rx.hstack(rx.switch(checked=EventsState.all_day, on_change=EventsState.set_all_day),
                          rx.text("All day", size="2"), align="center", padding_top="1.2rem"),
                spacing="4",
            ),
            schedule_x_date_picker(value=EventsState.date, on_change=EventsState.set_date, label="Date",
                                   full_width=True, dark=rx.color_mode_cond(light=False, dark=True)),
            rx.cond(
                EventsState.all_day,
                rx.fragment(),
                rx.hstack(
                    schedule_x_time_picker(value=EventsState.start_time, on_change=EventsState.set_start_time,
                                           label="Start", dark=rx.color_mode_cond(light=False, dark=True)),
                    schedule_x_time_picker(value=EventsState.end_time, on_change=EventsState.set_end_time,
                                           label="End", dark=rx.color_mode_cond(light=False, dark=True)),
                    spacing="3",
                ),
            ),
            labeled("Location", rx.input(value=EventsState.location, on_change=EventsState.set_location, width="100%"),
                    width="100%"),
            labeled("Description", rx.text_area(value=EventsState.description, on_change=EventsState.set_description,
                                                width="100%"), width="100%"),
            rx.button(rx.icon("plus", size=16), "Add event", on_click=EventsState.add_event, width="100%"),
            spacing="3",
            width="100%",
        ),
    )  # fmt: skip


def details() -> rx.Component:
    return card(
        rx.cond(
            EventsState.has_selection,
            rx.vstack(
                rx.hstack(rx.icon("mouse-pointer-click", size=18), rx.heading(EventsState.selected["title"].to(str), size="3"),
                          align="center"),
                rx.text(EventsState.selected["start"].to(str), " → ", EventsState.selected["end"].to(str), size="2"),
                rx.text("Calendar: ", rx.code(EventsState.selected["calendarId"].to(str)), size="2"),
                rx.text("Location: ", EventsState.selected["location"].to(str), size="2"),
                rx.text("People: ", EventsState.selected_people, size="2"),
                rx.hstack(
                    rx.button("-1 day", size="1", variant="soft", on_click=EventsState.shift_selected(-1, 0)),
                    rx.button("+1 day", size="1", variant="soft", on_click=EventsState.shift_selected(1, 0)),
                    rx.button("-1 h", size="1", variant="soft", on_click=EventsState.shift_selected(0, -1)),
                    rx.button("+1 h", size="1", variant="soft", on_click=EventsState.shift_selected(0, 1)),
                    wrap="wrap",
                ),
                rx.hstack(
                    *[rx.button(c["label"], size="1", variant="outline", on_click=EventsState.recolor_selected(k))
                      for k, c in CALENDARS.items()],
                    wrap="wrap",
                ),
                rx.button(rx.icon("trash-2", size=14), "Delete", color_scheme="red", size="2",
                          on_click=EventsState.delete_selected),
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.hstack(rx.icon("mouse-pointer-click", size=18), rx.heading("Selected event", size="3"), align="center"),
                rx.text("Click an event in the calendar to inspect, move, recolor or delete it.", size="2",
                        color_scheme="gray"),
            ),
        )
    )  # fmt: skip


CODE = """
class State(rx.State):
    events: list[dict] = []

    @rx.event
    def add_event(self):
        self.events = [*self.events, calendar_event("n1", datetime(2026, 9, 17, 10), datetime(2026, 9, 17, 11), "Meeting")]

    @rx.event
    def on_event_click(self, event: dict):   # {'id', 'title', 'start': 'YYYY-MM-DD HH:mm', ...}
        self.selected = event

    @rx.event
    def on_range_update(self, date_range: dict):   # lazy-load events for the visible range
        self.events = load_from_db(date_range["start"], date_range["end"])

schedule_x(
    events=State.events,
    on_event_click=State.on_event_click,
    on_double_click_event=State.on_double_click_event,
    on_click_date_time=State.on_click_date_time,       # week/day grid -> 'YYYY-MM-DD HH:mm'
    on_double_click_date_time=State.on_double_click_date_time,
    on_click_date=State.on_click_date,                 # month grid -> 'YYYY-MM-DD'
    on_click_agenda_date=State.on_click_agenda_date,
    on_click_plus_events=State.on_click_plus_events,
    on_selected_date_update=State.on_selected_date_update,
    on_view_change=State.on_view_change,
    on_range_update=State.on_range_update,
    on_calendar_render=State.on_calendar_render,
)
"""


@rx.page(route="/events", title="Events & callbacks · reflex-schedule-x")
def events_page() -> rx.Component:
    return page(
        "Events & callbacks",
        "Events live in Reflex state: add, move, recolor and delete them from Python. Every Schedule-X callback "
        "arrives as a typed event handler.",
        rx.hstack(
            rx.switch(
                checked=EventsState.backend_loading, on_change=EventsState.set_backend_loading, id="backend-switch"
            ),
            rx.text("Load events from a (simulated) backend on every range change", size="2"),
            rx.badge(EventsState.event_count, " events in state"),
            rx.cond(
                EventsState.backend_loading, rx.badge(EventsState.loaded_ranges, " ranges loaded", color_scheme="green")
            ),
            align="center",
            wrap="wrap",
        ),
        rx.grid(
            rx.box(
                schedule_x(
                    events=EventsState.events,
                    calendars=CALENDARS,
                    views=["week", "day", "month-grid", "month-agenda"],
                    default_view="week",
                    is_dark=rx.color_mode_cond(light=False, dark=True),
                    initial_scroll="08:00",
                    on_event_click=EventsState.on_event_click,
                    on_double_click_event=EventsState.on_double_click_event,
                    on_click_date_time=EventsState.on_click_date_time,
                    on_double_click_date_time=EventsState.on_double_click_date_time,
                    on_click_date=EventsState.on_click_date,
                    on_double_click_date=EventsState.on_double_click_date,
                    on_click_agenda_date=EventsState.on_click_agenda_date,
                    on_click_plus_events=EventsState.on_click_plus_events,
                    on_selected_date_update=EventsState.on_selected_date_update,
                    on_view_change=EventsState.on_view_change,
                    on_range_update=EventsState.on_range_update,
                    on_calendar_render=EventsState.on_calendar_render,
                    id="events-calendar",
                    height="760px",
                ),
                min_width="0",
            ),
            rx.vstack(details(), form(), spacing="3", width="100%"),
            columns=rx.breakpoints(initial="1", lg="minmax(0, 1fr) 340px"),
            spacing="4",
            width="100%",
        ),
        log_panel(EventsState.log, EventsState.clear_log),
        code(CODE),
    )
