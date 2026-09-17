import reflex as rx

config = rx.Config(
    app_name="schedule_x_demo",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.RadixThemesPlugin(theme=rx.theme(accent_color="violet", radius="medium")),
    ],
)
