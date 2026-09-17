"""Tests for the component definitions: props, triggers and imports."""

import pytest
import reflex as rx

from reflex_schedule_x import (
    LIB_DEPENDENCIES,
    SCHEDULE_X_VERSION,
    SLOT_NAMES,
    schedule_x,
    schedule_x_action,
    schedule_x_date_picker,
    schedule_x_event_card,
    schedule_x_field,
    schedule_x_show,
    schedule_x_slot,
    schedule_x_time_picker,
)


class _State(rx.State):
    events: list[dict] = []

    @rx.event
    def on_event(self, event: dict):
        pass

    @rx.event
    def on_text(self, value: str):
        pass


def _render(component) -> str:
    return str(component.render())


def test_calendar_props_are_camel_cased():
    cal = schedule_x(
        events=[{"id": 1, "start": "2026-01-01", "end": "2026-01-01"}],
        views=["week", "month-grid"],
        default_view="week",
        first_day_of_week=7,
        day_boundaries={"start": "06:00", "end": "18:00"},
        current_time_indicator=True,
        event_modal=True,
        initial_scroll="08:00",
        ical_data="BEGIN:VCALENDAR",
        datetime_format="iso",
    )
    rendered = _render(cal)
    for prop in [
        "defaultView",
        "firstDayOfWeek",
        "dayBoundaries",
        "currentTimeIndicator",
        "eventModal",
        "initialScroll",
        "icalData",
        "datetimeFormat",
    ]:
        assert prop in rendered, prop


def test_calendar_event_triggers_accept_typed_handlers():
    cal = schedule_x(
        on_event_click=_State.on_event,
        on_view_change=_State.on_text,
        on_click_date_time=_State.on_text,
        on_range_update=_State.on_event,
        on_slot_action=_State.on_event,
    )
    triggers = cal.event_triggers
    for name in ["on_event_click", "on_view_change", "on_click_date_time", "on_range_update", "on_slot_action"]:
        assert name in triggers


def test_calendar_rejects_wrong_handler_type():
    with pytest.raises(TypeError, match="on_view_change"):
        schedule_x(on_view_change=_State.on_event)


def test_theme_css_imports():
    default_imports = schedule_x()._get_all_imports()
    assert "@schedule-x/theme-default/dist/index.css" in default_imports
    assert "@schedule-x/timezone-select/index.css" in default_imports
    shadcn_imports = schedule_x(theme="shadcn")._get_all_imports()
    assert "@schedule-x/theme-shadcn/dist/index.css" in shadcn_imports
    assert "@schedule-x/theme-default/dist/index.css" not in shadcn_imports
    assert "@schedule-x/theme-default/dist/time-picker.css" in schedule_x_time_picker()._get_all_imports()


def test_lib_dependencies_are_pinned():
    assert f"@schedule-x/calendar@{SCHEDULE_X_VERSION}" in LIB_DEPENDENCIES
    assert any(dep.startswith("temporal-polyfill@") for dep in LIB_DEPENDENCIES)


def test_slot_validation_and_positional_name():
    slot = schedule_x_slot("timeGridEvent", schedule_x_event_card(schedule_x_field("title")))
    assert "timeGridEvent" in _render(slot)
    with pytest.raises(ValueError, match="Unknown Schedule-X slot"):
        schedule_x_slot("notASlot", rx.text("x"))
    with pytest.raises(ValueError, match="requires a slot name"):
        schedule_x_slot(rx.text("x"))
    assert set(SLOT_NAMES) >= {"eventModal", "headerContentRightAppend", "monthGridEvent"}


def test_slot_helpers_render():
    assert "time_range" in _render(schedule_x_field("time_range", format="time"))
    assert "location" in _render(schedule_x_show("location", rx.text("x")))
    rendered = _render(schedule_x_action(rx.button("Delete"), action="delete", close_modal=True))
    assert "closeModal" in rendered
    assert "delete" in rendered


def test_pickers_render():
    assert "onChange" in _render(schedule_x_date_picker(value="2026-01-01", on_change=_State.on_text))
    assert "is12Hour" in _render(schedule_x_time_picker(value="10:00", is_12_hour=True, on_change=_State.on_text))
