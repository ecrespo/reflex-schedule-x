# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-25

### Changed

- Requires Reflex 0.10.0 or later (`reflex>=0.10.0`); `.pyi` stubs regenerated with the Reflex 0.10 stub generator.
- Requires Python 3.11 or later; Python 3.10 support dropped, matching Reflex 0.10.
- Build tooling: Reflex 0.10 removed `reflex component build`, so stubs are now generated with
  `python -m reflex_base.utils.pyi_generator` and the distribution is built with `uv build`.
- CI: workflows run JavaScript actions on Node 24 and the demo bundle builds with Node 24.
- Demo app lockfiles refreshed for Reflex 0.10.

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

[Unreleased]: https://github.com/ecrespo/reflex-schedule-x/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ecrespo/reflex-schedule-x/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ecrespo/reflex-schedule-x/releases/tag/v0.1.0
