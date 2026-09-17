"""Playground: every configuration option wired to live controls."""

from __future__ import annotations

from typing import Any

import reflex as rx

from reflex_schedule_x import VIEWS, schedule_x, schedule_x_date_picker

from ..data import CALENDAR_COLORS, CALENDARS, TODAY, sample_background_events, sample_events
from ..layout import card, code, labeled, page

START_HOURS = [f"{h:02d}:00" for h in range(24)]
END_HOURS = [f"{h:02d}:00" for h in range(1, 25)]


class PlaygroundState(rx.State):
    """State of the playground page."""

    all_events: list[dict[str, Any]] = sample_events()
    background: list[dict[str, Any]] = sample_background_events()
    visible_calendars: list[str] = list(CALENDARS)
    enabled_views: list[str] = ["day", "week", "month-grid", "month-agenda", "week-agenda", "list"]
    view: str = "week"
    selected_date: str = TODAY.isoformat()
    first_day_of_week: str = "1"
    show_week_numbers: bool = False
    day_start: str = "00:00"
    day_end: str = "24:00"
    grid_step: str = "60"
    n_days: int = 7
    grid_height: int = 1600
    event_overlap: bool = True
    n_events_per_day: int = 4
    current_time: bool = True
    event_modal: bool = True
    skip_animations: bool = False
    is_responsive: bool = True
    show_background: bool = True
    scroll_target: str = "08:00"
    last_range: str = ""

    @rx.var
    def events(self) -> list[dict[str, Any]]:
        """Events of the visible calendars."""
        return [e for e in self.all_events if e.get("calendarId") in self.visible_calendars]

    @rx.var
    def background_events(self) -> list[dict[str, Any]]:
        """Background events, if enabled."""
        return self.background if self.show_background else []

    @rx.var
    def day_boundaries(self) -> dict[str, str]:
        """Visible hours of the time grid."""
        return {"start": self.day_start, "end": self.day_end}

    @rx.var
    def week_options(self) -> dict[str, Any]:
        """Week grid options."""
        return {
            "gridHeight": self.grid_height,
            "nDays": self.n_days,
            "eventWidth": 95,
            "gridStep": int(self.grid_step),
            "eventOverlap": self.event_overlap,
        }

    @rx.var
    def month_grid_options(self) -> dict[str, int]:
        """Month grid options."""
        return {"nEventsPerDay": self.n_events_per_day}

    @rx.event
    def toggle_calendar(self, calendar_id: str):
        """Show or hide a calendar."""
        if calendar_id in self.visible_calendars:
            self.visible_calendars = [c for c in self.visible_calendars if c != calendar_id]
        else:
            self.visible_calendars = [*self.visible_calendars, calendar_id]

    @rx.event
    def toggle_view(self, name: str, checked: bool):
        """Enable or disable a view (keeps at least one)."""
        views = [v for v in VIEWS if (v in self.enabled_views and v != name) or (v == name and checked)]
        if not views:
            return rx.toast.warning("At least one view must stay enabled.")
        self.enabled_views = views
        if self.view not in views:
            self.view = views[0]

    @rx.event
    def set_view(self, value: str):
        self.view = value

    @rx.event
    def set_selected_date(self, value: str):
        self.selected_date = value

    @rx.event
    def set_first_day_of_week(self, value: str):
        self.first_day_of_week = value

    @rx.event
    def set_show_week_numbers(self, value: bool):
        self.show_week_numbers = value

    @rx.event
    def set_day_start(self, value: str):
        self.day_start = value

    @rx.event
    def set_day_end(self, value: str):
        self.day_end = value

    @rx.event
    def set_grid_step(self, value: str):
        self.grid_step = value

    @rx.event
    def set_n_days(self, value: list[int | float]):
        self.n_days = int(value[0])

    @rx.event
    def set_grid_height(self, value: list[int | float]):
        self.grid_height = int(value[0])

    @rx.event
    def set_event_overlap(self, value: bool):
        self.event_overlap = value

    @rx.event
    def set_n_events_per_day(self, value: list[int | float]):
        self.n_events_per_day = int(value[0])

    @rx.event
    def set_current_time(self, value: bool):
        self.current_time = value

    @rx.event
    def set_event_modal(self, value: bool):
        self.event_modal = value

    @rx.event
    def set_skip_animations(self, value: bool):
        self.skip_animations = value

    @rx.event
    def set_is_responsive(self, value: bool):
        self.is_responsive = value

    @rx.event
    def set_show_background(self, value: bool):
        self.show_background = value

    @rx.event
    def set_scroll_target(self, value: str):
        self.scroll_target = value

    @rx.event
    def on_range_update(self, date_range: dict[str, str]):
        """Remember the visible range."""
        self.last_range = f"{date_range['start']} → {date_range['end']}"

    @rx.event
    def on_calendar_render(self, info: dict[str, Any]):
        """Show the initial range."""
        if info.get("range"):
            self.last_range = f"{info['range']['start']} → {info['range']['end']}"

    @rx.event
    def go_today(self):
        """Jump to today."""
        self.selected_date = TODAY.isoformat()


