"""Shared layout: sidebar navigation, page header and small UI helpers."""

from __future__ import annotations

import reflex as rx

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("Playground", "/", "sliders-horizontal"),
    ("Events & callbacks", "/events", "calendar-plus"),
    ("Custom components", "/custom-components", "puzzle"),
    ("Recurrence & iCal", "/recurrence", "repeat"),
    ("Language & timezones", "/i18n", "languages"),
    ("Imperative API & list", "/api", "terminal"),
    ("Date & time pickers", "/pickers", "clock"),
]


def nav_link(label: str, href: str, icon: str) -> rx.Component:
    """A sidebar link that highlights the active route."""
    active = rx.State.router.page.path == href
    return rx.link(
        rx.hstack(rx.icon(icon, size=16), rx.text(label, size="2"), spacing="2", align="center"),
        href=href,
        underline="none",
        padding_x="0.75rem",
        padding_y="0.5rem",
        border_radius="var(--radius-2)",
        width="100%",
        color=rx.cond(active, rx.color("accent", 11), rx.color("gray", 11)),
        background=rx.cond(active, rx.color("accent", 3), "transparent"),
        _hover={"background": rx.color("gray", 3)},
    )


def sidebar() -> rx.Component:
    """Navigation sidebar."""
    return rx.vstack(
        rx.hstack(
            rx.icon("calendar-days", size=26, color=rx.color("accent", 10)),
            rx.vstack(
                rx.heading("reflex-schedule-x", size="3", white_space="nowrap"),
                rx.text("Schedule-X for Reflex", size="1", color_scheme="gray"),
                spacing="0",
            ),
            align="center",
            spacing="2",
            padding_bottom="1rem",
        ),
        *[nav_link(*item) for item in NAV_ITEMS],
        rx.spacer(),
        rx.hstack(
            rx.color_mode.switch(),
            rx.text("Dark mode", size="2", color_scheme="gray"),
            align="center",
        ),
        rx.link(
            rx.hstack(rx.icon("external-link", size=14), rx.text("schedule-x.dev docs", size="1")),
            href="https://schedule-x.dev/docs/calendar",
            is_external=True,
        ),
        width="250px",
        min_width="250px",
        height="100vh",
        position="sticky",
        top="0",
        padding="1.25rem",
        border_right=f"1px solid {rx.color('gray', 5)}",
        spacing="1",
        display=["none", "none", "flex"],
    )


def page(title: str, description: str, *children: rx.Component) -> rx.Component:
    """Page wrapper with heading and description."""
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.heading(title, size="7"),
            rx.text(description, color_scheme="gray", size="3"),
            *children,
            width="100%",
            max_width="1500px",
            padding=["1rem", "1.5rem", "2rem"],
            spacing="4",
            min_width="0",
        ),
        align="start",
        spacing="0",
        width="100%",
    )


def card(*children: rx.Component, **props) -> rx.Component:
    """A padded surface."""
    return rx.card(*children, width="100%", **props)


def field_label(text: str) -> rx.Component:
    """Small label above a control."""
    return rx.text(text, size="1", weight="medium", color_scheme="gray")


def labeled(text: str, control: rx.Component, **props) -> rx.Component:
    """A control with a label."""
    return rx.vstack(field_label(text), control, spacing="1", min_width="150px", **props)


def code(source: str) -> rx.Component:
    """Collapsible code sample."""
    return rx.accordion.root(
        rx.accordion.item(
            header=rx.hstack(rx.icon("code", size=14), rx.text("Show code", size="2")),
            content=rx.code_block(source.strip(), language="python", show_line_numbers=False, width="100%"),
            value="code",
        ),
        collapsible=True,
        type="single",
        variant="ghost",
        width="100%",
    )


def log_panel(entries: rx.Var[list[str]], on_clear: rx.EventHandler | None = None) -> rx.Component:
    """A list of callback log lines."""
    return card(
        rx.hstack(
            rx.icon("activity", size=16),
            rx.text("Callback log", weight="bold", size="2"),
            rx.spacer(),
            rx.button("Clear", size="1", variant="soft", on_click=on_clear) if on_clear is not None else rx.fragment(),
            align="center",
            width="100%",
        ),
        rx.scroll_area(
            rx.vstack(
                rx.foreach(
                    entries,
                    lambda line: rx.text(line, size="1", font_family="monospace", white_space="pre-wrap"),
                ),
                spacing="1",
            ),
            type="auto",
            scrollbars="vertical",
            height="220px",
            margin_top="0.5rem",
        ),
    )
