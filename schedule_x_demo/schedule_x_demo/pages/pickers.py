"""Standalone date and time pickers."""

from __future__ import annotations

import reflex as rx

from reflex_schedule_x import LOCALES, schedule_x_date_picker, schedule_x_time_picker

from ..data import TODAY
from ..layout import card, code, labeled, page


class PickerState(rx.State):
    """State of the pickers page."""

    date: str = TODAY.isoformat()
    time: str = "09:30"
    locale: str = "es-ES"
    twelve_hour: bool = False
    disabled: bool = False

    @rx.event
    def set_date(self, value: str):
        self.date = value

    @rx.event
    def set_time(self, value: str):
        self.time = value

    @rx.event
    def set_locale(self, value: str):
        self.locale = value

    @rx.event
    def set_twelve_hour(self, value: bool):
        self.twelve_hour = value

    @rx.event
    def set_disabled(self, value: bool):
        self.disabled = value

    @rx.event
    def set_from_python(self):
        self.date = "2027-01-01"
        self.time = "18:45"


CODE = """
schedule_x_date_picker(
    value=State.date, on_change=State.set_date,       # 'YYYY-MM-DD'
    locale="es-ES", first_day_of_week=1, min="2026-01-01", max="2027-12-31",
    label="Fecha", placement="bottom-start", dark=False, full_width=True, disabled=False,
)
schedule_x_time_picker(
    value=State.time, on_change=State.set_time,       # 'HH:mm'
    label="Time", is_12_hour=True, placement="bottom-start",
)
"""


@rx.page(route="/pickers", title="Date & time pickers · reflex-schedule-x")
def pickers_page() -> rx.Component:
    dark = rx.color_mode_cond(light=False, dark=True)
    return page(
        "Date & time pickers",
        "@schedule-x/date-picker and @schedule-x/time-picker work on their own as controlled form inputs.",
        card(
            rx.hstack(
                labeled("Locale", rx.select(list(LOCALES), value=PickerState.locale, on_change=PickerState.set_locale)),
                rx.hstack(rx.switch(checked=PickerState.twelve_hour, on_change=PickerState.set_twelve_hour),
                          rx.text("12-hour clock", size="2"), align="center"),
                rx.hstack(rx.switch(checked=PickerState.disabled, on_change=PickerState.set_disabled),
                          rx.text("Disable date picker", size="2"), align="center"),
                rx.button("Set 2027-01-01 18:45 from Python", variant="soft", on_click=PickerState.set_from_python),
                wrap="wrap",
                align="end",
                spacing="5",
            ),
        ),
        rx.grid(
            card(
                rx.vstack(
                    rx.heading("Date picker", size="4"),
                    schedule_x_date_picker(
                        value=PickerState.date,
                        on_change=PickerState.set_date,
                        locale=PickerState.locale,
                        label="Date",
                        min="2025-01-01",
                        max="2028-12-31",
                        disabled=PickerState.disabled,
                        full_width=True,
                        dark=dark,
                    ),
                    rx.text("Value in state: ", rx.code(PickerState.date), size="2"),
                    spacing="3",
                    min_height="440px",
                ),
                overflow="visible",
            ),
            card(
                rx.vstack(
                    rx.heading("Time picker", size="4"),
                    schedule_x_time_picker(
                        value=PickerState.time,
                        on_change=PickerState.set_time,
                        locale=PickerState.locale,
                        label="Time",
                        is_12_hour=PickerState.twelve_hour,
                        dark=dark,
                    ),
                    rx.text("Value in state: ", rx.code(PickerState.time), size="2"),
                    spacing="3",
                    min_height="440px",
                ),
                overflow="visible",
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="4",
            width="100%",
        ),
        code(CODE),
    )  # fmt: skip
