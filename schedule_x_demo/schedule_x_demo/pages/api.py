"""Imperative API (rx.call_script) and the list view with lazy loading."""

from __future__ import annotations

import datetime as dt
from typing import Any

import reflex as rx

from reflex_schedule_x import ScheduleXAPI, calendar_event, schedule_x

from ..data import CALENDARS, TODAY, sample_events
from ..layout import card, code, log_panel, page

api = ScheduleXAPI("api-calendar")
list_api = ScheduleXAPI("list-calendar")


class ApiState(rx.State):
    """State of the API page."""

    log: list[str] = []
    counter: int = 0
    list_events: list[dict[str, Any]] = []
    loaded_until: str = ""

    def _log(self, text: str) -> None:
        self.log = [f"{dt.datetime.now().strftime('%H:%M:%S')}  {text}", *self.log][:50]

    @rx.event
    def add_via_api(self):
        self.counter += 1
        start = dt.datetime.combine(TODAY, dt.time(9 + self.counter % 9))
        event = calendar_event(f"api-{self.counter}", start, start + dt.timedelta(hours=1),
                               f"Added via JS API #{self.counter}", calendar_id="school")  # fmt: skip
        self._log(f"api.add_event({event['id']})")
        return api.add_event(event)

    @rx.event
    def receive(self, value: Any):
        if isinstance(value, list):
            titles = ", ".join(str(e.get("title")) for e in value[:5])
            self._log(f"get_events → {len(value)} events: {titles}…")
        else:
            self._log(f"result → {value}")

    # ---- list view lazy loading ------------------------------------------
    @rx.event
    def load_initial(self):
        if not self.list_events:
            self._load_days(TODAY, 21)

    def _load_days(self, first: dt.date, n_days: int) -> None:
        new: list[dict[str, Any]] = []
        for offset in range(n_days):
            current = first + dt.timedelta(days=offset)
            if current.weekday() >= 5:
                continue
            new.append(
                calendar_event(
                    f"list-{current}-a",
                    dt.datetime.combine(current, dt.time(9)),
                    dt.datetime.combine(current, dt.time(10)),
                    f"Morning block · {current:%a %d}",
                    calendar_id="work",
                )
            )
            new.append(
                calendar_event(
                    f"list-{current}-b",
                    dt.datetime.combine(current, dt.time(15)),
                    dt.datetime.combine(current, dt.time(16, 30)),
                    f"Afternoon focus · {current:%a %d}",
                    calendar_id="leisure",
                )
            )
        self.list_events = [*self.list_events, *new]
        self.loaded_until = (first + dt.timedelta(days=n_days - 1)).isoformat()
        self._log(f"loaded {len(new)} list events until {self.loaded_until}")  # fmt: skip

    @rx.event
    def on_scroll_day_into_view(self, date: str):
        """Load two more weeks when the user scrolls close to the end of the loaded data."""
        if not self.loaded_until:
            return
        last = dt.date.fromisoformat(self.loaded_until)
        if dt.date.fromisoformat(date) >= last - dt.timedelta(days=3):
            self._load_days(last + dt.timedelta(days=1), 14)


def api_button(label: str, icon: str, event: Any) -> rx.Component:
    return rx.button(rx.icon(icon, size=14), label, size="2", variant="soft", on_click=event)


CODE = """
api = ScheduleXAPI("api-calendar")          # same id as schedule_x(id=...)

rx.button("Week", on_click=api.set_view("week"))
rx.button("Next month", on_click=api.set_date("2026-10-01"))
rx.button("Dump events", on_click=api.get_events(callback=State.receive))

class State(rx.State):
    @rx.event
    def add_via_api(self):
        return api.add_event(calendar_event("x", datetime(...), datetime(...), "From Python"))

# List view + lazy loading
schedule_x(views=["list"], events=State.list_events, on_scroll_day_into_view=State.on_scroll_day_into_view)
"""


@rx.page(route="/api", title="Imperative API · reflex-schedule-x", on_load=ApiState.load_initial)
def api_page() -> rx.Component:
    return page(
        "Imperative API & list view",
        "ScheduleXAPI wraps the calendar-controls, events-service, scroll-controller and event-modal plugins via "
        "rx.call_script, for cases where you do not want to keep events in state.",
        card(
            rx.vstack(
                rx.hstack(
                    api_button("Day", "calendar-days", api.set_view("day")),
                    api_button("Week", "calendar-range", api.set_view("week")),
                    api_button("Month", "calendar", api.set_view("month-grid")),
                    api_button("Go to next month", "chevrons-right",
                               api.set_date((TODAY.replace(day=1) + dt.timedelta(days=32)).replace(day=1))),
                    api_button("Today", "locate", api.set_date(TODAY)),
                    api_button("Scroll to 18:00", "arrow-down", api.scroll_to("18:00")),
                    api_button("Dark", "moon", api.set_theme("dark")),
                    api_button("Light", "sun", api.set_theme("light")),
                    wrap="wrap",
                ),
                rx.hstack(
                    api_button("Add event (JS API)", "plus", ApiState.add_via_api),
                    api_button("Remove e1 (stand-up)", "trash-2", api.remove_event("e1")),
                    api_button("Get events", "list", api.get_events(callback=ApiState.receive)),
                    api_button("Get view", "eye", api.get_view(callback=ApiState.receive)),
                    api_button("Get date", "calendar-check", api.get_date(callback=ApiState.receive)),
                    api_button("Get range", "move-horizontal", api.get_range(callback=ApiState.receive)),
                    api_button("Close modal", "x", api.close_event_modal()),
                    wrap="wrap",
                ),
            ),
        ),
        rx.grid(
            rx.box(
                schedule_x(
                    events=sample_events(),
                    calendars=CALENDARS,
                    views=["day", "week", "month-grid", "month-agenda"],
                    default_view="week",
                    event_modal=True,
                    initial_scroll="08:00",
                    current_time_indicator=True,
                    current_time_full_week_width=True,
                    id="api-calendar",
                    height="640px",
                ),
                min_width="0",
            ),
            log_panel(ApiState.log),
            columns=rx.breakpoints(initial="1", lg="minmax(0, 1fr) 360px"),
            spacing="4",
            width="100%",
        ),
        rx.heading("List view with lazy loading", size="5", padding_top="1rem"),
        rx.text("Scroll the list: on_scroll_day_into_view loads two more weeks when you approach the end. Loaded until ",
                rx.code(ApiState.loaded_until), size="2", color_scheme="gray"),
        schedule_x(
            events=ApiState.list_events,
            calendars=CALENDARS,
            views=["list"],
            is_dark=rx.color_mode_cond(light=False, dark=True),
            on_scroll_day_into_view=ApiState.on_scroll_day_into_view,
            id="list-calendar",
            height="480px",
        ),
        code(CODE),
    )  # fmt: skip
