"""reflex-schedule-x demo app: a tour of the Schedule-X calendar in Reflex."""

import reflex as rx

from .pages import (  # noqa: F401  (registers pages)
    api,
    custom_components,
    events,
    i18n,
    pickers,
    playground,
    recurrence,
)

app = rx.App()
