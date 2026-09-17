"""Tests for the Python helpers (no browser needed)."""

import datetime as dt
import json

import pytest
import reflex as rx

from reflex_schedule_x import (
    LOCALES,
    ScheduleXAPI,
    background_event,
    calendar_event,
    calendar_type,
    parse_sx_datetime,
    to_sx_date,
    to_sx_datetime,
)


class _State(rx.State):
    @rx.event
    def receive(self, value: dict):
        pass


def test_to_sx_datetime_variants():
    assert to_sx_datetime(dt.date(2026, 9, 17)) == "2026-09-17"
    assert to_sx_datetime(dt.datetime(2026, 9, 17, 10, 5)) == "2026-09-17 10:05"
    aware = dt.datetime(2026, 9, 17, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
    assert to_sx_datetime(aware) == "2026-09-17T10:00:00-04:00"
    assert to_sx_datetime("2026-09-17 08:00") == "2026-09-17 08:00"


def test_to_sx_date():
    assert to_sx_date(dt.datetime(2026, 1, 2, 3, 4)) == "2026-01-02"
    assert to_sx_date("2026-01-02 10:00") == "2026-01-02"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-17", dt.date(2026, 9, 17)),
        ("2026-09-17 10:30", dt.datetime(2026, 9, 17, 10, 30)),
        (
            "2026-09-17T10:30:00-04:00[America/Caracas]",
            dt.datetime(2026, 9, 17, 10, 30, tzinfo=dt.timezone(dt.timedelta(hours=-4))),
        ),
    ],
)
def test_parse_sx_datetime(value, expected):
    assert parse_sx_datetime(value) == expected


def test_calendar_event_builds_schedule_x_shape():
    event = calendar_event(
        "1",
        dt.datetime(2026, 9, 17, 9),
        dt.datetime(2026, 9, 17, 10),
        "Stand-up",
        calendar_id="work",
        people=["Ana"],
        rrule="FREQ=DAILY;COUNT=3",
        disable_dnd=True,
        custom_content={"timeGrid": "<b>x</b>"},
        priority="high",
    )
    assert event == {
        "id": "1",
        "start": "2026-09-17 09:00",
        "end": "2026-09-17 10:00",
        "title": "Stand-up",
        "people": ["Ana"],
        "calendarId": "work",
        "rrule": "FREQ=DAILY;COUNT=3",
        "_options": {"disableDND": True},
        "_customContent": {"timeGrid": "<b>x</b>"},
        "priority": "high",
    }


def test_calendar_event_defaults_end_to_start():
    assert calendar_event(1, dt.date(2026, 1, 1))["end"] == "2026-01-01"


def test_background_event_and_calendar_type():
    bg = background_event(dt.date(2026, 1, 1), style={"opacity": 0.5}, title="Holiday")
    assert bg == {"start": "2026-01-01", "end": "2026-01-01", "style": {"opacity": 0.5}, "title": "Holiday"}
    cal = calendar_type("work", "#f91c45", "#ffd2dc", "#59000d", label="Work")
    assert cal["colorName"] == "work"
    assert cal["lightColors"] == {"main": "#f91c45", "container": "#ffd2dc", "onContainer": "#59000d"}
    assert cal["darkColors"]["container"] == "#f91c45"
    assert cal["label"] == "Work"


def test_locales_cover_known_codes():
    assert {"es-ES", "en-US", "sr-Latn-RS"} <= set(LOCALES)
    assert len(LOCALES) == len(set(LOCALES)) == 37


def test_api_builds_call_script():
    spec = ScheduleXAPI("cal").set_view("week")
    script = spec.args[0][1]._var_value
    assert 'window.__reflexScheduleX?.["cal"]' in script
    assert 'api.setView("week")' in script
    payload = {"id": 1, "title": 'quote " inside'}
    script = ScheduleXAPI("cal").add_event(payload).args[0][1]._var_value
    assert json.dumps(payload) in script


def _script(spec) -> str:
    return spec.args[0][1]._var_value


@pytest.mark.parametrize(
    ("method", "args", "expected"),
    [
        ("set_date", (dt.date(2026, 9, 17),), 'api.setDate("2026-09-17")'),
        ("set_theme", ("dark",), 'api.setTheme("dark")'),
        ("update_event", ({"id": 1},), 'api.updateEvent({"id": 1})'),
        ("remove_event", (7,), "api.removeEvent(7)"),
        ("set_events", ([],), "api.setEvents([])"),
        ("close_event_modal", (), "api.closeEventModal()"),
        ("scroll_to", ("08:00",), 'api.scrollTo("08:00")'),
    ],
)
def test_api_commands(method, args, expected):
    assert expected in _script(getattr(ScheduleXAPI("cal"), method)(*args))


@pytest.mark.parametrize(
    ("method", "args", "expected"),
    [
        ("get_view", (), "api.getView()"),
        ("get_date", (), "api.getDate()"),
        ("get_range", (), "api.getRange()"),
        ("get_events", (), "api.getEvents()"),
        ("get_event", ("42",), 'api.getEvent("42")'),
    ],
)
def test_api_queries_send_result_to_callback(method, args, expected):
    spec = getattr(ScheduleXAPI("cal"), method)(*args, callback=_State.receive)
    assert expected in _script(spec)
    assert "receive" in str(spec.args)


def test_builders_optional_fields():
    assert to_sx_date(dt.date(2026, 1, 2)) == "2026-01-02"
    bg = background_event("2026-01-01 08:00", "2026-01-01 09:00", rrule="FREQ=WEEKLY", exdate=["20260108T080000"])
    assert bg["rrule"] == "FREQ=WEEKLY"
    assert bg["exdate"] == ["20260108T080000"]
    assert bg["style"] == {"backgroundColor": "rgba(128, 128, 128, 0.15)"}
    assert calendar_type("x", "#000", "#fff", "#111", readonly=True)["readonly"] is True
