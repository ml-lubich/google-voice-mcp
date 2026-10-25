"""Machine-readable command schema for agent integrations."""

from __future__ import annotations

import typer

from google_voice_mcp import __version__


def build_schema(app: typer.Typer) -> dict[str, object]:
    """Describe the registered CLI leaves without invoking their callbacks."""
    root = typer.main.get_command(app)
    commands: list[dict[str, object]] = []
    global_params = [
        {
            "name": param.name,
            "type": getattr(param.type, "name", str(param.type)),
            "required": bool(param.required),
            "flags": list(getattr(param, "opts", [])),
        }
        for param in getattr(root, "params", [])
        if param.name not in {"help", "install_completion", "show_completion"}
    ]

    def visit(command: object, prefix: str) -> None:
        subcommands = getattr(command, "commands", None)
        if subcommands:
            for name, child in subcommands.items():
                visit(child, f"{prefix} {name}".strip())
            return

        params: list[dict[str, object]] = []
        for param in getattr(command, "params", []):
            params.append(
                {
                    "name": param.name,
                    "type": getattr(param.type, "name", str(param.type)),
                    "required": bool(param.required),
                    "flags": list(getattr(param, "opts", [])),
                }
            )
        commands.append(
            {
                "name": prefix,
                "help": (getattr(command, "help", None) or "").strip(),
                "params": params,
            }
        )

    visit(root, "")
    return {
        "version": __version__,
        "tool": "gvoice",
        "mcp": "google-voice-mcp",
        "help": "gvoice --help | gvoice <command> --help | google-voice-mcp serve",
        "global_params": global_params,
        "commands": commands,
    }