def switch_row(label: str, checked: rx.Var[bool], on_change: rx.EventHandler) -> rx.Component:
    return rx.el.label(
        rx.hstack(
            rx.switch(checked=checked, on_change=on_change, size="1"),
            rx.text(label, size="2"),
            align="center",
            spacing="2",
        ),
        cursor="pointer",
    )


def calendar_legend() -> rx.Component:
    return rx.hstack(
        *[
            rx.badge(
                rx.box(width="8px", height="8px", border_radius="50%", background=color),
                CALENDARS[key]["label"],
                variant=rx.cond(PlaygroundState.visible_calendars.contains(key), "soft", "outline"),
                color_scheme="gray",
                opacity=rx.cond(PlaygroundState.visible_calendars.contains(key), "1", "0.45"),
                cursor="pointer",
                size="2",
                on_click=PlaygroundState.toggle_calendar(key),
            )
            for key, color in CALENDAR_COLORS.items()
        ],
        rx.text("Click to filter calendars", size="1", color_scheme="gray"),
        wrap="wrap",
        align="center",
    )


def controls() -> rx.Component:
    return card(
        rx.vstack(
            rx.hstack(
                labeled(
                    "View (controlled)",
                    rx.select(
                        PlaygroundState.enabled_views, value=PlaygroundState.view, on_change=PlaygroundState.set_view
                    ),
                ),
                rx.hstack(
                    schedule_x_date_picker(
                        value=PlaygroundState.selected_date,
                        on_change=PlaygroundState.set_selected_date,
                        label="Selected date (controlled)",
                        dark=rx.color_mode_cond(light=False, dark=True),
                    ),
                    rx.button("Today", variant="soft", on_click=PlaygroundState.go_today),
                    align="center",
                ),
                labeled(
                    "First day of week",
                    rx.select.root(
                        rx.select.trigger(),
                        rx.select.content(
                            *[
                                rx.select.item(n, value=str(i))
                                for i, n in enumerate(
                                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                    start=1,
                                )
                            ]
                        ),
                        value=PlaygroundState.first_day_of_week,
                        on_change=PlaygroundState.set_first_day_of_week,
                    ),
                ),
                labeled(
                    "Day starts",
                    rx.select(START_HOURS, value=PlaygroundState.day_start, on_change=PlaygroundState.set_day_start),
                ),
                labeled(
                    "Day ends",
                    rx.select(END_HOURS, value=PlaygroundState.day_end, on_change=PlaygroundState.set_day_end),
                ),
                labeled(
                    "Grid step (min)",
                    rx.select(
                        ["180", "120", "60", "30", "15"],
                        value=PlaygroundState.grid_step,
                        on_change=PlaygroundState.set_grid_step,
                    ),
                ),
                labeled(
                    "Scroll to (scroll controller)",
                    rx.select(
                        [f"{h:02d}:00" for h in range(0, 24, 2)],
                        value=PlaygroundState.scroll_target,
                        on_change=PlaygroundState.set_scroll_target,
                    ),
                ),
                wrap="wrap",
                spacing="4",
                align="end",
            ),
            rx.hstack(
                labeled(
                    "Days in week view",
                    rx.hstack(
                        rx.slider(
                            min=1,
                            max=7,
                            step=1,
                            default_value=[7],
                            on_value_commit=PlaygroundState.set_n_days,
                            width="140px",
                        ),
                        rx.badge(PlaygroundState.n_days),
                    ),
                ),
                labeled(
                    "Grid height (px)",
                    rx.hstack(
                        rx.slider(
                            min=800,
                            max=3000,
                            step=100,
                            default_value=[1600],
                            on_value_commit=PlaygroundState.set_grid_height,
                            width="140px",
                        ),
                        rx.badge(PlaygroundState.grid_height),
                    ),
                ),
                labeled(
                    "Events per month-grid day",
                    rx.hstack(
                        rx.slider(
                            min=1,
                            max=8,
                            step=1,
                            default_value=[4],
                            on_value_commit=PlaygroundState.set_n_events_per_day,
                            width="140px",
                        ),
                        rx.badge(PlaygroundState.n_events_per_day),
                    ),
                ),
                wrap="wrap",
                spacing="5",
            ),
            rx.hstack(
                switch_row("Week numbers", PlaygroundState.show_week_numbers, PlaygroundState.set_show_week_numbers),
                switch_row("Event overlap", PlaygroundState.event_overlap, PlaygroundState.set_event_overlap),
                switch_row("Current time plugin", PlaygroundState.current_time, PlaygroundState.set_current_time),
                switch_row("Event modal plugin", PlaygroundState.event_modal, PlaygroundState.set_event_modal),
                switch_row("Background events", PlaygroundState.show_background, PlaygroundState.set_show_background),
                switch_row("Skip animations", PlaygroundState.skip_animations, PlaygroundState.set_skip_animations),
                switch_row("Responsive", PlaygroundState.is_responsive, PlaygroundState.set_is_responsive),
                wrap="wrap",
                spacing="5",
            ),
            rx.vstack(
                rx.text("Enabled views", size="1", weight="medium", color_scheme="gray"),
                rx.hstack(
                    *[
                        rx.checkbox(
                            name,
                            checked=PlaygroundState.enabled_views.contains(name),
                            on_change=lambda checked, n=name: PlaygroundState.toggle_view(n, checked),
                        )
                        for name in VIEWS
                    ],
                    wrap="wrap",
                    spacing="4",
                ),
                spacing="1",
            ),
            spacing="4",
            width="100%",
        )
    )


