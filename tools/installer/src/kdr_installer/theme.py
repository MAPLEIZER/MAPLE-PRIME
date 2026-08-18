from rich.theme import Theme

THEME_ROLES = {
    "kdr.title",
    "kdr.accent",
    "kdr.success",
    "kdr.warning",
    "kdr.danger",
    "kdr.muted",
}

KDR_THEME = Theme(
    {
        "kdr.title": "bold bright_cyan",
        "kdr.accent": "bold cyan",
        "kdr.success": "bold green",
        "kdr.warning": "bold yellow",
        "kdr.danger": "bold red",
        "kdr.muted": "dim white",
    }
)
