"""Local preview: show the effective state for one workspace without deploying.

Usage:
    python scripts/plan.py --workspace analytics-prod
    python scripts/plan.py --workspace analytics-prod --print-instructions
"""
from __future__ import annotations

import argparse
import sys

from lib.config import list_workspaces, load_workspace
from lib.inheritance import compose


def main():
    parser = argparse.ArgumentParser(description="Preview a workspace's effective state.")
    parser.add_argument("--workspace", "-w", required=True, help="Workspace name.")
    parser.add_argument(
        "--print-instructions", action="store_true",
        help="Dump the concatenated instructions text (otherwise just summary).",
    )
    args = parser.parse_args()

    if args.workspace not in list_workspaces():
        print(
            f"unknown workspace '{args.workspace}'. Available: {list_workspaces()}",
            file=sys.stderr,
        )
        return 2

    cfg = load_workspace(args.workspace)
    state = compose(cfg)

    print(f"Workspace: {cfg.name}")
    print(f"  host:        {cfg.host}")
    print(f"  scope:       {cfg.scope}")
    print(f"  environment: {cfg.environment}")
    print(f"  layers:      {' → '.join(cfg.layers)} → <workspace>")
    print(f"  auth mode:   {cfg.auth.get('mode', 'account_sp')}")

    print(f"\nInstructions ({len(state.instructions_files)} files):")
    for p in state.instructions_files:
        print(f"  - {p.relative_to(cfg.path.parents[1])}")

    print(f"\nSkills ({len(state.skills)}):")
    for name in sorted(state.skills):
        print(f"  - {name}  ({state.skills[name].relative_to(cfg.path.parents[1])})")

    if state.warnings:
        print("\nWarnings:")
        for w in state.warnings:
            print(f"  ! {w}")

    if args.print_instructions:
        from compile import _render_instructions
        print("\n" + "=" * 60)
        print("COMPILED INSTRUCTIONS")
        print("=" * 60)
        print(_render_instructions(state))

    return 0


if __name__ == "__main__":
    sys.exit(main())