CODE = """
schedule_x(
    events=State.events,                    # list[dict] — dates as strings
    background_events=State.background_events,
    calendars=CALENDARS,                    # calendar_type(...) helpers
    views=State.enabled_views,              # day, week, month-grid, month-agenda, week-agenda, list
    view=State.view,                        # controlled view
    on_view_change=State.set_view,
    selected_date=State.selected_date,
    on_selected_date_update=State.set_selected_date,
    first_day_of_week=State.first_day_of_week,
    day_boundaries={"start": "06:00", "end": "20:00"},
    week_options={"gridHeight": 1600, "nDays": 7, "gridStep": 60, "eventOverlap": True},
    month_grid_options={"nEventsPerDay": 4},
    show_week_numbers=True,
    is_dark=rx.color_mode_cond(light=False, dark=True),
    current_time_indicator=True,
    event_modal=True,
    initial_scroll="08:00",
    scroll_to=State.scroll_target,
    on_range_update=State.on_range_update,
)
"""


@rx.page(route="/", title="Playground · reflex-schedule-x")
def playground() -> rx.Component:
    return page(
        "Playground",
        "The full Schedule-X calendar driven from Python state. Every control below updates the running calendar.",
        controls(),
        calendar_legend(),
        schedule_x(
            events=PlaygroundState.events,
            background_events=PlaygroundState.background_events,
            calendars=CALENDARS,
            views=PlaygroundState.enabled_views,
            view=PlaygroundState.view,
            on_view_change=PlaygroundState.set_view,
            selected_date=PlaygroundState.selected_date,
            on_selected_date_update=PlaygroundState.set_selected_date,
            first_day_of_week=PlaygroundState.first_day_of_week.to(int),
            day_boundaries=PlaygroundState.day_boundaries,
            week_options=PlaygroundState.week_options,
            month_grid_options=PlaygroundState.month_grid_options,
            show_week_numbers=PlaygroundState.show_week_numbers,
            skip_animations=PlaygroundState.skip_animations,
            is_responsive=PlaygroundState.is_responsive,
            is_dark=rx.color_mode_cond(light=False, dark=True),
            current_time_indicator=PlaygroundState.current_time,
            event_modal=PlaygroundState.event_modal,
            initial_scroll="08:00",
            scroll_to=PlaygroundState.scroll_target,
            on_range_update=PlaygroundState.on_range_update,
            on_calendar_render=PlaygroundState.on_calendar_render,
            id="playground-calendar",
            height="780px",
        ),
        rx.text("Visible range: ", rx.code(PlaygroundState.last_range), size="2", color_scheme="gray"),
        code(CODE),
    )
