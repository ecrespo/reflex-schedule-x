"""Custom components: fill Schedule-X slots with Reflex components."""

from __future__ import annotations

import datetime as dt
from typing import Any

import reflex as rx

from reflex_schedule_x import (
    schedule_x,
    schedule_x_action,
    schedule_x_event_card,
    schedule_x_field,
    schedule_x_show,
    schedule_x_slot,
)

from ..data import CALENDARS, sample_events
from ..layout import card, code, log_panel, page


class CustomState(rx.State):
    """State of the custom components page."""

    events: list[dict[str, Any]] = sample_events()
    done: list[str] = []
    log: list[str] = []
    view: str = "week"
    counter: int = 0

    @rx.var
    def event_count(self) -> int:
        return len(self.events)

    @rx.event
    def set_view(self, value: str):
        self.view = value

    @rx.event
    def on_slot_action(self, payload: dict[str, Any]):
        """Handle clicks on schedule_x_action components rendered inside slots."""
        action = payload.get("action")
        event = payload.get("event") or {}
        stamp = dt.datetime.now().strftime("%H:%M:%S")
        self.log = [f"{stamp}  {action} · slot={payload.get('slot')} · event={event.get('title')} · date={payload.get('date')}",
                    *self.log][:40]  # fmt: skip
        if action == "delete":
            self.events = [e for e in self.events if e["id"] != event.get("id")]
            return rx.toast.info(f"Deleted “{event.get('title')}”")
        if action == "duplicate":
            self.counter += 1
            copy = {k: v for k, v in event.items() if k != "is_all_day"}
            copy["id"] = f"{event.get('id')}-copy{self.counter}"
            copy["title"] = f"{event.get('title')} (copy)"
            self.events = [*self.events, copy]
            return rx.toast.success("Duplicated")
        if action == "toggle_done":
            self.events = [
                {**e, "title": ("✅ " + e["title"]) if not e["title"].startswith("✅ ") else e["title"][2:]}
                if e["id"] == event.get("id")
                else e
                for e in self.events
            ]
        return None

    @rx.event
    def add_random(self):
        self.counter += 1
        today = dt.date.today()
        start = dt.datetime(today.year, today.month, today.day, 8 + self.counter % 10)
        self.events = [
            *self.events,
            {"id": f"x{self.counter}", "title": f"Quick event #{self.counter}", "calendarId": "school",
             "start": start.strftime("%Y-%m-%d %H:%M"), "end": (start + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")},
        ]  # fmt: skip


def time_grid_event() -> rx.Component:
    return schedule_x_slot(
        "timeGridEvent",
        schedule_x_event_card(
            rx.vstack(
                rx.hstack(
                    schedule_x_field("title", tag_name="strong", style={"fontSize": "12px"}),
                    spacing="1",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("clock", size=11),
                    schedule_x_field("time_range", style={"fontSize": "11px"}),
                    spacing="1",
                    align="center",
                ),
                schedule_x_show(
                    "location",
                    rx.hstack(rx.icon("map-pin", size=11), schedule_x_field("location", style={"fontSize": "11px"}),
                              spacing="1", align="center"),
                ),
                schedule_x_show(
                    "people",
                    rx.hstack(rx.icon("users", size=11), schedule_x_field("people", style={"fontSize": "11px"}),
                              spacing="1", align="center"),
                ),
                spacing="0",
                padding="4px 6px",
            ),
            style={"borderRadius": "6px"},
        ),
    )  # fmt: skip


def date_grid_event() -> rx.Component:
    return schedule_x_slot(
        "dateGridEvent",
        schedule_x_event_card(
            rx.hstack(rx.icon("sun", size=12), schedule_x_field("title"), spacing="1", align="center",
                      padding_x="6px", font_size="12px", height="100%"),
            variant="main",
            style={"borderRadius": "4px"},
        ),
    )  # fmt: skip


def month_grid_event() -> rx.Component:
    return schedule_x_slot(
        "monthGridEvent",
        schedule_x_event_card(
            rx.hstack(
                schedule_x_show("is_all_day", rx.icon("sun", size=11)),
                schedule_x_field("start", format="time", style={"fontVariantNumeric": "tabular-nums", "opacity": 0.8}),
                schedule_x_field("title", tag_name="strong"),
                spacing="1",
                align="center",
                padding_x="4px",
                font_size="11px",
                white_space="nowrap",
            ),
            style={"borderRadius": "4px"},
        ),
    )


def agenda_event(slot: str) -> rx.Component:
    return schedule_x_slot(
        slot,
        schedule_x_event_card(
            rx.vstack(
                schedule_x_field("title", tag_name="strong"),
                schedule_x_field("time_range", style={"fontSize": "12px"}),
                schedule_x_show("location", schedule_x_field("location", style={"fontSize": "12px", "opacity": 0.8})),
                spacing="0",
                padding="6px 8px",
            ),
            style={"borderRadius": "8px"},
        ),
    )


def event_modal() -> rx.Component:
    return schedule_x_slot(
        "eventModal",
        rx.card(
            rx.vstack(
                rx.hstack(
                    schedule_x_event_card(width="14px", height="14px", min_width="14px", border_radius="4px",
                                          variant="main"),
                    schedule_x_field("title", tag_name="h3", style={"margin": 0, "fontSize": "18px"}),
                    align="center",
                ),
                rx.hstack(rx.icon("calendar", size=14), schedule_x_field("start", format="date"), spacing="2", align="center"),
                rx.hstack(rx.icon("clock", size=14), schedule_x_field("time_range"), spacing="2", align="center"),
                rx.hstack(rx.icon("tag", size=14), schedule_x_field("calendar_label"), spacing="2", align="center"),
                schedule_x_show("location", rx.hstack(rx.icon("map-pin", size=14), schedule_x_field("location"),
                                                      spacing="2", align="center")),
                schedule_x_show("people", rx.hstack(rx.icon("users", size=14), schedule_x_field("people"),
                                                    spacing="2", align="center")),
                schedule_x_show("description", rx.text(schedule_x_field("description"), size="2", color_scheme="gray")),
                rx.separator(),
                rx.text("Rendered with Reflex · total events in state: ", rx.badge(CustomState.event_count), size="1"),
                rx.hstack(
                    schedule_x_action(rx.button(rx.icon("check", size=14), "Done", size="1", variant="soft"),
                                      action="toggle_done", close_modal=True),
                    schedule_x_action(rx.button(rx.icon("copy", size=14), "Duplicate", size="1", variant="soft"),
                                      action="duplicate", close_modal=True),
                    schedule_x_action(rx.button(rx.icon("trash-2", size=14), "Delete", size="1", color_scheme="red"),
                                      action="delete", close_modal=True),
                    spacing="2",
                ),
                spacing="2",
            ),
            width="320px",
            box_shadow="0 10px 30px rgba(0,0,0,.25)",
        ),
    )  # fmt: skip


def header_slots() -> list[rx.Component]:
    return [
        schedule_x_slot(
            "headerContentLeftAppend",
            rx.badge(rx.icon("sparkles", size=12), "Reflex slot · ", CustomState.view, color_scheme="violet",
                     margin_left="0.5rem"),
        ),
        schedule_x_slot(
            "headerContentRightPrepend",
            rx.button(rx.icon("plus", size=14), "Quick add", size="2", variant="soft", on_click=CustomState.add_random,
                      margin_right="0.5rem"),
        ),
    ]  # fmt: skip


def axis_slots() -> list[rx.Component]:
    return [
        schedule_x_slot(
            "weekGridDate",
            rx.vstack(
                schedule_x_field("date", format="weekday_short", style={"fontSize": "11px", "textTransform": "uppercase",
                                                                         "opacity": 0.7}),
                schedule_x_field("date", format="day", style={"fontSize": "20px", "fontWeight": 700}),
                spacing="0",
                align="center",
                padding_y="4px",
            ),
        ),
        schedule_x_slot(
            "weekGridHour",
            schedule_x_field("hour", format="hour", style={"fontSize": "10px", "opacity": 0.6}),
        ),
        schedule_x_slot(
            "monthGridDayName",
            schedule_x_field("day", format="weekday", style={"fontSize": "11px", "fontWeight": 600}),
        ),
        schedule_x_slot(
            "monthGridDate",
            rx.box(schedule_x_field("date"), padding="2px 6px", border_radius="999px", font_size="12px",
                   background=rx.color("accent", 3), color=rx.color("accent", 11)),
        ),
        schedule_x_slot(
            "monthAgendaDateDots",
            rx.badge(schedule_x_field("events", format="count"), size="1", variant="soft"),
        ),
    ]  # fmt: skip


CODE = """
schedule_x(
    # Event slots: read data with schedule_x_field / schedule_x_show
    schedule_x_slot(
        "timeGridEvent",
        schedule_x_event_card(                       # painted with the event calendar colors
            schedule_x_field("title", tag_name="strong"),
            schedule_x_field("time_range"),
            schedule_x_show("location", schedule_x_field("location")),
        ),
    ),
    # A fully custom event modal with actions handled in Python
    schedule_x_slot(
        "eventModal",
        rx.card(
            schedule_x_field("title", tag_name="h3"),
            schedule_x_action(rx.button("Delete"), action="delete", close_modal=True),
        ),
    ),
    # Header slots can contain any Reflex component bound to state
    schedule_x_slot("headerContentRightPrepend", rx.button("Quick add", on_click=State.add_random)),
    schedule_x_slot("weekGridDate", schedule_x_field("date", format="weekday_short")),
    events=State.events,
    event_modal=True,
    on_slot_action=State.on_slot_action,   # {'action', 'slot', 'event', 'date'}
)
"""


@rx.page(route="/custom-components", title="Custom components · reflex-schedule-x")
def custom_components_page() -> rx.Component:
    return page(
        "Custom components",
        "Every Schedule-X custom component slot can be filled with Reflex components. Slot content stays reactive "
        "(it can read state) and schedule_x_action sends clicks back to Python with the event that was clicked.",
        card(
            rx.hstack(
                rx.icon("info", size=16),
                rx.text(
                    "Slots used here: timeGridEvent, dateGridEvent, monthGridEvent, monthAgendaEvent, weekAgendaEvent, "
                    "eventModal, headerContentLeftAppend, headerContentRightPrepend, weekGridDate, weekGridHour, "
                    "monthGridDayName, monthGridDate, monthAgendaDateDots. Click an event to open the custom modal.",
                    size="2",
                ),
                align="start",
            )
        ),
        schedule_x(
            time_grid_event(),
            date_grid_event(),
            month_grid_event(),
            agenda_event("monthAgendaEvent"),
            agenda_event("weekAgendaEvent"),
            event_modal(),
            *header_slots(),
            *axis_slots(),
            events=CustomState.events,
            calendars=CALENDARS,
            views=["week", "day", "month-grid", "month-agenda", "week-agenda"],
            view=CustomState.view,
            on_view_change=CustomState.set_view,
            event_modal=True,
            initial_scroll="08:00",
            week_options={"gridHeight": 1500, "eventWidth": 96},
            is_dark=rx.color_mode_cond(light=False, dark=True),
            on_slot_action=CustomState.on_slot_action,
            id="custom-calendar",
            height="800px",
        ),
        log_panel(CustomState.log),
        code(CODE),
    )
