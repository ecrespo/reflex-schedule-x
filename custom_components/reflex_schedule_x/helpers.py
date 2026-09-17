"""Python helpers for building Schedule-X data and driving a calendar imperatively."""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any

import reflex as rx

LOCALES: tuple[str, ...] = (
    "ar-EG", "ca-ES", "cs-CZ", "da-DK", "de-DE", "en-GB", "en-US", "es-ES", "et-EE",
    "fa-IR", "fi-FI", "fr-CH", "fr-FR", "he-IL", "hr-HR", "id-ID", "it-IT", "ja-JP",
    "ko-KR", "ky-KG", "lt-LT", "mk-MK", "nb-NO", "nl-NL", "pl-PL", "pt-BR", "ro-RO",
    "ru-RU", "sk-SK", "sl-SI", "sr-Latn-RS", "sr-RS", "sv-SE", "tr-TR", "uk-UA",
    "zh-CN", "zh-TW",
)  # fmt: skip
"""Locales shipped with @schedule-x/translations."""

DateLike = str | _dt.date | _dt.datetime


# --------------------------------------------------------------------------- #
#                               Date conversion                               #
# --------------------------------------------------------------------------- #


def to_sx_date(value: DateLike) -> str:
    """Convert a date (or datetime) to the 'YYYY-MM-DD' string the calendar expects.

    Args:
        value: A ``date``, ``datetime`` or string.

    Returns:
        The date string.
    """
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    return str(value)[:10]


def to_sx_datetime(value: DateLike) -> str:
    """Convert a Python value to a Schedule-X start/end string.

    - ``date`` -> 'YYYY-MM-DD' (all-day)
    - naive ``datetime`` -> 'YYYY-MM-DD HH:mm' (interpreted in the calendar timezone)
    - aware ``datetime`` -> ISO 8601 with offset (converted to the calendar timezone)

    Args:
        value: A ``date``, ``datetime`` or already formatted string.

    Returns:
        The string for ``start``/``end``.
    """
    if isinstance(value, _dt.datetime):
        if value.tzinfo is not None and value.utcoffset() is not None:
            return value.isoformat(timespec="seconds")
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, _dt.date):
        return value.isoformat()
    return str(value)


def parse_sx_datetime(value: str) -> _dt.date | _dt.datetime:
    """Parse a date/date-time string sent by the calendar back into Python.

    Accepts 'YYYY-MM-DD', 'YYYY-MM-DD HH:mm' and RFC 9557 strings
    ('2025-01-01T10:00:00-04:00[America/Caracas]').

    Args:
        value: The string from an event payload.

    Returns:
        A ``date`` for all-day values, otherwise a ``datetime``.
    """
    text = value.strip()
    if len(text) == 10:
        return _dt.date.fromisoformat(text)
    if "[" in text:
        text = text.split("[", 1)[0]
    return _dt.datetime.fromisoformat(text.replace(" ", "T"))


# --------------------------------------------------------------------------- #
#                                Data builders                                #
# --------------------------------------------------------------------------- #


