"""Sample data for the demo, generated relative to today so the calendar is never empty."""

from __future__ import annotations

import datetime as dt
from typing import Any

from reflex_schedule_x import background_event, calendar_event, calendar_type

TODAY = dt.date.today()


def monday_of(day: dt.date) -> dt.date:
    """Return the Monday of the week containing ``day``."""
    return day - dt.timedelta(days=day.weekday())


WEEK_START = monday_of(TODAY)


def at(day_offset: int, hour: int, minute: int = 0) -> dt.datetime:
    """A naive datetime ``day_offset`` days after this week's Monday."""
    day = WEEK_START + dt.timedelta(days=day_offset)
    return dt.datetime(day.year, day.month, day.day, hour, minute)


def day(day_offset: int) -> dt.date:
    """A date ``day_offset`` days after this week's Monday."""
    return WEEK_START + dt.timedelta(days=day_offset)


CALENDARS: dict[str, dict[str, Any]] = {
    "work": calendar_type(
        "work", "#f91c45", "#ffd2dc", "#59000d",
        dark_main="#ffc0cc", dark_container="#a24258", dark_on_container="#ffdee6", label="Work",
    ),
    "personal": calendar_type(
        "personal", "#f9d71c", "#fff5aa", "#594800",
        dark_main="#fff5c0", dark_container="#a29742", dark_on_container="#fff5de", label="Personal",
    ),
    "leisure": calendar_type(
        "leisure", "#1cf9b0", "#dafff0", "#004d3d",
        dark_main="#c0fff5", dark_container="#42a297", dark_on_container="#e6fff5", label="Leisure",
    ),
    "school": calendar_type(
        "school", "#1c7df9", "#d2e7ff", "#002859",
        dark_main="#c0dfff", dark_container="#426aa2", dark_on_container="#dee6ff", label="School",
    ),
}  # fmt: skip

CALENDAR_COLORS: dict[str, str] = {key: value["lightColors"]["main"] for key, value in CALENDARS.items()}


def sample_events() -> list[dict[str, Any]]:
    """A realistic week (plus neighbours) of events across all calendars."""
    return [
        calendar_event("e1", at(0, 9), at(0, 9, 30), "Daily stand-up", calendar_id="work",
                       location="Zoom", people=["Ana", "Luis", "Sofía"], description="Sync on sprint goals."),
        calendar_event("e2", at(0, 11), at(0, 12, 30), "Architecture review", calendar_id="work",
                       location="Room 4B", people=["Sofía", "María"], description="Review the event bus ADR."),
        calendar_event("e3", at(0, 18), at(0, 19, 30), "Gym", calendar_id="leisure", location="Downtown gym"),
        calendar_event("e4", at(1, 8), at(1, 10), "Python course", calendar_id="school",
                       description="Async patterns and structured concurrency."),
        calendar_event("e5", at(1, 13), at(1, 14), "Lunch with Carla", calendar_id="personal", location="Café Arábica"),
        calendar_event("e6", at(1, 15), at(1, 17), "Reflex component sprint", calendar_id="work",
                       people=["Luis"], description="Ship reflex-schedule-x."),
        calendar_event("e7", at(2, 9), at(2, 9, 30), "Daily stand-up", calendar_id="work", location="Zoom"),
        calendar_event("e8", at(2, 10), at(2, 11), "1:1 with manager", calendar_id="work"),
        calendar_event("e9", at(2, 10, 30), at(2, 12), "Code review marathon", calendar_id="work"),
        calendar_event("e10", at(2, 19), at(2, 21), "Movie night", calendar_id="leisure", location="Cinema"),
        calendar_event("e11", at(3, 7), at(3, 8), "Morning run", calendar_id="leisure"),
        calendar_event("e12", at(3, 14), at(3, 16), "Client workshop", calendar_id="work",
                       location="HQ", people=["Ana", "Client team"], description="Scheduling requirements."),
        calendar_event("e13", at(4, 9), at(4, 9, 30), "Daily stand-up", calendar_id="work"),
        calendar_event("e14", at(4, 16), at(4, 18), "Sprint demo", calendar_id="work", location="Auditorium"),
        calendar_event("e15", day(5), day(6), "Beach weekend", calendar_id="leisure", location="Choroní"),
        calendar_event("e16", day(2), day(2), "Mom's birthday", calendar_id="personal"),
        calendar_event("e17", at(7, 10), at(7, 11), "Planning next sprint", calendar_id="work"),
        calendar_event("e18", at(8, 17), at(8, 18, 30), "Guitar lesson", calendar_id="personal"),
        calendar_event("e19", day(9), day(11), "PyCon workshop", calendar_id="school", location="Barcelona"),
        calendar_event("e20", at(-3, 10), at(-3, 12), "Retrospective", calendar_id="work"),
        calendar_event("e21", at(-5, 9), at(-5, 11), "Hackathon prep", calendar_id="school"),
        calendar_event("e22", at(4, 20), at(5, 1), "Late night deploy", calendar_id="work",
                       description="Crosses midnight to show multi-day timed events."),
    ]  # fmt: skip


def sample_background_events() -> list[dict[str, Any]]:
    """Lunch breaks and a holiday rendered behind regular events."""
    stripes = {
        "backgroundImage": "repeating-linear-gradient(45deg, #ccc, #ccc 5px, transparent 5px, transparent 10px)",
        "opacity": 0.45,
    }
    return [
        *(background_event(at(i, 12), at(i, 13), {"background": "rgba(249, 215, 28, 0.18)"}, "Lunch break")
          for i in range(5)),
        background_event(day(4), day(4), stripes, "Public holiday"),
    ]  # fmt: skip


RECURRING_EVENTS: list[dict[str, Any]] = [
    calendar_event("r1", at(0, 9), at(0, 9, 15), "Stand-up (Mon–Fri)", calendar_id="work",
                   rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=40"),
    calendar_event("r2", at(1, 18), at(1, 19), "Bi-weekly Tue & Thu yoga", calendar_id="leisure",
                   rrule="FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH;COUNT=12"),
    calendar_event("r3", day(0), day(0), "Weekly report (4 times)", calendar_id="school", rrule="FREQ=WEEKLY;COUNT=4"),
    calendar_event("r4", at(2, 12), at(2, 13), "Daily lunch, 5 times", calendar_id="personal", rrule="FREQ=DAILY;COUNT=5"),
    calendar_event("r5", at(3, 16), at(3, 17), "Monthly review", calendar_id="work", rrule="FREQ=MONTHLY;COUNT=6"),
    calendar_event("r6", at(0, 15), at(0, 16), "Weekly sync with exclusions", calendar_id="work",
                   rrule="FREQ=WEEKLY;COUNT=6",
                   exdate=[(at(7, 15)).strftime("%Y%m%dT%H%M%S")]),
]  # fmt: skip


def ics_sample() -> str:
    """An iCalendar document with a single and a recurring event (times in UTC)."""
    d1 = day(1).strftime("%Y%m%d")
    d3 = day(3).strftime("%Y%m%d")
    return (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "CALSCALE:GREGORIAN\n"
        "BEGIN:VEVENT\n"
        "SUMMARY:ICS · Dentist appointment\n"
        f"DTSTART:{d1}T140000Z\n"
        f"DTEND:{d1}T150000Z\n"
        "LOCATION:Clínica Central\n"
        "DESCRIPTION:Imported from an .ics string\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "RRULE:FREQ=DAILY;COUNT=3\n"
        "SUMMARY:ICS · Night study session\n"
        f"DTSTART:{d3}T200000Z\n"
        f"DTEND:{d3}T213000Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )
