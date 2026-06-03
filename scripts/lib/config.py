"""Load and merge defaults.yaml + per-workspace config.yaml.

A workspace's effective config is `defaults.yaml` deep-merged with the
workspace's own `config.yaml`. Workspace values win.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = REPO_ROOT / "defaults.yaml"
WORKSPACES_DIR = REPO_ROOT / "workspaces"


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in overlay.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class WorkspaceConfig:
    name: str
    host: str
    workspace_id: int | None
    scope: str                         # "workspace" or "user"
    environment: str
    auth: dict
    inheritance: dict
    path: Path = field(repr=False)     # workspaces/<name>/

    @property
    def layers(self) -> list[str]:
        return list(self.inheritance.get("layers", ["enterprise"]))

    @property
    def instructions_enabled(self) -> bool:
        return bool(
            self.inheritance.get("instructions", {}).get("enabled", True)
        )

    def skill_allowlist(self, layer: str) -> list[str] | str:
        """Returns "all" or a list of skill names allowed from `layer`."""
        return self.inheritance.get("skills", {}).get(layer, "all")


def load_defaults() -> dict:
    if not DEFAULTS_PATH.exists():
        return {}
    return yaml.safe_load(DEFAULTS_PATH.read_text()) or {}


def load_workspace(name: str) -> WorkspaceConfig:
    wpath = WORKSPACES_DIR / name
    cfg_path = wpath / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"No config.yaml at {cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text()) or {}
    merged = _deep_merge(load_defaults(), raw)

    return WorkspaceConfig(
        name=merged.get("name", name),
        host=merged["host"],
        workspace_id=merged.get("workspace_id"),
        scope=merged.get("scope", "workspace"),
        environment=merged.get("environment", "dev"),
        auth=merged.get("auth", {}),
        inheritance=merged.get("inheritance", {}),
        path=wpath,
    )


def list_workspaces() -> list[str]:
    """Return names of all workspaces (folders under workspaces/ with a config.yaml).

    Skips folders starting with `_` so `workspaces/_example/` is treated as a template.
    """
    if not WORKSPACES_DIR.exists():
        return []
    return sorted(
        p.name
        for p in WORKSPACES_DIR.iterdir()
        if p.is_dir()
        and not p.name.startswith("_")
        and (p / "config.yaml").exists()
    )


def layer_path(layer: str) -> Path:
    """Resolve a layer name to its directory on disk.

    `enterprise` → REPO_ROOT/enterprise
    `profiles/hipaa` → REPO_ROOT/profiles/hipaa  (forward-compat: works the day you create it)
    """
    return REPO_ROOT / layer
