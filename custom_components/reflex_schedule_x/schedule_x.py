"""Reflex wrapper for the Schedule-X event calendar (https://schedule-x.dev).

The heavy lifting happens in ``schedule_x.jsx``: it turns the JSON props sent by
Reflex into Temporal objects, plugins and callbacks, and turns Schedule-X
callbacks back into JSON payloads for Reflex event handlers.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import reflex as rx
from reflex_base.components.component import (
    MemoizationLeaf,
    NoSSRComponent,
    field,
)
from reflex_base.event import EventHandler, passthrough_event_spec
from reflex_base.utils.imports import ImportDict, ImportVar
from reflex_base.vars.base import LiteralVar, Var

# --------------------------------------------------------------------------- #
#                               Package versions                              #
# --------------------------------------------------------------------------- #

SCHEDULE_X_VERSION = "4.8.0"
"""Version of the @schedule-x/* npm packages bundled by this component."""

TEMPORAL_POLYFILL_VERSION = "0.3.0"
"""temporal-polyfill version required by @schedule-x/calendar as peer dependency."""

_SX_PACKAGES = (
    "calendar",
    "calendar-controls",
    "current-time",
    "date-picker",
    "event-modal",
    "event-recurrence",
    "events-service",
    "ical",
    "scroll-controller",
    "theme-default",
    "theme-shadcn",
    "time-picker",
    "timezone-select",
    "translations",
)

LIB_DEPENDENCIES: list[str] = [
    *(f"@schedule-x/{pkg}@{SCHEDULE_X_VERSION}" for pkg in _SX_PACKAGES),
    f"temporal-polyfill@{TEMPORAL_POLYFILL_VERSION}",
    "preact@10.29.0",
    "@preact/signals@2.5.1",
]

_JSX_MODULE = rx.asset("schedule_x.jsx", shared=True)
_LIBRARY = _JSX_MODULE.importable_path

THEME_CSS = {
    "default": "@schedule-x/theme-default/dist/index.css",
    "shadcn": "@schedule-x/theme-shadcn/dist/index.css",
}

# --------------------------------------------------------------------------- #
#                                    Types                                    #
# --------------------------------------------------------------------------- #

ViewName = Literal["day", "week", "month-grid", "month-agenda", "week-agenda", "list"]
ThemeName = Literal["default", "shadcn"]
DatetimeFormat = Literal["naive", "iso"]

VIEWS: tuple[str, ...] = ("day", "week", "month-grid", "month-agenda", "week-agenda", "list")

SLOT_NAMES: tuple[str, ...] = (
    "timeGridEvent",
    "dateGridEvent",
    "monthGridEvent",
    "monthAgendaEvent",
    "weekAgendaEvent",
    "monthAgendaDateDots",
    "eventModal",
    "headerContentLeftPrepend",
    "headerContentLeftAppend",
    "headerContentRightPrepend",
    "headerContentRightAppend",
    "headerContent",
    "weekGridDate",
    "weekGridHour",
    "monthGridDayName",
    "monthGridDate",
)
"""Custom component slots supported by Schedule-X (see schedule-x.dev/docs/frameworks/react)."""


class CalendarEvent(TypedDict, total=False):
    """Payload of an event sent back by the calendar."""

    id: str | int
    title: str
    start: str
    end: str
    description: str
    location: str
    people: list[str]
    calendarId: str
    rrule: str
    exdate: list[str]
    is_all_day: bool


class DateRange(TypedDict):
    """Visible date range sent by ``on_range_update``."""

    start: str
    end: str


class RenderInfo(TypedDict):
    """Payload sent by ``on_calendar_render``."""

    view: str
    date: str
    range: DateRange | None


class SlotAction(TypedDict):
    """Payload sent by ``on_slot_action`` when a ``schedule_x_action`` is clicked."""

    action: str
    slot: str
    event: CalendarEvent | None
    date: str | None


def _literal_value(value: Any, default: Any = None) -> Any:
    """Return the Python value of a literal Var (or the value itself)."""
    if isinstance(value, LiteralVar):
        return getattr(value, "_var_value", default)
    if isinstance(value, Var):
        return default
    return default if value is None else value


# --------------------------------------------------------------------------- #
#                                  Calendar                                   #
# --------------------------------------------------------------------------- #


class ScheduleX(NoSSRComponent, MemoizationLeaf):
    """The Schedule-X event calendar.

    Props are plain JSON (strings for dates). Changing ``events``, ``view``,
    ``selected_date``, ``locale``, ``timezone``, ``first_day_of_week``,
    ``day_boundaries``, ``week_options``, ``month_grid_options``, ``calendars``,
    ``min_date``, ``max_date``, ``is_dark`` or ``scroll_to`` updates the running
    calendar in place. Changing any other prop re-creates the calendar.
    """

    library = _LIBRARY
    tag = "ScheduleXCalendar"
    lib_dependencies: list[str] = LIB_DEPENDENCIES

    # ----- data ----------------------------------------------------------- #
    events: Var[list[dict[str, Any]]] = field(
        doc=(
            "Calendar events. Each dict needs `id`, `start` and `end`; `start`/`end` accept "
            "'YYYY-MM-DD' (all-day), 'YYYY-MM-DD HH:mm' (in `timezone`), ISO strings with offset, "
            "or RFC 9557 strings. Optional: title, description, location, people, calendarId "
            "(or calendar_id), rrule, exdate, _options, _customContent and any custom key."
        )
    )
    background_events: Var[list[dict[str, Any]]] = field(
        doc="Background events: dicts with start, end, style (CSS dict) and optional title/rrule/exdate."
    )
    calendars: Var[dict[str, dict[str, Any]]] = field(
        doc="Calendar categories keyed by id: {colorName, label, lightColors: {main, container, onContainer}, darkColors}."
    )

    # ----- views & navigation -------------------------------------------- #
    views: Var[list[str]] = field(
        doc="Views to enable: day, week, month-grid, month-agenda, week-agenda, list. Defaults to day/week/month-grid/month-agenda."
    )
    default_view: Var[str] = field(doc="View shown on first render.")
    view: Var[str] = field(doc="Controlled current view. Updates the running calendar when it changes.")
    selected_date: Var[str] = field(doc="Selected date 'YYYY-MM-DD'. Updates the running calendar when it changes.")
    min_date: Var[str] = field(doc="Minimum navigable date 'YYYY-MM-DD'.")
    max_date: Var[str] = field(doc="Maximum navigable date 'YYYY-MM-DD'.")

    # ----- localisation --------------------------------------------------- #
    locale: Var[str] = field(doc="Locale such as 'en-US' or 'es-ES'. Defaults to 'en-US'.")
    timezone: Var[str] = field(doc="IANA timezone, e.g. 'America/Caracas'. Defaults to 'UTC'.")
    first_day_of_week: Var[int] = field(doc="First day of the week: 1 = Monday ... 7 = Sunday.")
    translations: Var[dict[str, dict[str, str]]] = field(
        doc="Translation overrides merged over the built-in ones, keyed by locale: {'en-US': {'Week': '4 days'}}."
    )

    # ----- layout --------------------------------------------------------- #
    day_boundaries: Var[dict[str, str]] = field(
        doc="Visible hours in week/day grids: {'start': '06:00', 'end': '18:00'}."
    )
    week_options: Var[dict[str, Any]] = field(
        doc="Week grid options: gridHeight, nDays, eventWidth, timeAxisFormatOptions, eventOverlap, gridStep (snake_case accepted)."
    )
    month_grid_options: Var[dict[str, Any]] = field(doc="Month grid options: {'nEventsPerDay': 4}.")
    month_agenda_options: Var[dict[str, Any]] = field(doc="Month agenda options: {'nEventIndicatorsPerDay': 3}.")
    show_week_numbers: Var[bool] = field(doc="Show week numbers.")
    is_responsive: Var[bool] = field(doc="Switch to small-screen views below the breakpoint. Defaults to true.")
    small_breakpoint: Var[int] = field(doc="Custom width (px) below which the calendar counts as small.")
    skip_animations: Var[bool] = field(doc="Disable navigation transitions.")
    skip_validation: Var[bool] = field(doc="Skip event validation (faster for large data sets).")
    date_picker: Var[dict[str, Any]] = field(
        doc="Options for the header date picker (e.g. {'placement': 'bottom-end'})."
    )

    # ----- theme ---------------------------------------------------------- #
    theme: Var[str] = field(doc="'default' or 'shadcn'. Use a literal value; one theme per app.")
    is_dark: Var[bool] = field(doc="Dark mode. Can be bound to rx.color_mode == 'dark'.")

    # ----- plugins -------------------------------------------------------- #
    current_time_indicator: Var[bool] = field(doc="Enable the current-time plugin.")
    current_time_full_week_width: Var[bool] = field(doc="Draw the current-time line across the whole week.")
    event_modal: Var[bool] = field(doc="Enable the event-modal plugin (customizable with the 'eventModal' slot).")
    initial_scroll: Var[str] = field(doc="Enable the scroll-controller plugin with this initial time, e.g. '07:50'.")
    scroll_to: Var[str] = field(doc="Scroll the week/day grid to 'HH:mm' whenever this changes (needs initial_scroll).")
    recurrence: Var[bool] = field(doc="Enable the event-recurrence plugin (RFC 5545 rrule / exdate on events).")
    ical_data: Var[str] = field(doc="iCalendar (.ics) text to load through the ical plugin.")
    timezone_select: Var[bool] = field(doc="Show the timezone-select plugin in the header.")

    # ----- misc ----------------------------------------------------------- #
    datetime_format: Var[str] = field(
        doc="Format of date-times sent to Python: 'naive' ('YYYY-MM-DD HH:mm' in the calendar timezone) or 'iso' (RFC 9557)."
    )

    # ----- event triggers ------------------------------------------------- #
    on_event_click: EventHandler[passthrough_event_spec(CalendarEvent)] = field(doc="An event was clicked.")
    on_double_click_event: EventHandler[passthrough_event_spec(CalendarEvent)] = field(
        doc="An event was double-clicked."
    )
    on_event_update: EventHandler[passthrough_event_spec(CalendarEvent)] = field(
        doc="An event was changed by an interactive plugin (drag & drop, resize, ...)."
    )
    on_range_update: EventHandler[passthrough_event_spec(DateRange)] = field(doc="The visible range changed.")
    on_selected_date_update: EventHandler[passthrough_event_spec(str)] = field(doc="The selected date changed.")
    on_view_change: EventHandler[passthrough_event_spec(str)] = field(doc="The active view changed.")
    on_click_date: EventHandler[passthrough_event_spec(str)] = field(doc="A month-grid date was clicked.")
    on_double_click_date: EventHandler[passthrough_event_spec(str)] = field(doc="A month-grid date was double-clicked.")
    on_click_date_time: EventHandler[passthrough_event_spec(str)] = field(doc="The week/day time grid was clicked.")
    on_double_click_date_time: EventHandler[passthrough_event_spec(str)] = field(
        doc="The week/day time grid was double-clicked."
    )
    on_click_agenda_date: EventHandler[passthrough_event_spec(str)] = field(doc="A month-agenda date was clicked.")
    on_double_click_agenda_date: EventHandler[passthrough_event_spec(str)] = field(
        doc="A month-agenda date was double-clicked."
    )
    on_click_plus_events: EventHandler[passthrough_event_spec(str)] = field(doc="The '+ N events' button was clicked.")
    on_scroll_day_into_view: EventHandler[passthrough_event_spec(str)] = field(
        doc="A day scrolled into view in the list view (use it to lazy-load events)."
    )
    on_calendar_render: EventHandler[passthrough_event_spec(RenderInfo)] = field(doc="The calendar finished rendering.")
    on_slot_action: EventHandler[passthrough_event_spec(SlotAction)] = field(
        doc="A schedule_x_action inside a slot was clicked."
    )
    on_error: EventHandler[passthrough_event_spec(str)] = field(doc="The calendar could not be created.")

    def add_imports(self) -> ImportDict:
        """Import the theme stylesheet selected by ``theme`` plus plugin stylesheets.

        Returns:
            The CSS side-effect imports.
        """
        theme = _literal_value(self.theme, "default")
        css = THEME_CSS.get(str(theme), THEME_CSS["default"])
        return {
            css: [ImportVar(tag=None, install=False)],
            # The timezone-select plugin ships its own stylesheet.
            "@schedule-x/timezone-select/index.css": [ImportVar(tag=None, install=False)],
        }

    def add_style(self) -> dict[str, Any] | None:
        """Give the calendar a sensible default size.

        Returns:
            The default style.
        """
        return {"width": "100%", "height": "800px", "max_height": "90vh"}

    @classmethod
    def create(cls, *children, **props) -> ScheduleX:
        """Create the calendar.

        Args:
            *children: ``schedule_x_slot`` components (custom components).
            **props: Calendar props.

        Returns:
            The component.
        """
        return super().create(*children, **props)  # type: ignore[return-value]


class ScheduleXSlot(NoSSRComponent):
    """Custom content for a Schedule-X slot (must be a direct child of ``schedule_x``).

    Inside the slot use ``schedule_x_field``, ``schedule_x_show``,
    ``schedule_x_event_card`` and ``schedule_x_action`` to read the slot data.
    """

    library = _LIBRARY
    tag = "ScheduleXSlot"

    slot_name: Var[str] = field(doc=f"Slot to fill. One of: {', '.join(SLOT_NAMES)}.")

    @classmethod
    def create(cls, *children, **props) -> ScheduleXSlot:
        """Create a slot.

        Args:
            *children: The content rendered inside the slot.
            **props: ``slot_name`` (or ``slot`` / first positional str).

        Returns:
            The component.

        Raises:
            ValueError: If the slot name is missing or unknown.
        """
        if children and isinstance(children[0], str) and "slot_name" not in props and "slot" not in props:
            props["slot_name"], children = children[0], children[1:]
        if "slot" in props:
            props["slot_name"] = props.pop("slot")
        name = props.get("slot_name")
        if name is None:
            msg = "schedule_x_slot requires a slot name, e.g. schedule_x_slot('timeGridEvent', ...)."
            raise ValueError(msg)
        if isinstance(name, str) and name not in SLOT_NAMES:
            msg = f"Unknown Schedule-X slot {name!r}. Expected one of: {', '.join(SLOT_NAMES)}."
            raise ValueError(msg)
        return super().create(*children, **props)  # type: ignore[return-value]


class ScheduleXField(NoSSRComponent):
    """Text of a slot field, e.g. the event title, formatted for display."""

    library = _LIBRARY
    tag = "ScheduleXField"

    name: Var[str] = field(
        doc=(
            "Field name or dotted path in the slot props. Event fields: title, description, location, "
            "people, calendarId, start, end, id or custom keys. Virtual: time_range, date_range, "
            "calendar_label. Other slots: date, hour, day, jsDate."
        )
    )
    format: Var[str] = field(
        doc="Optional format: time, date, datetime, weekday, weekday_short, day, month, hour, count, upper, json."
    )
    fallback: Var[str] = field(doc="Text shown when the field is empty.")
    tag_name: Var[str] = field(doc="HTML tag to render (default span).")

    @classmethod
    def create(cls, *children, **props) -> ScheduleXField:
        """Create a field.

        Args:
            *children: A single string is used as the field name.
            **props: Component props.

        Returns:
            The component.
        """
        if children and isinstance(children[0], str) and "name" not in props:
            props["name"], children = children[0], children[1:]
        return super().create(*children, **props)  # type: ignore[return-value]


class ScheduleXShow(NoSSRComponent):
    """Render children only when a slot field is truthy (``negate`` inverts it)."""

    library = _LIBRARY
    tag = "ScheduleXShow"

    name: Var[str] = field(doc="Field to test, e.g. location, people, description or is_all_day.")
    negate: Var[bool] = field(doc="Render when the field is falsy instead.")

    @classmethod
    def create(cls, *children, **props) -> ScheduleXShow:
        """Create the conditional wrapper.

        Args:
            *children: Content. A leading string is used as the field name.
            **props: Component props.

        Returns:
            The component.
        """
        if children and isinstance(children[0], str) and "name" not in props:
            props["name"], children = children[0], children[1:]
        return super().create(*children, **props)  # type: ignore[return-value]


class ScheduleXEventCard(NoSSRComponent):
    """A box painted with the colors of the event's calendar."""

    library = _LIBRARY
    tag = "ScheduleXEventCard"

    variant: Var[str] = field(doc="'container' (soft background, colored border) or 'main' (solid).")


class ScheduleXAction(NoSSRComponent):
    """Clickable wrapper that fires the calendar's ``on_slot_action`` with the slot's event/date."""

    library = _LIBRARY
    tag = "ScheduleXAction"

    action: Var[str] = field(doc="Action name delivered in the payload, e.g. 'delete'.")
    close_modal: Var[bool] = field(doc="Close the event modal after the action.")
    stop_propagation: Var[bool] = field(doc="Stop the click from reaching the calendar. Defaults to true.")


# --------------------------------------------------------------------------- #
#                           Standalone date / time                            #
# --------------------------------------------------------------------------- #


class _ThemedPicker(NoSSRComponent):
    library = _LIBRARY
    lib_dependencies: list[str] = LIB_DEPENDENCIES

    theme: Var[str] = field(doc="'default' or 'shadcn' stylesheet (literal).")

    def add_imports(self) -> ImportDict:
        theme = _literal_value(self.theme, "default")
        css = THEME_CSS.get(str(theme), THEME_CSS["default"])
        return {css: [ImportVar(tag=None, install=False)]}


class ScheduleXDatePicker(_ThemedPicker):
    """The standalone Schedule-X date picker."""

    tag = "ScheduleXDatePicker"

    value: Var[str] = field(doc="Selected date 'YYYY-MM-DD'.")
    locale: Var[str] = field(doc="Locale, e.g. 'es-ES'.")
    first_day_of_week: Var[int] = field(doc="1 = Monday ... 7 = Sunday.")
    min: Var[str] = field(doc="Minimum date 'YYYY-MM-DD'.")
    max: Var[str] = field(doc="Maximum date 'YYYY-MM-DD'.")
    placement: Var[str] = field(doc="Popup placement: top-start, top-end, bottom-start, bottom-end.")
    dark: Var[bool] = field(doc="Dark mode.")
    full_width: Var[bool] = field(doc="Stretch the input to its container.")
    label: Var[str] = field(doc="Input label.")
    name: Var[str] = field(doc="Input name.")
    disabled: Var[bool] = field(doc="Disable the input.")
    has_placeholder: Var[bool] = field(doc="Show a placeholder instead of a date when no value is set.")
    timezone: Var[str] = field(doc="IANA timezone used to compute 'today'.")

    on_change: EventHandler[passthrough_event_spec(str)] = field(doc="Selected date changed ('YYYY-MM-DD').")


class ScheduleXTimePicker(_ThemedPicker):
    """The standalone Schedule-X time picker."""

    tag = "ScheduleXTimePicker"

    def add_imports(self) -> ImportDict:
        """Import the theme plus the time-picker stylesheet (not part of index.css).

        Returns:
            The CSS side-effect imports.
        """
        imports = dict(super().add_imports())
        if str(_literal_value(self.theme, "default")) != "shadcn":
            imports["@schedule-x/theme-default/dist/time-picker.css"] = [ImportVar(tag=None, install=False)]
        return imports

    value: Var[str] = field(doc="Time 'HH:mm'.")
    locale: Var[str] = field(doc="Locale used for the buttons, e.g. 'es-ES'.")
    dark: Var[bool] = field(doc="Dark mode.")
    placement: Var[str] = field(doc="Popup placement: top-start, top-end, bottom-start, bottom-end.")
    label: Var[str] = field(doc="Input label.")
    name: Var[str] = field(doc="Input name.")
    is_12_hour: Var[bool] = field(doc="Use a 12-hour clock.")

    on_change: EventHandler[passthrough_event_spec(str)] = field(doc="Time changed ('HH:mm').")


schedule_x = ScheduleX.create
schedule_x_slot = ScheduleXSlot.create
schedule_x_field = ScheduleXField.create
schedule_x_show = ScheduleXShow.create
schedule_x_event_card = ScheduleXEventCard.create
schedule_x_action = ScheduleXAction.create
schedule_x_date_picker = ScheduleXDatePicker.create
schedule_x_time_picker = ScheduleXTimePicker.create
