# reflex-schedule-x

[![Quality](https://github.com/ecrespo/reflex-schedule-x/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/ecrespo/reflex-schedule-x/actions/workflows/quality.yml)
[![Security](https://github.com/ecrespo/reflex-schedule-x/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/ecrespo/reflex-schedule-x/actions/workflows/security.yml)
[![PyPI](https://img.shields.io/pypi/v/reflex-schedule-x)](https://pypi.org/project/reflex-schedule-x/)
[![Python](https://img.shields.io/pypi/pyversions/reflex-schedule-x)](https://pypi.org/project/reflex-schedule-x/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Schedule-X](https://schedule-x.dev) event calendar for [Reflex](https://reflex.dev) — a modern alternative to
FullCalendar and react-big-calendar, driven entirely from Python.

- **6 views**: day, week, month grid, month agenda, week agenda and list.
- **Events in Reflex state**: pass a `list[dict]` with plain date strings; edits in Python update the running calendar.
- **Every callback** (`on_event_click`, `on_range_update`, `on_click_date_time`, `on_view_change`, ...) as typed Reflex event triggers.
- **Plugins**: events service, calendar controls, current time, event modal, scroll controller, event recurrence (RRULE / EXDATE), iCalendar import, timezone select.
- **Custom components**: fill any Schedule-X slot (`timeGridEvent`, `monthGridEvent`, `eventModal`, header slots, ...) with Reflex components.
- **i18n & timezones**: 37 locales, translation overrides, IANA timezones, dark mode, `default` and `shadcn` themes.
- **Standalone** date picker and time picker components.
- **Imperative API** (`ScheduleXAPI`) for `rx.call_script` driven control.

Bundles `@schedule-x/*` **4.8.0** (open-source packages). Premium plugins (drag & drop, resize, drag-to-create,
resource scheduler, ...) are not included.

## Installation

```bash
pip install reflex-schedule-x
# or
uv add reflex-schedule-x
```

Requires `reflex>=0.9.11`. The npm packages are installed automatically by Reflex.

## Quick start

```python
import reflex as rx
from reflex_schedule_x import calendar_type, schedule_x


class State(rx.State):
    events: list[dict] = [
        {"id": "1", "title": "Coffee with John", "start": "2026-09-17 10:05", "end": "2026-09-17 10:35", "calendarId": "work"},
        {"id": "2", "title": "Ski trip", "start": "2026-09-19", "end": "2026-09-21"},
    ]
    selected: dict = {}

    @rx.event
    def on_event_click(self, event: dict):
        self.selected = event


def index():
    return schedule_x(
        events=State.events,
        calendars={"work": calendar_type("work", "#f91c45", "#ffd2dc", "#59000d", label="Work")},
        views=["day", "week", "month-grid", "month-agenda"],
        default_view="week",
        timezone="America/Caracas",
        locale="es-ES",
        is_dark=rx.color_mode_cond(light=False, dark=True),
        event_modal=True,
        current_time_indicator=True,
        on_event_click=State.on_event_click,
        height="800px",
    )


app = rx.App()
app.add_page(index)
```

## Dates and times

Schedule-X uses the Temporal API. The component converts strings for you:

| Value you pass | Meaning |
| --- | --- |
| `"2026-09-17"` | All-day date (`Temporal.PlainDate`) |
| `"2026-09-17 10:00"` or `"2026-09-17T10:00"` | Wall-clock time in the calendar `timezone` |
| `"2026-09-17T10:00:00-04:00"` / `"...Z"` | Absolute instant, shown in the calendar `timezone` |
| `"2026-09-17T10:00:00+02:00[Europe/Berlin]"` | RFC 9557 zoned date-time |

Payloads sent back to Python use `"YYYY-MM-DD"` for dates and `"YYYY-MM-DD HH:mm"` (calendar timezone) for
date-times, so they round-trip with your state. Set `datetime_format="iso"` to receive RFC 9557 strings instead.

Helpers: `to_sx_datetime(date | datetime)`, `to_sx_date(...)`, `parse_sx_datetime(str)`,
`calendar_event(...)`, `background_event(...)`, `calendar_type(...)`.

## `schedule_x` props

Props marked **live** update the running calendar; changing any other prop re-creates it.

| Prop | Type | Notes |
| --- | --- | --- |
| `events` | `list[dict]` | **live**. `id`, `start`, `end`, `title`, `description`, `location`, `people`, `calendarId`, `rrule`, `exdate`, `_options`, `_customContent`, any custom key |
| `background_events` | `list[dict]` | **live**. `start`, `end`, `style`, `title`, `rrule`, `exdate` |
| `calendars` | `dict[str, dict]` | **live**. `colorName`, `label`, `lightColors`, `darkColors` |
| `views` | `list[str]` | `day`, `week`, `month-grid`, `month-agenda`, `week-agenda`, `list` |
| `default_view` | `str` | Initial view |
| `view` | `str` | **live**, controlled view (pair with `on_view_change`) |
| `selected_date` | `str` | **live**, `YYYY-MM-DD` |
| `min_date` / `max_date` | `str` | **live** |
| `locale` | `str` | **live**, see `reflex_schedule_x.LOCALES` |
| `timezone` | `str` | **live**, IANA name, default `UTC` |
| `first_day_of_week` | `int` | **live**, 1 = Monday … 7 = Sunday |
| `translations` | `dict` | Overrides merged over the built-in texts: `{"en-US": {"Week": "4 days"}}` |
| `day_boundaries` | `dict` | **live**, `{"start": "06:00", "end": "18:00"}` |
| `week_options` | `dict` | **live**, `gridHeight`, `nDays`, `eventWidth`, `gridStep`, `eventOverlap`, `timeAxisFormatOptions` |
| `month_grid_options` | `dict` | **live**, `{"nEventsPerDay": 4}` |
| `month_agenda_options` | `dict` | `{"nEventIndicatorsPerDay": 3}` |
| `show_week_numbers`, `is_responsive`, `skip_animations`, `skip_validation` | `bool` | |
| `small_breakpoint` | `int` | Width (px) under which small-screen views are used |
| `date_picker` | `dict` | Header date picker options |
| `theme` | `"default" \| "shadcn"` | Literal value; use one theme per app |
| `is_dark` | `bool` | **live** |
| `current_time_indicator`, `current_time_full_week_width` | `bool` | current-time plugin |
| `event_modal` | `bool` | event-modal plugin |
| `initial_scroll` / `scroll_to` | `str` | scroll-controller plugin; `scroll_to` is **live** |
| `recurrence` | `bool` | event-recurrence plugin |
| `ical_data` | `str` | iCalendar plugin (times are treated as UTC) |
| `timezone_select` | `bool` | timezone-select plugin |
| `datetime_format` | `"naive" \| "iso"` | Format of date-times in payloads |
| `id` | `str` | Enables `ScheduleXAPI(id)` |

The calendar defaults to `width="100%"`, `height="800px"`, `max_height="90vh"`; override with normal style props.

## Event triggers

| Trigger | Payload |
| --- | --- |
| `on_event_click`, `on_double_click_event`, `on_event_update` | event `dict` (plus `is_all_day`) |
| `on_range_update` | `{"start": str, "end": str}` |
| `on_calendar_render` | `{"view": str, "date": str, "range": {...}}` |
| `on_view_change` | view name |
| `on_selected_date_update`, `on_click_date`, `on_double_click_date`, `on_click_agenda_date`, `on_double_click_agenda_date`, `on_click_plus_events`, `on_scroll_day_into_view` | `"YYYY-MM-DD"` |
| `on_click_date_time`, `on_double_click_date_time` | `"YYYY-MM-DD HH:mm"` |
| `on_slot_action` | `{"action", "slot", "event", "date"}` |
| `on_error` | error message |

Lazy loading: load events in `on_range_update` (and `on_scroll_day_into_view` for the list view) and assign them to
the `events` state var.

## Custom components (slots)

Put `schedule_x_slot(name, *children)` components inside `schedule_x`. Slot content is normal Reflex UI, so it can use
state. Inside a slot:

- `schedule_x_field(name, format=None)` renders slot data. Event fields: `title`, `description`, `location`,
  `people`, `start`, `end`, `calendarId`, custom keys; virtual fields `time_range`, `date_range`, `calendar_label`.
  Other slots expose `date`, `day`, `hour`, `events`. Formats: `time`, `date`, `datetime`, `weekday`,
  `weekday_short`, `day`, `month`, `hour`, `count`, `upper`, `json`.
- `schedule_x_show(name, *children, negate=False)` renders children when the field is truthy (`is_all_day` too).
- `schedule_x_event_card(*children, variant="container" | "main")` paints the event's calendar colors.
- `schedule_x_action(*children, action="delete", close_modal=True)` sends clicks to `on_slot_action`.

```python
schedule_x(
    schedule_x_slot(
        "timeGridEvent",
        schedule_x_event_card(
            schedule_x_field("title", tag_name="strong"),
            schedule_x_field("time_range"),
            schedule_x_show("location", schedule_x_field("location")),
        ),
    ),
    schedule_x_slot(
        "eventModal",
        rx.card(
            schedule_x_field("title", tag_name="h3"),
            schedule_x_action(rx.button("Delete"), action="delete", close_modal=True),
        ),
    ),
    schedule_x_slot("headerContentRightPrepend", rx.button("New", on_click=State.new_event)),
    events=State.events,
    event_modal=True,
    on_slot_action=State.on_slot_action,
)
```

Supported slots: `timeGridEvent`, `dateGridEvent`, `monthGridEvent`, `monthAgendaEvent`, `weekAgendaEvent`,
`monthAgendaDateDots`, `eventModal`, `headerContent`, `headerContentLeftPrepend`, `headerContentLeftAppend`,
`headerContentRightPrepend`, `headerContentRightAppend`, `weekGridDate`, `weekGridHour`, `monthGridDayName`,
`monthGridDate`.

## Imperative API

```python
from reflex_schedule_x import ScheduleXAPI

api = ScheduleXAPI("my-calendar")  # schedule_x(id="my-calendar")

rx.button("Week", on_click=api.set_view("week"))
rx.button("Today", on_click=api.set_date(datetime.date.today()))
rx.button("Dump", on_click=api.get_events(callback=State.receive_events))
```

Methods: `set_view`, `set_date`, `set_theme`, `add_event`, `update_event`, `remove_event`, `set_events`,
`close_event_modal`, `scroll_to`, `get_view`, `get_date`, `get_range`, `get_events`, `get_event`.

## Date and time pickers

```python
schedule_x_date_picker(value=State.date, on_change=State.set_date, locale="es-ES", label="Fecha", min="2026-01-01")
schedule_x_time_picker(value=State.time, on_change=State.set_time, is_12_hour=True, label="Hora")
```

## Demo app

The `schedule_x_demo/` folder contains a multi-page demo: playground with every option, events CRUD and callback
log, custom components, recurrence + background events + iCal, language and timezones, imperative API with the list
view, and the pickers.

```bash
uv venv && uv pip install -e .
cd schedule_x_demo
uv pip install -r requirements.txt
uv run reflex run
```

## Development

```bash
uv sync --extra dev
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov
uv run reflex component build   # generates .pyi stubs and builds sdist + wheel
```

Branches: work happens on `develop`; `main` only receives pull requests from `develop`. The `Quality` (ruff, pytest on
Python 3.10–3.13, build, stub freshness, demo bundle) and `Security` (CodeQL, Bandit, pip-audit, Gitleaks, dependency
review) workflows must pass before merging.

## License

MIT © Ernesto Crespo. Schedule-X is MIT licensed, © Tom Österlund.
