"""Deploy a compiled workspace artifact to its Databricks workspace.

Usage:
    python scripts/deploy.py --workspace analytics-prod [--dry-run] [--sha <git-sha>]

Assumes `scripts/compile.py --workspace <name>` has already been run, producing
`build/<name>/`. The deploy step:

  1. Loads the prior managed-by manifest from the workspace (if any).
  2. Diffs build files against the manifest's stored content hashes — uploads only
     files whose content actually changed.
  3. Deletes skills that were in the prior manifest but are absent from build/.
     (Skills outside the manifest are user-owned — we leave them alone.)
  4. Writes a new manifest with the current git SHA, skill list, and file hashes.

Idempotent: re-running with no changes performs zero uploads beyond the manifest.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lib.auth import get_client
from lib.config import REPO_ROOT, load_workspace
from lib.workspace_io import (
    DeployedManifest,
    delete_path,
    instructions_path,
    manifest_path,
    read_manifest,
    sha256_bytes,
    skills_root,
    upload_file,
    write_manifest,
)

BUILD_DIR = REPO_ROOT / "build"
REPO_NAME = os.environ.get("REPO_NAME", REPO_ROOT.name)


def _walk_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def deploy_workspace(workspace_name: str, *, sha: str | None, dry_run: bool) -> int:
    build_dir = BUILD_DIR / workspace_name
    if not build_dir.exists():
        print(
            f"no build artifact at {build_dir} — run scripts/compile.py first",
            file=sys.stderr,
        )
        return 2

    config = load_workspace(workspace_name)
    client = get_client(config)

    inst_remote = instructions_path(client, config)
    skills_remote_root = skills_root(client, config)
    mfst_remote = manifest_path(client, config, REPO_NAME)

    prior = read_manifest(client, mfst_remote)
    new_manifest = DeployedManifest(sha=sha, skills=[], file_hashes={})

    print(f"[{workspace_name}] deploying to {config.host} (scope={config.scope})")
    print(f"  prior deploy SHA: {prior.sha or '<none>'}")

    # 1. Instructions
    inst_local = build_dir / ".assistant_workspace_instructions.md"
    if inst_local.exists():
        content = inst_local.read_bytes()
        h = sha256_bytes(content)
        if prior.file_hashes.get(inst_remote) == h:
            print(f"  instructions: unchanged ({len(content)} bytes)")
        else:
            print(f"  instructions: uploading ({len(content)} bytes)")
            upload_file(client, inst_remote, content, dry_run=dry_run)
        new_manifest.file_hashes[inst_remote] = h

    # 2. Skills — upload changed files, leave unchanged ones alone.
    skills_local = build_dir / "skills"
    deployed_skills: list[str] = []
    if skills_local.exists():
        for skill_dir in sorted(p for p in skills_local.iterdir() if p.is_dir()):
            deployed_skills.append(skill_dir.name)
            for local_file in _walk_files(skill_dir):
                rel = local_file.relative_to(skills_local)
                remote = f"{skills_remote_root}/{rel.as_posix()}"
                content = local_file.read_bytes()
                h = sha256_bytes(content)
                if prior.file_hashes.get(remote) == h:
                    continue
                print(f"  upload: {remote}")
                upload_file(client, remote, content, dry_run=dry_run)
                new_manifest.file_hashes[remote] = h
            # Preserve hashes for files that didn't change.
            for remote, h in prior.file_hashes.items():
                if remote.startswith(f"{skills_remote_root}/{skill_dir.name}/"):
                    new_manifest.file_hashes.setdefault(remote, h)

    new_manifest.skills = deployed_skills

    # 3. Delete skills removed from the repo since last deploy.
    removed = set(prior.skills or []) - set(deployed_skills)
    for skill_name in sorted(removed):
        target = f"{skills_remote_root}/{skill_name}"
        print(f"  remove: {target} (no longer in repo)")
        delete_path(client, target, dry_run=dry_run)
        # Drop its file_hashes entries.
        new_manifest.file_hashes = {
            k: v
            for k, v in new_manifest.file_hashes.items()
            if not k.startswith(f"{target}/")
        }

    # Detect orphans: files in prior.file_hashes under a still-present skill
    # whose local counterpart was removed (skill exists but a file inside was deleted).
    for remote in list(prior.file_hashes):
        if remote == inst_remote:
            continue
        if remote in new_manifest.file_hashes:
            continue
        # remote belonged to a skill we still ship → file was removed.
        if any(
            remote.startswith(f"{skills_remote_root}/{skill}/")
            for skill in deployed_skills
        ):
            print(f"  remove: {remote} (file removed from skill)")
            delete_path(client, remote, dry_run=dry_run)

    # 4. Write the new manifest.
    if dry_run:
        print(f"  [dry-run] would write manifest to {mfst_remote}")
    else:
        write_manifest(client, mfst_remote, new_manifest)
    print(f"[{workspace_name}] done.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Deploy a workspace from build/.")
    parser.add_argument("--workspace", "-w", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--sha",
        default=os.environ.get("GITHUB_SHA"),
        help="Git SHA recorded in the manifest (defaults to $GITHUB_SHA).",
    )
    args = parser.parse_args()
    return deploy_workspace(args.workspace, sha=args.sha, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
