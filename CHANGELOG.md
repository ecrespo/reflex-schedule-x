# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Release workflow: PyPI Trusted Publishing and GitHub release on `v*` tags.

## [0.1.0] - 2026-09-17

### Added

- `schedule_x` calendar component wrapping `@schedule-x/*` 4.8.0: day, week, month grid, month agenda, week agenda
  and list views.
- Live props applied through the calendar-controls and events-service plugins.
- Plugins: current time, event modal, scroll controller, event recurrence, iCalendar and timezone select.
- Custom component slots (`schedule_x_slot`, `schedule_x_field`, `schedule_x_show`, `schedule_x_event_card`,
  `schedule_x_action`).
- `ScheduleXAPI` imperative API, date and time pickers, and Python helpers for events, calendars and dates.
- Multi-page demo app, test suite, and quality, security and release workflows.

[Unreleased]: https://github.com/ecrespo/reflex-schedule-x/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ecrespo/reflex-schedule-x/releases/tag/v0.1.0
