/**
 * reflex-schedule-x — React bridge between Reflex and the Schedule-X calendar.
 *
 * Schedule-X is configured with Temporal objects, JS callbacks and plugin
 * instances, none of which can cross the Reflex (Python) <-> browser boundary.
 * This module accepts plain JSON props from Reflex, converts them into the
 * shapes Schedule-X expects, wires every callback to a Reflex event trigger with
 * a JSON-serializable payload, and applies prop changes to the live calendar
 * through the calendar-controls and events-service plugins.
 *
 * The custom-component ("slot") rendering mirrors the official
 * @schedule-x/react adapter: Schedule-X hands us a wrapper element and props,
 * and we render React content into it with a portal.
 */
import React, {
  Children,
  createContext,
  isValidElement,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import "temporal-polyfill/global";
import { render as preactRender } from "preact";
import { signal } from "@preact/signals";
import {
  createCalendar,
  createViewDay,
  createViewList,
  createViewMonthAgenda,
  createViewMonthGrid,
  createViewWeek,
  createViewWeekAgenda,
} from "@schedule-x/calendar";
import { createEventsServicePlugin } from "@schedule-x/events-service";
import { createCalendarControlsPlugin } from "@schedule-x/calendar-controls";
import { createCurrentTimePlugin } from "@schedule-x/current-time";
import { createEventModalPlugin } from "@schedule-x/event-modal";
import { createScrollControllerPlugin } from "@schedule-x/scroll-controller";
import {
  createEventRecurrencePlugin,
  createEventsServicePlugin as createRecurringEventsServicePlugin,
} from "@schedule-x/event-recurrence";
import { createIcalendarPlugin } from "@schedule-x/ical";
import {
  createTimezoneSelectPlugin,
  translations as timezoneTranslations,
} from "@schedule-x/timezone-select";
import {
  mergeLocales,
  translate,
  translations as baseTranslations,
} from "@schedule-x/translations";
import { createDatePicker } from "@schedule-x/date-picker";
import { createTimePicker } from "@schedule-x/time-picker";

/* -------------------------------------------------------------------------- */
/*                                   Helpers                                  */
/* -------------------------------------------------------------------------- */

const VIEW_FACTORIES = {
  day: createViewDay,
  week: createViewWeek,
  "month-grid": createViewMonthGrid,
  "month-agenda": createViewMonthAgenda,
  "week-agenda": createViewWeekAgenda,
  list: createViewList,
};

const PLAIN_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const OFFSET_RE = /(?:[zZ]|[+-]\d{2}:?\d{2})$/;

const isTemporal = (value, kind) =>
  typeof Temporal !== "undefined" && value instanceof Temporal[kind];

const snakeToCamel = (key) =>
  key.startsWith("_")
    ? "_" + snakeToCamel(key.slice(1))
    : key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());

/** Recursively camelCase the keys of plain objects (arrays are walked too). */
const camelizeKeys = (value) => {
  if (Array.isArray(value)) return value.map(camelizeKeys);
  if (value && typeof value === "object" && value.constructor === Object) {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[snakeToCamel(k)] = camelizeKeys(v);
    return out;
  }
  return value;
};

const stableStringify = (value) => {
  try {
    return JSON.stringify(value ?? null);
  } catch (e) {
    return String(Math.random());
  }
};

/**
 * Convert a date/time string coming from Python into a Temporal object.
 *
 *  - "2025-01-31"                        -> Temporal.PlainDate (all-day)
 *  - "2025-01-31 10:00" / "...T10:00:00" -> ZonedDateTime in `timezone`
 *  - "2025-01-31T10:00:00-04:00" / "Z"   -> Instant converted to `timezone`
 *  - "2025-01-31T10:00:00-04:00[America/Caracas]" -> ZonedDateTime as given
 */
export const toTemporal = (value, timezone = "UTC") => {
  if (value === null || value === undefined || value === "") return undefined;
  if (isTemporal(value, "PlainDate") || isTemporal(value, "ZonedDateTime")) return value;
  const s = String(value).trim();
  if (PLAIN_DATE_RE.test(s)) return Temporal.PlainDate.from(s);
  if (s.includes("[")) return Temporal.ZonedDateTime.from(s);
  const iso = s.replace(" ", "T");
  if (OFFSET_RE.test(iso) && iso.includes("T")) {
    return Temporal.Instant.from(iso).toZonedDateTimeISO(timezone);
  }
  return Temporal.PlainDateTime.from(iso).toZonedDateTime(timezone);
};

const toPlainDate = (value) => {
  if (value === null || value === undefined || value === "") return undefined;
  if (isTemporal(value, "PlainDate")) return value;
  const s = String(value).trim();
  return Temporal.PlainDate.from(s.length > 10 ? s.slice(0, 10) : s);
};

const pad = (n) => String(n).padStart(2, "0");

