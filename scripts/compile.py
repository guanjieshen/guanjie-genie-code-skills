"""Compile per-workspace artifacts into build/<workspace>/.

Outputs:
  build/<workspace>/.assistant_workspace_instructions.md   (concatenated)
  build/<workspace>/skills/<skill>/...                     (one folder per skill)
  build/<workspace>/manifest.json                          (what we plan to deploy)

Fails loudly if the compiled instructions exceed the 20,000-char cap.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from lib.config import WorkspaceConfig, list_workspaces, load_workspace, REPO_ROOT
from lib.inheritance import EffectiveState, compose

INSTRUCTIONS_CAP = 20_000   # Databricks Genie Code workspace-instructions limit
BUILD_DIR = REPO_ROOT / "build"


def compile_workspace(workspace_name: str, *, verbose: bool = True) -> dict:
    workspace = load_workspace(workspace_name)
    state = compose(workspace)

    out_dir = BUILD_DIR / workspace.name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "skills").mkdir(parents=True, exist_ok=True)

    instructions_text = _render_instructions(state)
    instructions_path = out_dir / ".assistant_workspace_instructions.md"
    instructions_path.write_text(instructions_text)

    if len(instructions_text) > INSTRUCTIONS_CAP:
        offender = _identify_offender(state, INSTRUCTIONS_CAP)
        raise SystemExit(
            f"[{workspace.name}] compiled instructions are "
            f"{len(instructions_text):,} chars; cap is {INSTRUCTIONS_CAP:,}. "
            f"Largest contributor: {offender}"
        )

    skill_paths: dict[str, str] = {}
    for skill_name, src in state.skills.items():
        dst = out_dir / "skills" / skill_name
        shutil.copytree(src, dst)
        skill_paths[skill_name] = str(dst.relative_to(out_dir))

    manifest = {
        "workspace": workspace.name,
        "host": workspace.host,
        "scope": workspace.scope,
        "instructions_chars": len(instructions_text),
        "instructions_cap": INSTRUCTIONS_CAP,
        "skills": sorted(skill_paths.keys()),
        "warnings": state.warnings,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    if verbose:
        pct = 100 * len(instructions_text) / INSTRUCTIONS_CAP
        print(
            f"[{workspace.name}] OK — {len(state.skills)} skills, "
            f"instructions {len(instructions_text):,}/{INSTRUCTIONS_CAP:,} chars "
            f"({pct:.1f}%)"
        )
        for w in state.warnings:
            print(f"  warn: {w}")

    return manifest


def _render_instructions(state: EffectiveState) -> str:
    """Concatenate instruction files with source-tracking comments."""
    if not state.instructions_files:
        return ""
    parts = []
    for path in state.instructions_files:
        rel = path.relative_to(REPO_ROOT)
        parts.append(f"<!-- source: {rel} -->")
        parts.append(path.read_text().rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _identify_offender(state: EffectiveState, cap: int) -> str:
    running = 0
    for path in state.instructions_files:
        size = len(path.read_text())
        if running + size > cap:
            rel = path.relative_to(REPO_ROOT)
            return f"{rel} (this file alone is {size:,} chars; running total was {running:,})"
        running += size
    return "<unknown>"


def main():
    parser = argparse.ArgumentParser(description="Compile per-workspace build artifacts.")
    parser.add_argument(
        "--workspace", "-w",
        help="Workspace name (under workspaces/). Omit to compile all.",
    )
    args = parser.parse_args()

    if args.workspace:
        targets = [args.workspace]
    else:
        targets = list_workspaces()
        if not targets:
            print("no workspaces found under workspaces/", file=sys.stderr)
            return 0

    for name in targets:
        compile_workspace(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
