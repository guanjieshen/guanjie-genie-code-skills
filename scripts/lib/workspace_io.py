"""Thin wrappers around WorkspaceClient.workspace for the deploy step.

Centralizes:
  - path resolution (workspace vs user scope)
  - file content hashing (for idempotent uploads)
  - the managed-by manifest read/write (state lives in the workspace itself)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from io import BytesIO

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, ObjectType

from .config import WorkspaceConfig

# Constants — Databricks Genie Code expects exactly these paths.
WORKSPACE_INSTRUCTIONS_PATH = "/Workspace/.assistant_workspace_instructions.md"
WORKSPACE_SKILLS_ROOT = "/Workspace/.assistant/skills"


def _user_instructions_path(client: WorkspaceClient) -> str:
    me = client.current_user.me().user_name
    return f"/Workspace/Users/{me}/.assistant_instructions.md"


def _user_skills_root(client: WorkspaceClient) -> str:
    me = client.current_user.me().user_name
    return f"/Workspace/Users/{me}/.assistant/skills"


def instructions_path(client: WorkspaceClient, config: WorkspaceConfig) -> str:
    return (
        WORKSPACE_INSTRUCTIONS_PATH
        if config.scope == "workspace"
        else _user_instructions_path(client)
    )


def skills_root(client: WorkspaceClient, config: WorkspaceConfig) -> str:
    return (
        WORKSPACE_SKILLS_ROOT
        if config.scope == "workspace"
        else _user_skills_root(client)
    )


def manifest_path(client: WorkspaceClient, config: WorkspaceConfig, repo_name: str) -> str:
    return f"{skills_root(client, config)}/.managed_by_{repo_name}.json"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class DeployedManifest:
    sha: str | None = None           # git SHA of last successful deploy
    skills: list[str] = None         # skill names previously deployed
    file_hashes: dict = None         # workspace_path -> sha256 of last-uploaded content

    @classmethod
    def empty(cls) -> "DeployedManifest":
        return cls(sha=None, skills=[], file_hashes={})

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "skills": sorted(self.skills or []),
            "file_hashes": self.file_hashes or {},
        }


def read_manifest(client: WorkspaceClient, path: str) -> DeployedManifest:
    try:
        client.workspace.get_status(path)
    except Exception:
        return DeployedManifest.empty()
    raw = b"".join(client.workspace.download(path))
    data = json.loads(raw.decode("utf-8"))
    return DeployedManifest(
        sha=data.get("sha"),
        skills=data.get("skills", []),
        file_hashes=data.get("file_hashes", {}),
    )


def write_manifest(
    client: WorkspaceClient, path: str, manifest: DeployedManifest
) -> None:
    payload = json.dumps(manifest.to_dict(), indent=2).encode("utf-8")
    ensure_parent_dir(client, path)
    client.workspace.upload(
        path,
        BytesIO(payload),
        format=ImportFormat.AUTO,
        overwrite=True,
    )


def ensure_parent_dir(client: WorkspaceClient, path: str) -> None:
    parent = path.rsplit("/", 1)[0]
    if parent:
        client.workspace.mkdirs(parent)


def upload_file(
    client: WorkspaceClient, path: str, content: bytes, *, dry_run: bool = False
) -> None:
    if dry_run:
        print(f"  [dry-run] would upload {path} ({len(content)} bytes)")
        return
    ensure_parent_dir(client, path)
    client.workspace.upload(
        path,
        BytesIO(content),
        format=ImportFormat.AUTO,
        overwrite=True,
    )


def delete_path(client: WorkspaceClient, path: str, *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [dry-run] would delete {path}")
        return
    try:
        client.workspace.delete(path, recursive=True)
    except Exception as e:
        print(f"  warn: failed to delete {path}: {e}")


def list_dir(client: WorkspaceClient, path: str) -> list[tuple[str, ObjectType]]:
    try:
        return [(o.path, o.object_type) for o in client.workspace.list(path)]
    except Exception:
        return []