/**
 * Serialize a Temporal value for Python.
 * format "naive": "YYYY-MM-DD HH:mm" in the calendar timezone (round-trips with input)
 * format "iso":   RFC 9557 string, e.g. "2025-01-31T10:00:00-04:00[America/Caracas]"
 */
export const fromTemporal = (value, timezone = "UTC", format = "naive") => {
  if (value === null || value === undefined) return value;
  if (isTemporal(value, "PlainDate")) return value.toString();
  if (isTemporal(value, "ZonedDateTime")) {
    const zdt = timezone ? value.withTimeZone(timezone) : value;
    if (format === "iso") return zdt.toString();
    return `${zdt.year}-${pad(zdt.month)}-${pad(zdt.day)} ${pad(zdt.hour)}:${pad(zdt.minute)}`;
  }
  if (isTemporal(value, "PlainDateTime") || isTemporal(value, "Instant")) return value.toString();
  return value;
};

const EVENT_KEY_ALIASES = {
  calendar_id: "calendarId",
  resource_id: "resourceId",
  custom_content: "_customContent",
  _custom_content: "_customContent",
  options: "_options",
};

/** Normalize an event dict from Python into a Schedule-X event. */
const toSxEvent = (event, timezone) => {
  const out = {};
  for (const [rawKey, value] of Object.entries(event || {})) {
    const key = EVENT_KEY_ALIASES[rawKey] || rawKey;
    if (key === "start" || key === "end") out[key] = toTemporal(value, timezone);
    else if (key === "_options" || key === "_customContent") out[key] = camelizeKeys(value);
    else out[key] = value;
  }
  if (out.id === undefined || out.id === null) {
    out.id = `rx-sx-${Math.random().toString(36).slice(2, 11)}`;
  }
  if (out.start && !out.end) out.end = out.start;
  return out;
};

const toSxBackgroundEvent = (event, timezone) => {
  const out = { ...event };
  out.start = toTemporal(event.start, timezone);
  out.end = toTemporal(event.end ?? event.start, timezone);
  out.style = camelizeKeys(event.style || {});
  return out;
};

/** Serialize a Schedule-X event (external shape) for Python. */
const serializeEvent = (event, timezone, format) => {
  if (!event) return null;
  const out = {};
  for (const [key, value] of Object.entries(event)) {
    if (typeof value === "function") continue;
    if (value === null || value === undefined) continue;
    if (key.startsWith("_") && key !== "_options" && key !== "_customContent") continue;
    if (isTemporal(value, "PlainDate") || isTemporal(value, "ZonedDateTime")) {
      out[key] = fromTemporal(value, timezone, format);
    } else {
      out[key] = value;
    }
  }
  out.is_all_day = isTemporal(event.start, "PlainDate");
  return out;
};

const normalizeCalendars = (calendars) => {
  if (!calendars) return undefined;
  const out = {};
  for (const [id, cfg] of Object.entries(calendars)) {
    const c = camelizeKeys(cfg || {});
    out[id] = { colorName: c.colorName || id, ...c };
  }
  return out;
};

const normalizeWeekOptions = (weekOptions) => {
  if (!weekOptions) return undefined;
  return camelizeKeys(weekOptions);
};

const buildViews = (views) => {
  const names = (views && views.length ? views : ["day", "week", "month-grid", "month-agenda"]).map(
    (v) => String(v).replace("_", "-")
  );
  return names
    .filter((name) => {
      if (!VIEW_FACTORIES[name]) {
        console.warn(`[reflex-schedule-x] Unknown view "${name}" ignored.`);
        return false;
      }
      return true;
    })
    .map((name) => VIEW_FACTORIES[name]());
};

const buildTranslations = (custom, withTimezone) => {
  const sources = [baseTranslations];
  if (withTimezone) sources.push(timezoneTranslations);
  if (custom && Object.keys(custom).length) {
    const normalized = {};
    for (const [locale, dict] of Object.entries(custom)) {
      normalized[String(locale).replaceAll("-", "").replaceAll("_", "")] = dict;
    }
    sources.push(normalized);
  }
  return sources.length === 1 ? undefined : mergeLocales(...sources);
};

const safely = (label, fn) => {
  try {
    return fn();
  } catch (e) {
    console.warn(`[reflex-schedule-x] ${label} failed:`, e);
    return undefined;
  }
};

const registry = () => {
  if (typeof window === "undefined") return {};
  window.__reflexScheduleX = window.__reflexScheduleX || {};
  return window.__reflexScheduleX;
};

/* -------------------------------------------------------------------------- */
/*                           Slot (custom components)                         */
/* -------------------------------------------------------------------------- */

const SlotContext = createContext(null);

/** Marker component: its children are rendered into a Schedule-X slot. */
export function ScheduleXSlot() {
  return null;
}

const getPath = (obj, path) =>
  String(path)
    .split(".")
    .reduce((acc, key) => (acc === null || acc === undefined ? acc : acc[key]), obj);

