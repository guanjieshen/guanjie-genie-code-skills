"""Resolve credentials for a workspace and produce an authenticated WorkspaceClient.

Two modes, controlled by `auth.mode` in defaults.yaml / config.yaml:

  account_sp     (default) — one service principal at the Databricks account level,
                  granted access to every managed workspace. Credentials live in two
                  org-wide GitHub secrets:
                      ACCOUNT_SP_CLIENT_ID
                      ACCOUNT_SP_CLIENT_SECRET

  workspace_sp   — per-workspace SP. config.yaml names the GitHub secret keys
                  to read for that workspace.

The caller never branches on auth mode; it just calls `get_client(config)`.
"""
from __future__ import annotations

import os
import sys

from databricks.sdk import WorkspaceClient

from .config import WorkspaceConfig

ACCOUNT_SP_CLIENT_ID_ENV = "ACCOUNT_SP_CLIENT_ID"
ACCOUNT_SP_CLIENT_SECRET_ENV = "ACCOUNT_SP_CLIENT_SECRET"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"missing required env var: {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def get_client(config: WorkspaceConfig) -> WorkspaceClient:
    mode = config.auth.get("mode", "account_sp")
    if mode == "account_sp":
        return WorkspaceClient(
            host=config.host,
            client_id=_require_env(ACCOUNT_SP_CLIENT_ID_ENV),
            client_secret=_require_env(ACCOUNT_SP_CLIENT_SECRET_ENV),
        )
    if mode == "workspace_sp":
        client_id_env = config.auth.get("client_id_secret")
        client_secret_env = config.auth.get("client_secret_secret")
        if not (client_id_env and client_secret_env):
            raise SystemExit(
                f"workspace {config.name}: auth.mode=workspace_sp requires "
                f"client_id_secret and client_secret_secret in config.yaml"
            )
        return WorkspaceClient(
            host=config.host,
            client_id=_require_env(client_id_env),
            client_secret=_require_env(client_secret_env),
        )
    raise SystemExit(f"workspace {config.name}: unknown auth.mode '{mode}'")
