"""Fail-fast checks before merge/deploy.

Checks:
  - Every SKILL.md has frontmatter with `name` matching the folder name and a non-empty `description`.
  - Every workspace's compiled instructions fit under the 20K cap (delegates to compile.py).
  - `inheritance.skills.<layer>` allow-lists reference real skill names in that layer.
  - No two workspaces share the same `host`.
  - Paths inside skill folders are safe (no `..`, no absolute paths).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from lib.config import (
    REPO_ROOT,
    layer_path,
    list_workspaces,
    load_defaults,
    load_workspace,
)
from lib.inheritance import _find_skill_dirs

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\s*\n", re.DOTALL)


def _read_frontmatter(skill_md: Path) -> dict | None:
    text = skill_md.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}


def validate_skill(skill_md: Path, errors: list[str]) -> None:
    folder_name = skill_md.parent.name
    fm = _read_frontmatter(skill_md)
    if fm is None:
        errors.append(f"{skill_md.relative_to(REPO_ROOT)}: missing YAML frontmatter")
        return
    name = fm.get("name")
    if name != folder_name:
        errors.append(
            f"{skill_md.relative_to(REPO_ROOT)}: frontmatter name '{name}' "
            f"does not match folder '{folder_name}'"
        )
    desc = fm.get("description", "").strip()
    if not desc:
        errors.append(f"{skill_md.relative_to(REPO_ROOT)}: empty/missing description")
    elif len(desc) < 30:
        errors.append(
            f"{skill_md.relative_to(REPO_ROOT)}: description is only {len(desc)} chars — "
            f"Genie matches on this, be specific about triggers"
        )


def validate_skill_paths(skill_dir: Path, errors: list[str]) -> None:
    """Guard against symlinks that escape the skill folder."""
    for p in skill_dir.rglob("*"):
        if p.is_symlink():
            target = p.resolve()
            try:
                target.relative_to(skill_dir.resolve())
            except ValueError:
                errors.append(
                    f"{p.relative_to(REPO_ROOT)}: symlink escapes skill folder"
                )


def validate_layers(defaults: dict, errors: list[str]) -> set[str]:
    """Return the set of layer names referenced anywhere in defaults or workspaces."""
    referenced = set(
        defaults.get("inheritance", {}).get("layers", ["enterprise"])
    )
    for name in list_workspaces():
        cfg = load_workspace(name)
        referenced.update(cfg.layers)
    for layer in referenced:
        if not layer_path(layer).exists():
            errors.append(
                f"layer '{layer}' is referenced but {layer_path(layer)} does not exist"
            )
    return referenced


def validate_workspace_allowlists(errors: list[str]) -> None:
    for name in list_workspaces():
        cfg = load_workspace(name)
        for layer in cfg.layers:
            allow = cfg.skill_allowlist(layer)
            if allow == "all":
                continue
            if not isinstance(allow, list):
                errors.append(
                    f"workspace {name}: inheritance.skills.{layer} must be a list or 'all'"
                )
                continue
            layer_skills = _find_skill_dirs(layer_path(layer) / "skills")
            for skill in allow:
                if skill not in layer_skills:
                    errors.append(
                        f"workspace {name}: inheritance.skills.{layer} references "
                        f"'{skill}' which does not exist in layer '{layer}'"
                    )


def validate_host_uniqueness(errors: list[str]) -> None:
    seen = defaultdict(list)
    for name in list_workspaces():
        cfg = load_workspace(name)
        seen[cfg.host].append(name)
    for host, names in seen.items():
        if len(names) > 1:
            errors.append(
                f"host {host} is used by multiple workspaces: {', '.join(names)}"
            )


def main():
    parser = argparse.ArgumentParser(description="Validate skills repo + workspace configs.")
    parser.add_argument(
        "--skip-compile", action="store_true",
        help="Skip the 20K-cap check (faster, but caller must run compile.py separately).",
    )
    args = parser.parse_args()

    errors: list[str] = []
    defaults = load_defaults()

    # Validate every skill we can find on disk.
    for skill_md in REPO_ROOT.rglob("SKILL.md"):
        rel = skill_md.relative_to(REPO_ROOT)
        if "build/" in str(rel):
            continue
        # Skip templates / drafts (any path component starting with `_`).
        if any(part.startswith("_") for part in rel.parts):
            continue
        validate_skill(skill_md, errors)
        validate_skill_paths(skill_md.parent, errors)

    validate_layers(defaults, errors)
    validate_workspace_allowlists(errors)
    validate_host_uniqueness(errors)

    # 20K cap check: compile each workspace; compile.py raises on overflow.
    if not args.skip_compile:
        from compile import compile_workspace
        for name in list_workspaces():
            try:
                compile_workspace(name, verbose=False)
            except SystemExit as e:
                errors.append(str(e))

    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("validation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