const DATE_FORMATS = new Set(["date", "datetime", "weekday", "weekday_short", "day", "month"]);

const formatSlotValue = (rawValue, format, ctx) => {
  if (rawValue === null || rawValue === undefined) return undefined;
  const locale = ctx?.locale || "en-US";
  const timezone = ctx?.timezone || "UTC";
  let value = rawValue;
  if (typeof value === "string" && PLAIN_DATE_RE.test(value) && DATE_FORMATS.has(format)) {
    value = Temporal.PlainDate.from(value);
  }
  if (value instanceof Date && DATE_FORMATS.has(format)) {
    value = Temporal.PlainDate.from({ year: value.getFullYear(), month: value.getMonth() + 1, day: value.getDate() });
  }
  if (typeof value === "number") {
    if (format === "weekday" || format === "weekday_short") {
      // JS day index (0 = Sunday); 2024-01-07 was a Sunday.
      return new Date(2024, 0, 7 + value).toLocaleDateString(locale, {
        weekday: format === "weekday" ? "long" : "short",
      });
    }
    if (format === "hour") {
      return new Date(2024, 0, 1, value).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
    }
  }
  if (Array.isArray(value) && format === "count") return String(value.length);
  const toZ = (v) => (isTemporal(v, "ZonedDateTime") ? v.withTimeZone(timezone) : v);
  const timeFmt = { hour: "2-digit", minute: "2-digit" };
  const dateFmt = { year: "numeric", month: "short", day: "numeric" };
  switch (format) {
    case "time":
      return isTemporal(value, "ZonedDateTime") ? toZ(value).toLocaleString(locale, timeFmt) : "";
    case "date":
      return isTemporal(value, "ZonedDateTime") || isTemporal(value, "PlainDate")
        ? toZ(value).toLocaleString(locale, dateFmt)
        : String(value);
    case "datetime":
      return isTemporal(value, "ZonedDateTime")
        ? toZ(value).toLocaleString(locale, { ...dateFmt, ...timeFmt })
        : formatSlotValue(value, "date", ctx);
    case "weekday":
    case "weekday_short":
      return isTemporal(value, "ZonedDateTime") || isTemporal(value, "PlainDate")
        ? toZ(value).toLocaleString(locale, { weekday: format === "weekday" ? "long" : "short" })
        : String(value);
    case "day":
      return isTemporal(value, "ZonedDateTime") || isTemporal(value, "PlainDate") ? String(toZ(value).day) : String(value);
    case "month":
      return isTemporal(value, "ZonedDateTime") || isTemporal(value, "PlainDate")
        ? toZ(value).toLocaleString(locale, { month: "short" })
        : String(value);
    case "json":
      return JSON.stringify(value);
    case "upper":
      return String(value).toUpperCase();
    default:
      if (Array.isArray(value)) return value.join(", ");
      if (isTemporal(value, "ZonedDateTime") || isTemporal(value, "PlainDate")) {
        return fromTemporal(value, timezone, "naive");
      }
      if (value instanceof Date) return value.toLocaleDateString(locale);
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
  }
};

const resolveSlotField = (ctx, name, format) => {
  if (!ctx) return undefined;
  const event = ctx.props?.calendarEvent;
  // Virtual fields computed from the event.
  if (event && name === "time_range") {
    if (isTemporal(event.start, "PlainDate")) {
      const s = formatSlotValue(event.start, "date", ctx);
      const e = formatSlotValue(event.end, "date", ctx);
      return s === e ? s : `${s} – ${e}`;
    }
    return `${formatSlotValue(event.start, "time", ctx)} – ${formatSlotValue(event.end, "time", ctx)}`;
  }
  if (event && name === "date_range") {
    const s = formatSlotValue(event.start, "date", ctx);
    const e = formatSlotValue(event.end, "date", ctx);
    return s === e ? s : `${s} – ${e}`;
  }
  if (event && name === "calendar_label") {
    const cal = ctx.calendars?.[event.calendarId];
    return cal?.label || event.calendarId;
  }
  let value;
  if (event && !String(name).includes(".") && name in event) value = event[name];
  else value = getPath(ctx.props, name);
  return formatSlotValue(value, format, ctx);
};

/** Renders a field of the slot props (e.g. the event title) inside a slot. */
export function ScheduleXField({ name = "title", format, fallback = "", tagName: As = "span", ...rest }) {
  const ctx = useContext(SlotContext);
  const text = resolveSlotField(ctx, name, format);
  return (
    <As data-sx-field={name} {...rest}>
      {text === undefined || text === null || text === "" ? fallback : text}
    </As>
  );
}

/** Renders its children only when a slot field is truthy (or falsy with `negate`). */
export function ScheduleXShow({ name, negate = false, children }) {
  const ctx = useContext(SlotContext);
  const event = ctx?.props?.calendarEvent;
  let value;
  if (name === "is_all_day") value = event ? isTemporal(event.start, "PlainDate") : false;
  else if (event && name in event) value = event[name];
  else value = getPath(ctx?.props, name);
  const visible = Array.isArray(value) ? value.length > 0 : Boolean(value);
  return visible !== negate ? <>{children}</> : null;
}

