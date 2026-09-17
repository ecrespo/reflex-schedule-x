"""Language, translations and timezones."""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import reflex as rx

from reflex_schedule_x import LOCALES, calendar_event, schedule_x

from ..data import CALENDARS, at
from ..layout import card, code, labeled, page

TIMEZONES = [
    "UTC", "America/Caracas", "America/New_York", "America/Los_Angeles", "America/Mexico_City",
    "America/Sao_Paulo", "Europe/Madrid", "Europe/London", "Europe/Berlin", "Africa/Cairo",
    "Asia/Dubai", "Asia/Kolkata", "Asia/Shanghai", "Asia/Tokyo", "Australia/Sydney",
]  # fmt: skip


def zoned_events() -> list[dict[str, Any]]:
    """Events created in different timezones (aware datetimes -> ISO with offset)."""

    def aware(offset: int, hour: int, tz: str) -> dt.datetime:
        naive = at(offset, hour)
        return naive.replace(tzinfo=ZoneInfo(tz))

    return [
        calendar_event("tz1", aware(1, 9, "Europe/Madrid"), aware(1, 10, "Europe/Madrid"),
                       "09:00 in Madrid", calendar_id="work", location="Europe/Madrid"),
        calendar_event("tz2", aware(1, 9, "America/Caracas"), aware(1, 10, "America/Caracas"),
                       "09:00 in Caracas", calendar_id="personal", location="America/Caracas"),
        calendar_event("tz3", aware(2, 9, "Asia/Tokyo"), aware(2, 10, "Asia/Tokyo"),
                       "09:00 in Tokyo", calendar_id="leisure", location="Asia/Tokyo"),
        calendar_event("tz4", "2026-01-01T12:00:00Z", "2026-01-01T13:00:00Z", "Noon UTC (ISO 'Z')",
                       calendar_id="school"),
        {"id": "tz5", "title": "RFC 9557 string (New York)", "calendarId": "school",
         "start": f"{at(3, 11).isoformat()}-04:00[America/New_York]",
         "end": f"{at(3, 12).isoformat()}-04:00[America/New_York]"},
        calendar_event("tz6", at(3, 15), at(3, 16), "Naive time = calendar timezone", calendar_id="work"),
    ]  # fmt: skip


class I18nState(rx.State):
    """State of the i18n page."""

    locale: str = "es-ES"
    timezone: str = "America/Caracas"
    timezone_select: bool = True
    custom_labels: bool = False
    last_click: str = ""

    @rx.var
    def translations(self) -> dict[str, dict[str, str]]:
        if not self.custom_labels:
            return {}
        return {self.locale: {"Today": "📍 Today", "Week": "🗓 Week", "Day": "☀️ Day", "Month": "🌙 Month"}}

    @rx.event
    def set_locale(self, value: str):
        self.locale = value

    @rx.event
    def set_timezone(self, value: str):
        self.timezone = value

    @rx.event
    def set_timezone_select(self, value: bool):
        self.timezone_select = value

    @rx.event
    def set_custom_labels(self, value: bool):
        self.custom_labels = value

    @rx.event
    def on_event_click(self, event: dict[str, Any]):
        self.last_click = f"{event.get('title')}: {event.get('start')} → {event.get('end')}"


CODE = """
schedule_x(
    events=[
        calendar_event("tz1", datetime(2026, 9, 15, 9, tzinfo=ZoneInfo("Europe/Madrid")), ..., "09:00 in Madrid"),
        {"id": "tz5", "start": "2026-09-17T11:00:00-04:00[America/New_York]", "end": "..."},  # RFC 9557
        {"id": "tz6", "start": "2026-09-17 15:00", "end": "2026-09-17 16:00"},  # naive -> calendar timezone
    ],
    locale=State.locale,                 # 37 locales, see reflex_schedule_x.LOCALES
    timezone=State.timezone,             # events are converted to this timezone
    timezone_select=True,                # @schedule-x/timezone-select plugin in the header
    translations={"es-ES": {"Today": "📍 Today"}},   # merged over the built-in translations
    datetime_format="iso",               # callbacks send RFC 9557 strings
    on_event_click=State.on_event_click,
)
"""


@rx.page(route="/i18n", title="Language & timezones · reflex-schedule-x")
def i18n_page() -> rx.Component:
    return page(
        "Language & timezones",
        "Switch between the 37 bundled locales, override translations, and render events that were created in "
        "different timezones in the timezone of your choice.",
        card(
            rx.hstack(
                labeled("Locale", rx.select(list(LOCALES), value=I18nState.locale, on_change=I18nState.set_locale)),
                labeled("Calendar timezone", rx.select(TIMEZONES, value=I18nState.timezone,
                                                       on_change=I18nState.set_timezone)),
                rx.hstack(rx.switch(checked=I18nState.timezone_select, on_change=I18nState.set_timezone_select),
                          rx.text("Timezone-select plugin", size="2"), align="center"),
                rx.hstack(rx.switch(checked=I18nState.custom_labels, on_change=I18nState.set_custom_labels),
                          rx.text("Custom translations", size="2"), align="center"),
                wrap="wrap",
                align="end",
                spacing="5",
            ),
        ),
        rx.cond(
            I18nState.last_click != "",
            rx.callout(I18nState.last_click, icon="info", size="1", width="100%"),
            rx.callout("Click an event: with datetime_format='iso' the payload keeps the timezone.", icon="info",
                       size="1", width="100%"),
        ),
        schedule_x(
            events=zoned_events(),
            calendars=CALENDARS,
            locale=I18nState.locale,
            timezone=I18nState.timezone,
            timezone_select=I18nState.timezone_select,
            translations=I18nState.translations,
            datetime_format="iso",
            views=["week", "day", "month-grid", "month-agenda", "list"],
            default_view="week",
            event_modal=True,
            initial_scroll="00:00",
            is_dark=rx.color_mode_cond(light=False, dark=True),
            on_event_click=I18nState.on_event_click,
            id="i18n-calendar",
            height="760px",
        ),
        code(CODE),
    )  # fmt: skip