def calendar_event(
    id: str | int,
    start: DateLike,
    end: DateLike | None = None,
    title: str | None = None,
    *,
    description: str | None = None,
    location: str | None = None,
    people: list[str] | None = None,
    calendar_id: str | None = None,
    rrule: str | None = None,
    exdate: list[str] | None = None,
    disable_dnd: bool | None = None,
    disable_resize: bool | None = None,
    additional_classes: list[str] | None = None,
    custom_content: dict[str, str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build an event dict for ``schedule_x(events=[...])``.

    Args:
        id: Unique id.
        start: Start (date for all-day, datetime for timed events).
        end: End; defaults to ``start``.
        title: Title.
        description: Description shown in the event modal.
        location: Location.
        people: Participants.
        calendar_id: Key of a calendar in ``calendars``.
        rrule: RFC 5545 recurrence rule (needs ``recurrence=True``).
        exdate: Excluded dates, e.g. ['20250101T100000'].
        disable_dnd: Disable drag & drop for this event (premium plugin).
        disable_resize: Disable resizing for this event (premium plugin).
        additional_classes: Extra CSS classes for the event element.
        custom_content: HTML per view: timeGrid, dateGrid, monthGrid, monthAgenda, weekAgenda.
        **extra: Any other keys; they are returned untouched in callbacks.

    Returns:
        The event dict.
    """
    event: dict[str, Any] = {
        "id": id,
        "start": to_sx_datetime(start),
        "end": to_sx_datetime(end if end is not None else start),
    }
    optional = {
        "title": title,
        "description": description,
        "location": location,
        "people": people,
        "calendarId": calendar_id,
        "rrule": rrule,
        "exdate": exdate,
    }
    event.update({k: v for k, v in optional.items() if v is not None})
    options = {
        "disableDND": disable_dnd,
        "disableResize": disable_resize,
        "additionalClasses": additional_classes,
    }
    options = {k: v for k, v in options.items() if v is not None}
    if options:
        event["_options"] = options
    if custom_content:
        event["_customContent"] = custom_content
    event.update(extra)
    return event


def background_event(
    start: DateLike,
    end: DateLike | None = None,
    style: dict[str, Any] | None = None,
    title: str | None = None,
    *,
    rrule: str | None = None,
    exdate: list[str] | None = None,
) -> dict[str, Any]:
    """Build a background event (holidays, out-of-office blocks, ...).

    Args:
        start: Start.
        end: End; defaults to ``start``.
        style: CSS for the block (camelCase or snake_case keys).
        title: Tooltip.
        rrule: Recurrence rule (needs ``recurrence=True``).
        exdate: Excluded dates.

    Returns:
        The background event dict.
    """
    event: dict[str, Any] = {
        "start": to_sx_datetime(start),
        "end": to_sx_datetime(end if end is not None else start),
        "style": style or {"backgroundColor": "rgba(128, 128, 128, 0.15)"},
    }
    if title is not None:
        event["title"] = title
    if rrule is not None:
        event["rrule"] = rrule
    if exdate is not None:
        event["exdate"] = exdate
    return event


def calendar_type(
    color_name: str,
    main: str,
    container: str,
    on_container: str,
    *,
    dark_main: str | None = None,
    dark_container: str | None = None,
    dark_on_container: str | None = None,
    label: str | None = None,
    readonly: bool | None = None,
) -> dict[str, Any]:
    """Build a calendar category for ``schedule_x(calendars={...})``.

    Args:
        color_name: Lower-case name used in CSS variables (``--sx-color-<name>``).
        main: Main color (light mode).
        container: Background color (light mode).
        on_container: Text color on the background (light mode).
        dark_main: Main color in dark mode (defaults to ``container``).
        dark_container: Background in dark mode (defaults to ``main``).
        dark_on_container: Text color in dark mode (defaults to ``container``).
        label: Human-readable name.
        readonly: Mark events of this calendar as read-only (premium interactions).

    Returns:
        The calendar dict.
    """
    cal: dict[str, Any] = {
        "colorName": color_name,
        "lightColors": {"main": main, "container": container, "onContainer": on_container},
        "darkColors": {
            "main": dark_main or container,
            "container": dark_container or main,
            "onContainer": dark_on_container or container,
        },
    }
    if label is not None:
        cal["label"] = label
    if readonly is not None:
        cal["readonly"] = readonly
    return cal


# --------------------------------------------------------------------------- #
#                               Imperative API                                #
# --------------------------------------------------------------------------- #


class ScheduleXAPI:
    """Drive a calendar rendered with ``schedule_x(id=...)`` from event handlers.

    Every method returns an ``rx.call_script`` event, so return it (or yield it)
    from an event handler, or use it directly as an ``on_click``.

    Example:
        ```python
        api = ScheduleXAPI("my-calendar")
        rx.button("Week", on_click=api.set_view("week"))

        @rx.event
        def refresh(self):
            return api.get_events(callback=State.receive_events)
        ```
    """

    def __init__(self, calendar_id: str):
        """Bind the API to a calendar id.

        Args:
            calendar_id: The ``id`` passed to ``schedule_x``.
        """
        self.calendar_id = calendar_id

    def _call(self, method: str, *args: Any, callback: Any = None) -> Any:
        arguments = ", ".join(json.dumps(a, default=str) for a in args)
        target = f"window.__reflexScheduleX?.[{json.dumps(self.calendar_id)}]"
        script = f"(() => {{ const api = {target}; return api ? api.{method}({arguments}) : null; }})()"
        if callback is None:
            return rx.call_script(script)
        return rx.call_script(script, callback=callback)

    def set_view(self, view: str) -> Any:
        """Change the view ('day', 'week', 'month-grid', ...)."""
        return self._call("setView", view)

    def set_date(self, date: DateLike) -> Any:
        """Navigate to a date."""
        return self._call("setDate", to_sx_date(date))

    def set_theme(self, mode: str) -> Any:
        """Switch between 'light' and 'dark'."""
        return self._call("setTheme", mode)

    def add_event(self, event: dict[str, Any]) -> Any:
        """Add an event without going through the ``events`` prop."""
        return self._call("addEvent", event)

    def update_event(self, event: dict[str, Any]) -> Any:
        """Update an event (matched by id)."""
        return self._call("updateEvent", event)

    def remove_event(self, event_id: str | int) -> Any:
        """Remove an event by id."""
        return self._call("removeEvent", event_id)

    def set_events(self, events: list[dict[str, Any]]) -> Any:
        """Replace all events."""
        return self._call("setEvents", events)

    def close_event_modal(self) -> Any:
        """Close the event modal plugin."""
        return self._call("closeEventModal")

    def scroll_to(self, time: str) -> Any:
        """Scroll the week/day grid to 'HH:mm' (needs ``initial_scroll``)."""
        return self._call("scrollTo", time)

    def get_view(self, callback: Any) -> Any:
        """Send the current view name to ``callback``."""
        return self._call("getView", callback=callback)

    def get_date(self, callback: Any) -> Any:
        """Send the selected date to ``callback``."""
        return self._call("getDate", callback=callback)

    def get_range(self, callback: Any) -> Any:
        """Send the visible range ``{start, end}`` to ``callback``."""
        return self._call("getRange", callback=callback)

    def get_events(self, callback: Any) -> Any:
        """Send all events currently in the calendar to ``callback``."""
        return self._call("getEvents", callback=callback)

    def get_event(self, event_id: str | int, callback: Any) -> Any:
        """Send one event to ``callback``."""
        return self._call("getEvent", event_id, callback=callback)