const CARD_CSS_ID = "rx-schedule-x-card-css";
const ensureCardCss = () => {
  if (typeof document === "undefined" || document.getElementById(CARD_CSS_ID)) return;
  const el = document.createElement("style");
  el.id = CARD_CSS_ID;
  // :where() keeps specificity at zero so Reflex style props always win.
  el.textContent = `
:where(.rx-sx-event-card) {
  height: 100%; width: 100%; box-sizing: border-box; overflow: hidden;
  background-color: var(--rx-sx-bg); color: var(--rx-sx-fg); border-inline-start: var(--rx-sx-border, none);
}`;
  document.head.appendChild(el);
};

/** A box styled with the colors of the event's calendar (like the built-in events). */
export function ScheduleXEventCard({ children, className = "", style = {}, variant = "container", ...rest }) {
  ensureCardCss();
  const ctx = useContext(SlotContext);
  const event = ctx?.props?.calendarEvent;
  const calendar = event?.calendarId ? ctx?.calendars?.[event.calendarId] : undefined;
  const color = calendar?.colorName || "primary";
  const vars =
    variant === "main"
      ? { "--rx-sx-bg": `var(--sx-color-${color})`, "--rx-sx-fg": `var(--sx-color-${color}-container)` }
      : {
          "--rx-sx-bg": `var(--sx-color-${color}-container)`,
          "--rx-sx-fg": `var(--sx-color-on-${color}-container)`,
          "--rx-sx-border": `4px solid var(--sx-color-${color})`,
        };
  return (
    <div className={`rx-sx-event-card ${className}`} style={{ ...vars, ...style }} data-calendar={color} {...rest}>
      {children}
    </div>
  );
}

/**
 * Makes its children clickable and reports the click to Reflex through the
 * calendar's `on_slot_action` trigger, together with the slot's event/date.
 */
