# Databricks notebook source
# MAGIC %md
# MAGIC # Install Guanjie's Genie Code Skills
# MAGIC
# MAGIC Downloads skills from a GitHub repo and uploads them into this workspace's
# MAGIC `.assistant/skills/` directory so they are picked up by Genie Code.
# MAGIC
# MAGIC Works on any compute, including **serverless** — uses only the Databricks SDK
# MAGIC and the public GitHub API.
# MAGIC
# MAGIC **Steps:**
# MAGIC 1. Set the widgets at the top (repo, branch, scope, skills, optional token).
# MAGIC 2. Run all cells.
# MAGIC 3. Open Genie Code in a new chat — your skills are available.

# COMMAND ----------

dbutils.widgets.text("github_owner", "guanjieshen", "GitHub owner")
dbutils.widgets.text("github_repo", "guanjie-genie-code-skills", "GitHub repo")
dbutils.widgets.text("branch", "main", "Branch / ref")
dbutils.widgets.dropdown("scope", "user", ["user", "workspace"], "Install scope")
dbutils.widgets.text("skills", "all", "Skills (comma-separated, or 'all')")
dbutils.widgets.text("github_token", "", "GitHub token (private repos only)")
dbutils.widgets.dropdown("dry_run", "false", ["false", "true"], "Dry run (no uploads)")

# COMMAND ----------

# MAGIC %pip install --quiet --upgrade databricks-sdk
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import io
import json
import urllib.request
from urllib.error import HTTPError

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

owner = dbutils.widgets.get("github_owner").strip()
repo = dbutils.widgets.get("github_repo").strip()
branch = dbutils.widgets.get("branch").strip() or "main"
scope = dbutils.widgets.get("scope").strip()
skills_arg = dbutils.widgets.get("skills").strip()
gh_token = dbutils.widgets.get("github_token").strip()
dry_run = dbutils.widgets.get("dry_run").strip().lower() == "true"

w = WorkspaceClient()

if scope == "workspace":
    install_root = "/Workspace/.assistant/skills"
else:
    me = w.current_user.me().user_name
    install_root = f"/Workspace/Users/{me}/.assistant/skills"

print(f"Repo:         {owner}/{repo}@{branch}")
print(f"Install root: {install_root}")
print(f"Skills:       {skills_arg}")
print(f"Dry run:      {dry_run}")

# COMMAND ----------

def _gh_request(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if gh_token:
        req.add_header("Authorization", f"Bearer {gh_token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.read()
    except HTTPError as e:
        raise RuntimeError(f"GitHub {e.code} for {url}: {e.read().decode(errors='replace')}") from e


def gh_list(path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    return json.loads(_gh_request(url))


def gh_raw(item):
    url = item["download_url"]
    if url is None:
        raise RuntimeError(f"No download_url for {item['path']} — submodule or symlink?")
    return _gh_request(url)


def list_skills():
    items = gh_list("skills")
    return [it["name"] for it in items if it["type"] == "dir"]


def walk_skill(skill_name, sub_path=""):
    path = f"skills/{skill_name}" + (f"/{sub_path}" if sub_path else "")
    for it in gh_list(path):
        rel = it["path"].split(f"skills/{skill_name}/", 1)[1]
        if it["type"] == "file":
            yield rel, gh_raw(it)
        elif it["type"] == "dir":
            yield from walk_skill(skill_name, rel)

# COMMAND ----------

available = list_skills()
print(f"Available skills in repo: {available}")

if skills_arg.lower() == "all":
    selected = available
else:
    selected = [s.strip() for s in skills_arg.split(",") if s.strip()]
    unknown = [s for s in selected if s not in available]
    if unknown:
        raise ValueError(f"Unknown skill(s): {unknown}. Available: {available}")

print(f"Will install: {selected}")

# COMMAND ----------

def upload(workspace_path: str, content: bytes) -> None:
    parent = workspace_path.rsplit("/", 1)[0]
    if dry_run:
        print(f"   [dry-run] would upload {workspace_path} ({len(content)} bytes)")
        return
    w.workspace.mkdirs(parent)
    w.workspace.upload(
        path=workspace_path,
        content=io.BytesIO(content),
        format=ImportFormat.AUTO,
        overwrite=True,
    )


total_files = 0
for skill in selected:
    print(f"→ {skill}")
    for rel_path, content in walk_skill(skill):
        target = f"{install_root}/{skill}/{rel_path}"
        upload(target, content)
        total_files += 1
        print(f"   uploaded {target}")

print(f"\nDone. {len(selected)} skill(s), {total_files} file(s) {'(dry run)' if dry_run else 'uploaded'}.")
print(f"Start a new Genie Code chat to pick them up.")
