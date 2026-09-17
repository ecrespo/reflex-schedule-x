"""Recurrence, background events and iCalendar import."""

from __future__ import annotations

from typing import Any

import reflex as rx

from reflex_schedule_x import background_event, calendar_event, schedule_x

from ..data import CALENDARS, RECURRING_EVENTS, WEEK_START, at, day, ics_sample
from ..layout import card, code, labeled, page

RRULE_PRESETS = {
    "Every weekday": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=20",
    "Every Monday & Wednesday": "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10",
    "Daily, 7 times": "FREQ=DAILY;COUNT=7",
    "Every 2 days, 6 times": "FREQ=DAILY;INTERVAL=2;COUNT=6",
    "Monthly, first Friday": "FREQ=MONTHLY;BYDAY=1FR;COUNT=6",
    "Yearly, 3 times": "FREQ=YEARLY;COUNT=3",
}


class RecurrenceState(rx.State):
    """State of the recurrence page."""

    events: list[dict[str, Any]] = list(RECURRING_EVENTS)
    preset: str = "Every weekday"
    custom_title: str = "Recurring focus block"
    ics: str = ics_sample()
    ics_applied: str = ics_sample()
    counter: int = 0
    show_holidays: bool = True

    @rx.var
    def background_events(self) -> list[dict[str, Any]]:
        stripes = {
            "backgroundImage": "repeating-linear-gradient(45deg, #ccc, #ccc 5px, transparent 5px, transparent 10px)",
            "opacity": 0.5,
        }
        items = [
            background_event(at(0, 0), at(0, 7), {"background": "rgba(100,100,120,.12)"}, "Night (recurring)",
                             rrule="FREQ=DAILY;COUNT=60"),
            background_event(at(0, 19), at(0, 23, 59), {"background": "rgba(100,100,120,.12)"}, "Evening (recurring)",
                             rrule="FREQ=DAILY;COUNT=60"),
        ]  # fmt: skip
        if self.show_holidays:
            items.append(background_event(day(3), day(3), stripes, "Holiday"))
        return items

    @rx.event
    def set_preset(self, value: str):
        self.preset = value

    @rx.event
    def set_custom_title(self, value: str):
        self.custom_title = value

    @rx.event
    def set_ics(self, value: str):
        self.ics = value

    @rx.event
    def set_show_holidays(self, value: bool):
        self.show_holidays = value

    @rx.event
    def add_recurring(self):
        self.counter += 1
        event = calendar_event(
            f"rec-{self.counter}", at(1, 14), at(1, 15), f"{self.custom_title} ({self.preset})",
            calendar_id="leisure", rrule=RRULE_PRESETS[self.preset],
        )  # fmt: skip
        self.events = [*self.events, event]
        return rx.toast.success(f"RRULE: {RRULE_PRESETS[self.preset]}")

    @rx.event
    def reset_events(self):
        self.events = list(RECURRING_EVENTS)

    @rx.event
    def apply_ics(self):
        self.ics_applied = self.ics


CODE = """
schedule_x(
    events=[
        calendar_event("r1", datetime(2026, 9, 14, 9), datetime(2026, 9, 14, 9, 15), "Stand-up",
                       rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=40"),
        calendar_event("r6", datetime(2026, 9, 14, 15), datetime(2026, 9, 14, 16), "Weekly sync",
                       rrule="FREQ=WEEKLY;COUNT=6", exdate=["20260921T150000"]),
    ],
    background_events=[
        background_event(datetime(2026, 9, 14, 0), datetime(2026, 9, 14, 7), {"background": "#eee"}, "Night",
                         rrule="FREQ=DAILY;COUNT=60"),
    ],
    recurrence=True,          # @schedule-x/event-recurrence
)

# iCalendar import (@schedule-x/ical) — times are treated as UTC
schedule_x(ical_data=ics_text, timezone="UTC", views=["week", "month-grid"])
"""


@rx.page(route="/recurrence", title="Recurrence & iCal · reflex-schedule-x")
def recurrence_page() -> rx.Component:
    return page(
        "Recurrence, background events & iCal",
        "The event-recurrence plugin expands RFC 5545 rules (FREQ, INTERVAL, COUNT, UNTIL, BYDAY, BYMONTHDAY, exdate). "
        "Background events can recur too. The iCal plugin imports .ics data.",
        card(
            rx.hstack(
                labeled("Title", rx.input(value=RecurrenceState.custom_title, on_change=RecurrenceState.set_custom_title)),
                labeled("Rule", rx.select(list(RRULE_PRESETS), value=RecurrenceState.preset,
                                          on_change=RecurrenceState.set_preset)),
                rx.button(rx.icon("repeat", size=14), "Add recurring event", on_click=RecurrenceState.add_recurring),
                rx.button("Reset", variant="soft", on_click=RecurrenceState.reset_events),
                rx.hstack(rx.switch(checked=RecurrenceState.show_holidays, on_change=RecurrenceState.set_show_holidays),
                          rx.text("Holiday background event", size="2"), align="center"),
                wrap="wrap",
                align="end",
                spacing="4",
            )
        ),
        schedule_x(
            events=RecurrenceState.events,
            background_events=RecurrenceState.background_events,
            calendars=CALENDARS,
            recurrence=True,
            event_modal=True,
            views=["week", "month-grid", "month-agenda", "list"],
            default_view="week",
            selected_date=WEEK_START.isoformat(),
            initial_scroll="06:00",
            is_dark=rx.color_mode_cond(light=False, dark=True),
            id="recurrence-calendar",
            height="720px",
        ),
        rx.heading("iCalendar (.ics) import", size="5", padding_top="1rem"),
        rx.grid(
            card(
                rx.vstack(
                    rx.text_area(value=RecurrenceState.ics, on_change=RecurrenceState.set_ics, rows="18",
                                 font_family="monospace", font_size="12px", width="100%"),
                    rx.button(rx.icon("upload", size=14), "Load .ics into the calendar", on_click=RecurrenceState.apply_ics),
                    width="100%",
                ),
            ),
            schedule_x(
                ical_data=RecurrenceState.ics_applied,
                timezone="UTC",
                views=["week", "month-grid", "list"],
                default_view="week",
                selected_date=WEEK_START.isoformat(),
                event_modal=True,
                initial_scroll="12:00",
                is_dark=rx.color_mode_cond(light=False, dark=True),
                id="ical-calendar",
                height="560px",
            ),
            columns=rx.breakpoints(initial="1", lg="380px minmax(0, 1fr)"),
            spacing="4",
            width="100%",
        ),
        code(CODE),
    )  # fmt: skip