export function ScheduleXAction({ action, children, closeModal = false, stopPropagation = true, ...rest }) {
  const ctx = useContext(SlotContext);
  const onClick = (e) => {
    if (stopPropagation) e.stopPropagation();
    ctx?.fireAction?.(action, closeModal);
  };
  return (
    <div className="rx-sx-action" style={{ display: "contents" }} onClick={onClick} {...rest}>
      {children}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*                                  Calendar                                  */
/* -------------------------------------------------------------------------- */

const collectSlots = (children) => {
  const slots = {};
  Children.forEach(children, (child) => {
    if (!isValidElement(child)) return;
    const name = child.props?.slotName;
    if (name) slots[name] = child.props.children;
  });
  return slots;
};

export function ScheduleXCalendar(props) {
  const {
    id,
    className,
    style,
    children,
    // structural config (re-creates the calendar when changed)
    views,
    defaultView,
    theme,
    translations,
    showWeekNumbers,
    isResponsive,
    skipAnimations,
    skipValidation,
    smallBreakpoint,
    monthAgendaOptions,
    datePicker,
    currentTimeIndicator,
    currentTimeFullWeekWidth,
    eventModal,
    initialScroll,
    recurrence,
    icalData,
    timezoneSelect,
    // live config (applied through plugins)
    events,
    backgroundEvents,
    view,
    selectedDate,
    locale,
    timezone,
    firstDayOfWeek,
    dayBoundaries,
    weekOptions,
    monthGridOptions,
    calendars,
    minDate,
    maxDate,
    isDark,
    scrollTo,
  } = props;

  const containerRef = useRef(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const appRef = useRef(null);
  const appliedRef = useRef({});
  const [portals, setPortals] = useState({});
  const [renderCount, setRenderCount] = useState(0);

  const slots = collectSlots(children);
  const slotNames = Object.keys(slots).sort();
  const tz = timezone || "UTC";

  const structuralKey = stableStringify({
    views,
    theme,
    translations,
    showWeekNumbers,
    isResponsive,
    skipAnimations,
    skipValidation,
    smallBreakpoint,
    monthAgendaOptions,
    datePicker,
    currentTimeIndicator,
    currentTimeFullWeekWidth,
    eventModal,
    initialScroll: Boolean(initialScroll),
    recurrence,
    icalData,
    timezoneSelect,
    slotNames,
  });

  // Create / re-create the calendar.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const p = propsRef.current;
    const zone = p.timezone || "UTC";
    const format = p.datetimeFormat || "naive";

    const fire = (name, ...args) => {
      const handler = propsRef.current[name];
      if (typeof handler === "function") handler(...args);
    };
    const ser = (v) => fromTemporal(v, propsRef.current.timezone || "UTC", propsRef.current.datetimeFormat || format);
    const serEvent = (e) => serializeEvent(e, propsRef.current.timezone || "UTC", propsRef.current.datetimeFormat || format);

    const eventsService = p.recurrence ? createRecurringEventsServicePlugin() : createEventsServicePlugin();
    const controls = createCalendarControlsPlugin();
    const plugins = [eventsService, controls];
    let recurrencePlugin, currentTime, modal, scroller, ical, tzSelect;
    if (p.recurrence) plugins.push((recurrencePlugin = createEventRecurrencePlugin()));
    if (p.currentTimeIndicator) {
      plugins.push((currentTime = createCurrentTimePlugin({ fullWeekWidth: Boolean(p.currentTimeFullWeekWidth) })));
    }
    if (p.eventModal) plugins.push((modal = createEventModalPlugin()));
    if (p.initialScroll) {
      plugins.push((scroller = createScrollControllerPlugin({ initialScroll: p.scrollTo || p.initialScroll })));
    }
    if (p.icalData) plugins.push((ical = createIcalendarPlugin({ data: p.icalData })));
    if (p.timezoneSelect) plugins.push((tzSelect = createTimezoneSelectPlugin()));

    // Bridge plugin: reports view changes back to Reflex.
    const bridge = {
      name: "reflexBridge",
      unsubscribe: null,
      onRender($app) {
        let first = true;
        this.unsubscribe = $app.calendarState.view.subscribe((viewName) => {
          if (first) {
            first = false;
            return;
          }
          fire("onViewChange", viewName);
        });
      },
      destroy() {
        this.unsubscribe?.();
      },
    };
    plugins.push(bridge);

    const builtViews = buildViews(p.views);
    const viewNames = builtViews.map((v) => v.name);
    const initialView = p.view && viewNames.includes(p.view) ? p.view : p.defaultView;

    const config = {
      views: builtViews,
      events: (p.events || []).map((e) => toSxEvent(e, zone)),
      backgroundEvents: (p.backgroundEvents || []).map((e) => toSxBackgroundEvent(e, zone)),
      timezone: zone,
      plugins: undefined,
      callbacks: {
        onEventClick: (event) => fire("onEventClick", serEvent(event)),
        onDoubleClickEvent: (event) => fire("onDoubleClickEvent", serEvent(event)),
        onRangeUpdate: (range) => fire("onRangeUpdate", { start: ser(range.start), end: ser(range.end) }),
        onSelectedDateUpdate: (date) => fire("onSelectedDateUpdate", ser(date)),
        onClickDate: (date) => fire("onClickDate", ser(date)),
        onDoubleClickDate: (date) => fire("onDoubleClickDate", ser(date)),
        onClickDateTime: (dt) => fire("onClickDateTime", ser(dt)),
        onDoubleClickDateTime: (dt) => fire("onDoubleClickDateTime", ser(dt)),
        onClickAgendaDate: (date) => fire("onClickAgendaDate", ser(date)),
        onDoubleClickAgendaDate: (date) => fire("onDoubleClickAgendaDate", ser(date)),
        onClickPlusEvents: (date) => fire("onClickPlusEvents", ser(date)),
        onScrollDayIntoView: (date) => fire("onScrollDayIntoView", ser(date)),
        onEventUpdate: (event) => fire("onEventUpdate", serEvent(event)),
        onRender: ($app) => {
          const range = $app.calendarState.range.value;
          fire("onCalendarRender", {
            view: $app.calendarState.view.value,
            date: ser($app.datePickerState.selectedDate.value),
            range: range ? { start: ser(range.start), end: ser(range.end) } : null,
          });
        },
      },
    };
    if (initialView && viewNames.includes(initialView)) config.defaultView = initialView;
    if (p.selectedDate) config.selectedDate = toPlainDate(p.selectedDate);
    if (p.locale) config.locale = p.locale;
    if (p.firstDayOfWeek) config.firstDayOfWeek = Number(p.firstDayOfWeek);
    if (p.dayBoundaries) config.dayBoundaries = camelizeKeys(p.dayBoundaries);
    if (p.weekOptions) config.weekOptions = normalizeWeekOptions(p.weekOptions);
    if (p.monthGridOptions) config.monthGridOptions = camelizeKeys(p.monthGridOptions);
    if (p.monthAgendaOptions) config.monthAgendaOptions = camelizeKeys(p.monthAgendaOptions);
    if (p.calendars) config.calendars = normalizeCalendars(p.calendars);
    if (p.minDate) config.minDate = toPlainDate(p.minDate);
    if (p.maxDate) config.maxDate = toPlainDate(p.maxDate);
    if (p.isDark !== undefined && p.isDark !== null) config.isDark = Boolean(p.isDark);
    if (p.theme && p.theme !== "default") config.theme = p.theme;
    if (p.showWeekNumbers !== undefined) config.showWeekNumbers = Boolean(p.showWeekNumbers);
    if (p.isResponsive !== undefined) config.isResponsive = Boolean(p.isResponsive);
    if (p.skipAnimations !== undefined) config.skipAnimations = Boolean(p.skipAnimations);
    if (p.skipValidation !== undefined) config.skipValidation = Boolean(p.skipValidation);
    if (p.datePicker) config.datePicker = camelizeKeys(p.datePicker);
    const mergedTranslations = buildTranslations(p.translations, p.timezoneSelect);
    if (mergedTranslations) config.translations = mergedTranslations;
    if (p.smallBreakpoint) {
      config.callbacks.isCalendarSmall = ($app) =>
        ($app.elements.calendarWrapper?.clientWidth ?? Infinity) < Number(propsRef.current.smallBreakpoint);
    }
    if (ical) {
      const userRangeUpdate = config.callbacks.onRangeUpdate;
      config.callbacks.onRangeUpdate = (range) => {
        safely("ical.between", () => ical.between(range.start, range.end));
        userRangeUpdate(range);
      };
    }

    let calendar;
    try {
      calendar = createCalendar(config, plugins);
    } catch (e) {
      console.error("[reflex-schedule-x] Could not create the calendar:", e);
      fire("onError", String(e?.message || e));
      return undefined;
    }

    for (const slotName of Object.keys(collectSlots(propsRef.current.children))) {
      calendar._setCustomComponentFn(slotName, (wrapperElement, slotProps) => {
        const ccid = wrapperElement?.dataset?.ccid || `${slotName}-${Math.random().toString(36).slice(2)}`;
        setPortals((prev) => {
          const next = {};
          for (const [key, value] of Object.entries(prev)) {
            // Drop detached wrappers and older portals that targeted the same element
            // (Schedule-X may re-use a DOM node with a new data-ccid).
            if (value.el.isConnected && key !== ccid && value.el !== wrapperElement) next[key] = value;
          }
          next[ccid] = { slot: slotName, props: slotProps, el: wrapperElement };
          return next;
        });
      });
    }
    calendar._setDestroyCustomComponentInstance?.((ccid) => {
      setPortals((prev) => {
        if (!(ccid in prev)) return prev;
        const next = { ...prev };
        delete next[ccid];
        return next;
      });
    });

    calendar.render(el);

    const app = {
      calendar,
      controls,
      eventsService,
      eventModal: modal,
      scrollController: scroller,
      currentTime,
      recurrence: recurrencePlugin,
      ical,
      timezoneSelect: tzSelect,
    };
    appRef.current = app;
    appliedRef.current = {
      events: stableStringify(p.events || []),
      backgroundEvents: stableStringify(p.backgroundEvents || []),
      view: initialView,
      selectedDate: p.selectedDate,
      locale: p.locale,
      timezone: p.timezone,
      firstDayOfWeek: p.firstDayOfWeek,
      dayBoundaries: stableStringify(p.dayBoundaries),
      weekOptions: stableStringify(p.weekOptions),
      monthGridOptions: stableStringify(p.monthGridOptions),
      calendars: stableStringify(p.calendars),
      minDate: p.minDate,
      maxDate: p.maxDate,
      isDark: p.isDark,
      scrollTo: p.scrollTo,
    };

    // Imperative API, reachable from rx.call_script via window.__reflexScheduleX[id].
    const api = {
      ...app,
      getView: () => controls.getView(),
      setView: (name) => controls.setView(name),
      getDate: () => fromTemporal(controls.getDate()),
      setDate: (date) => controls.setDate(toPlainDate(date)),
      getRange: () => {
        const r = controls.getRange();
        return r ? { start: ser(r.start), end: ser(r.end) } : null;
      },
      getEvents: () => eventsService.getAll().map(serEvent),
      getEvent: (eventId) => serEvent(eventsService.get(eventId)),
      addEvent: (event) => eventsService.add(toSxEvent(event, propsRef.current.timezone || "UTC")),
      updateEvent: (event) => eventsService.update(toSxEvent(event, propsRef.current.timezone || "UTC")),
      removeEvent: (eventId) => eventsService.remove(eventId),
      setEvents: (list) => eventsService.set((list || []).map((e) => toSxEvent(e, propsRef.current.timezone || "UTC"))),
      setTheme: (mode) => calendar.setTheme(mode),
      closeEventModal: () => modal?.close(),
      scrollTo: (time) => scroller?.scrollTo(time),
    };
    const instanceId = p.id;
    if (instanceId) registry()[instanceId] = api;

    setRenderCount((c) => c + 1);

    return () => {
      if (instanceId && registry()[instanceId] === api) delete registry()[instanceId];
      appRef.current = null;
      setPortals({});
      safely("destroy", () => calendar.destroy());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structuralKey]);

  // Apply live prop changes without re-creating the calendar.
  useEffect(() => {
    const app = appRef.current;
    if (!app) return;
    const applied = appliedRef.current;
    const { controls, eventsService, calendar } = app;

    if (timezone !== applied.timezone && timezone) {
      safely("setTimezone", () => controls.setTimezone(timezone));
      applied.timezone = timezone;
    }
    const eventsKey = stableStringify(events || []);
    if (eventsKey !== applied.events) {
      safely("events.set", () => eventsService.set((events || []).map((e) => toSxEvent(e, tz))));
      applied.events = eventsKey;
    }
    const bgKey = stableStringify(backgroundEvents || []);
    if (bgKey !== applied.backgroundEvents) {
      safely("setBackgroundEvents", () =>
        eventsService.setBackgroundEvents((backgroundEvents || []).map((e) => toSxBackgroundEvent(e, tz)))
      );
      applied.backgroundEvents = bgKey;
    }
    if (view && view !== applied.view) {
      if (controls.getView() !== view) safely("setView", () => controls.setView(view));
      applied.view = view;
    }
    if (selectedDate && selectedDate !== applied.selectedDate) {
      const current = safely("getDate", () => controls.getDate()?.toString());
      if (current !== String(selectedDate).slice(0, 10)) {
        safely("setDate", () => controls.setDate(toPlainDate(selectedDate)));
      }
      applied.selectedDate = selectedDate;
    }
    if (locale && locale !== applied.locale) {
      safely("setLocale", () => controls.setLocale(locale));
      applied.locale = locale;
    }
    if (firstDayOfWeek && firstDayOfWeek !== applied.firstDayOfWeek) {
      safely("setFirstDayOfWeek", () => controls.setFirstDayOfWeek(Number(firstDayOfWeek)));
      applied.firstDayOfWeek = firstDayOfWeek;
    }
    const dbKey = stableStringify(dayBoundaries);
    if (dayBoundaries && dbKey !== applied.dayBoundaries) {
      safely("setDayBoundaries", () => controls.setDayBoundaries(camelizeKeys(dayBoundaries)));
      applied.dayBoundaries = dbKey;
    }
    const woKey = stableStringify(weekOptions);
    if (weekOptions && woKey !== applied.weekOptions) {
      safely("setWeekOptions", () => controls.setWeekOptions(normalizeWeekOptions(weekOptions)));
      applied.weekOptions = woKey;
    }
    const mgKey = stableStringify(monthGridOptions);
    if (monthGridOptions && mgKey !== applied.monthGridOptions) {
      safely("setMonthGridOptions", () => controls.setMonthGridOptions(camelizeKeys(monthGridOptions)));
      applied.monthGridOptions = mgKey;
    }
    const calKey = stableStringify(calendars);
    if (calendars && calKey !== applied.calendars) {
      safely("setCalendars", () => controls.setCalendars(normalizeCalendars(calendars)));
      applied.calendars = calKey;
    }
    if (minDate !== applied.minDate) {
      safely("setMinDate", () => controls.setMinDate(toPlainDate(minDate)));
      applied.minDate = minDate;
    }
    if (maxDate !== applied.maxDate) {
      safely("setMaxDate", () => controls.setMaxDate(toPlainDate(maxDate)));
      applied.maxDate = maxDate;
    }
    if (isDark !== undefined && isDark !== null && Boolean(isDark) !== Boolean(applied.isDark)) {
      safely("setTheme", () => calendar.setTheme(isDark ? "dark" : "light"));
      applied.isDark = isDark;
    }
    if (scrollTo && scrollTo !== applied.scrollTo && app.scrollController) {
      try {
        app.scrollController.scrollTo(scrollTo);
        applied.scrollTo = scrollTo;
      } catch (e) {
        // The plugin is not initialized until the first render; retry on the next update.
      }
    }
  });

  const slotContextBase = useMemo(
    () => ({ locale: locale || "en-US", timezone: tz, calendars: normalizeCalendars(calendars) || {} }),
    [locale, tz, stableStringify(calendars)]
  );

  return (
    <>
      <div
        ref={containerRef}
        id={id}
        className={`sx-react-calendar-wrapper rx-schedule-x ${className || ""}`}
        style={style}
        data-render-count={renderCount}
      />
      {Object.entries(portals).map(([ccid, portal]) => {
        const template = slots[portal.slot];
        if (template === undefined || !portal.el) return null;
        if (portal.el.dataset?.ccid && portal.el.dataset.ccid !== ccid) return null;
        const value = {
          ...slotContextBase,
          slot: portal.slot,
          props: portal.props,
          fireAction: (action, closeModal) => {
            const current = propsRef.current;
            const zone = current.timezone || "UTC";
            const fmt = current.datetimeFormat || "naive";
            const payload = { action, slot: portal.slot, event: null, date: null };
            if (portal.props?.calendarEvent) payload.event = serializeEvent(portal.props.calendarEvent, zone, fmt);
            if (portal.props?.jsDate instanceof Date) {
              const d = portal.props.jsDate;
              payload.date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
            } else if (portal.props?.date !== undefined) {
              payload.date = fromTemporal(portal.props.date, zone, fmt);
            }
            if (typeof current.onSlotAction === "function") current.onSlotAction(payload);
            if (closeModal) appRef.current?.eventModal?.close();
          },
        };
        return createPortal(<SlotContext.Provider value={value}>{template}</SlotContext.Provider>, portal.el, ccid);
      })}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/*                                 Date picker                                */
/* -------------------------------------------------------------------------- */

export function ScheduleXDatePicker(props) {
  const {
    id,
    className,
    style,
    value,
    locale,
    firstDayOfWeek,
    min,
    max,
    placement,
    dark,
    fullWidth,
    label,
    name,
    disabled,
    hasPlaceholder,
    timezone,
  } = props;
  const ref = useRef(null);
  const appRef = useRef(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const lastEmittedRef = useRef(undefined);
  const [externalChanges, setExternalChanges] = useState(0);

  const key = stableStringify({
    locale, firstDayOfWeek, min, max, placement, dark, fullWidth, label, name, hasPlaceholder, timezone, externalChanges,
  });

  useEffect(() => {
    if (!ref.current) return undefined;
    const p = propsRef.current;
    const config = {
      listeners: {
        onChange: (date) => {
          const value = date ? date.toString() : "";
          lastEmittedRef.current = value;
          const handler = propsRef.current.onChange;
          if (typeof handler === "function") handler(value);
        },
      },
      style: { dark: Boolean(p.dark), fullWidth: Boolean(p.fullWidth) },
    };
    if (p.value) config.selectedDate = toPlainDate(p.value);
    if (p.locale) config.locale = p.locale;
    if (p.firstDayOfWeek) config.firstDayOfWeek = Number(p.firstDayOfWeek);
    if (p.min) config.min = toPlainDate(p.min);
    if (p.max) config.max = toPlainDate(p.max);
    if (p.placement) config.placement = p.placement;
    if (p.label) config.label = p.label;
    if (p.name) config.name = p.name;
    if (p.disabled !== undefined) config.disabled = Boolean(p.disabled);
    if (p.hasPlaceholder !== undefined) config.hasPlaceholder = Boolean(p.hasPlaceholder);
    if (p.timezone) config.timezone = p.timezone;
    let picker;
    try {
      picker = createDatePicker(config);
      picker.render(ref.current);
    } catch (e) {
      console.error("[reflex-schedule-x] Could not create the date picker:", e);
      return undefined;
    }
    appRef.current = picker;
    const node = ref.current;
    return () => {
      appRef.current = null;
      safely("date picker unmount", () => preactRender(null, node));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    const picker = appRef.current;
    if (!picker) return;
    const wanted = value ? String(value).slice(0, 10) : undefined;
    if (wanted && picker.value?.toString() !== wanted && wanted !== lastEmittedRef.current) {
      // Value changed from Python: re-create so the popup also shows the new month.
      lastEmittedRef.current = wanted;
      setExternalChanges((n) => n + 1);
      return;
    }
    if (disabled !== undefined && Boolean(picker.disabled) !== Boolean(disabled)) {
      safely("date picker disabled", () => {
        picker.disabled = Boolean(disabled);
      });
    }
  });

  return <div ref={ref} id={id} className={`rx-schedule-x-date-picker ${className || ""}`} style={style} />;
}

/* -------------------------------------------------------------------------- */
/*                                 Time picker                                */
/* -------------------------------------------------------------------------- */

export function ScheduleXTimePicker(props) {
  const { id, className, style, value, locale, dark, placement, label, name, is12Hour } = props;
  const ref = useRef(null);
  const appRef = useRef(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  const key = stableStringify({ locale, dark, placement, label, name, is12Hour });

  useEffect(() => {
    if (!ref.current) return undefined;
    const p = propsRef.current;
    const config = {
      dark: Boolean(p.dark),
      initialValue: p.value || "00:00",
      onChange: (time) => {
        const handler = propsRef.current.onChange;
        if (typeof handler === "function") handler(time);
      },
    };
    if (p.placement) config.placement = p.placement;
    if (p.label) config.label = p.label;
    if (p.name) config.name = p.name;
    if (p.is12Hour !== undefined) config.is12Hour = Boolean(p.is12Hour);
    let picker;
    try {
      const translateFn = translate(signal(p.locale || "en-US"), signal(baseTranslations));
      picker = createTimePicker(config, translateFn);
      picker.render(ref.current);
    } catch (e) {
      console.error("[reflex-schedule-x] Could not create the time picker:", e);
      return undefined;
    }
    appRef.current = picker;
    const node = ref.current;
    return () => {
      appRef.current = null;
      safely("time picker unmount", () => preactRender(null, node));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    const picker = appRef.current;
    if (picker && value && picker.value !== value) {
      safely("time picker value", () => {
        picker.value = value;
      });
    }
  });

  return <div ref={ref} id={id} className={`rx-schedule-x-time-picker ${className || ""}`} style={style} />;
}
