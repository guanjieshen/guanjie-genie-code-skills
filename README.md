# Databricks Enterprise Skills

GitOps repo template for managing **Genie Code skills + workspace instructions** across many Databricks workspaces in one organization.

## What this does

- **Enterprise tier** (`enterprise/`) — skills + instructions deployed to every managed workspace.
- **Workspace tier** (`workspaces/<name>/`) — per-workspace overlays.
- **Effective state in a workspace** = enterprise + workspace-specific, with explicit inheritance controls.
- **CI/CD via GitHub Actions** — merge to `main` → diff-aware matrix deploys.
- **Centralized credentials** — one account-level service principal reaches every workspace.

## Layout

```
.
├── defaults.yaml                   # repo-wide config defaults
├── enterprise/                     # default-inherited layer
│   ├── instructions/               # *.md, ordered by filename (00-*, 10-*, ...)
│   └── skills/                     # one folder per skill, can be nested by domain
│       └── data-exploration/SKILL.md
├── workspaces/
│   ├── _example/config.yaml        # template — copy to create a new workspace
│   └── <name>/
│       ├── config.yaml             # only fields that override defaults
│       ├── instructions/           # workspace-specific instruction files
│       └── skills/                 # workspace-specific skills
├── scripts/
│   ├── compile.py                  # builds build/<workspace>/ artifacts
│   ├── validate.py                 # frontmatter + cap + naming checks
│   ├── deploy.py                   # pushes build/<workspace>/ into Databricks
│   ├── plan.py                     # local preview of a workspace's effective state
│   └── lib/                        # auth, inheritance, workspace I/O
└── .github/workflows/
    ├── validate-pr.yml             # lint + compile + cap check on PR
    ├── deploy-on-merge.yml         # main push → diff-aware matrix deploy
    ├── deploy-manual.yml           # workflow_dispatch for explicit redeploys / rollback
    └── drift-check.yml             # nightly: compare deployed vs repo
```

## Quick start (admins)

### 1. One-time account-SP setup

1. In the Databricks **account console**, create a service principal.
2. Assign it to every managed workspace with **Workspace admin** entitlement.
3. Mint OAuth credentials for the SP (client_id + client_secret).
4. Add them to this repo as **organization-level GitHub secrets**:
   - `ACCOUNT_SP_CLIENT_ID`
   - `ACCOUNT_SP_CLIENT_SECRET`

### 2. Register your first workspace

```bash
cp -r workspaces/_example workspaces/analytics-prod
# edit workspaces/analytics-prod/config.yaml — set host + workspace_id
```

Then in **GitHub repo settings → Environments**, create one Environment per workspace (name must match the folder, e.g. `analytics-prod`). Add reviewer protection to any Environment that represents a production workspace.

### 3. Add content

- **Enterprise skill**: drop a folder under `enterprise/skills/<skill-name>/` containing `SKILL.md`. Optionally nest by domain (`enterprise/skills/data-eng/some-skill/SKILL.md`) — the walker finds it.
- **Enterprise instructions**: drop a `*.md` file under `enterprise/instructions/`. Files load in lexical order; use numeric prefixes (`00-`, `10-`, `20-`).
- **Workspace overlay**: same shape but under `workspaces/<name>/`.

Every SKILL.md needs YAML frontmatter:

```yaml
---
name: my-skill                       # must match the folder name
description: |
  Specific enough that Genie knows when to load it. Include trigger phrases.
tags: [data, sql]                    # reserved for future tag-based composition
owners: [data-platform-team]         # reserved for path-level CODEOWNERS
---
```

### 4. Preview locally

```bash
pip install -r requirements.txt
python scripts/plan.py --workspace analytics-prod
python scripts/plan.py --workspace analytics-prod --print-instructions
python scripts/validate.py
python scripts/compile.py            # writes build/<workspace>/
```

### 5. Ship

Open a PR. `validate-pr.yml` runs validation + compiles a preview artifact you can download. Once merged, `deploy-on-merge.yml` deploys only the workspaces affected by the diff.

## How a change flows

1. **Edit on a branch** — add a skill, change instructions, etc.
2. **PR validation** — frontmatter check, 20K-char cap check, full compile of every workspace, build artifact uploaded.
3. **Merge to main** — only the changes diff-routed to affected workspaces.
4. **Matrix deploy** — one parallel job per affected workspace, authed as the account SP, scoped to that workspace's GitHub Environment.
5. **Manifest update** — each workspace stores `/Workspace/.assistant/skills/.managed_by_<repo>.json` so the next deploy knows what to clean up.

Files the deploy script writes:

| Scope | Path |
|---|---|
| Workspace instructions | `/Workspace/.assistant_workspace_instructions.md` |
| Workspace skills | `/Workspace/.assistant/skills/<skill>/...` |
| User-scoped (per-deployer) | `/Workspace/Users/<email>/.assistant_instructions.md` + `/Workspace/Users/<email>/.assistant/skills/` |

## Inheritance model

Per-workspace `config.yaml` controls what's inherited:

```yaml
inheritance:
  layers: [enterprise]            # ordered list of layer dirs. Workspace overlays last.
  instructions:
    enabled: true                 # false → drop inherited instructions, keep only workspace's own
  skills:
    enterprise: all               # or: [data-exploration, pii-handling] — explicit allow-list
```

**Skill name collisions**: workspace wins. Validator emits a warning.

**Extending to a third tier later** (e.g. by-domain or by-region profiles):

```yaml
inheritance:
  layers: [enterprise, profiles/hipaa]
  skills:
    enterprise: all
    hipaa: all
```

Create `profiles/hipaa/` matching the `enterprise/` shape — no script changes needed.

## Constraints to be aware of

- **Workspace instructions are capped at 20,000 characters** ([Databricks docs](https://docs.databricks.com/aws/en/genie-code/instructions)). `validate.py` and `compile.py` fail loudly if exceeded.
- **A Genie Code chat session reads skills on session start.** Edits to existing skills only apply in **new chats**.
- **The managed-by manifest tracks what we deployed.** Skills users add manually in the workspace UI are left alone; skills we previously deployed but that have been removed from the repo get cleaned up on the next deploy.

## Comparison: why the Python SDK and not DABs / Git folders / Terraform

| Approach | Verdict |
|---|---|
| Databricks Asset Bundles | Ruled out — no `workspace_file` resource type. DABs is for jobs/pipelines/apps. |
| Databricks Git folders | Officially recommended for single-workspace version control but does verbatim sync — no compile step, no enterprise+workspace overlay. Incompatible with this repo's composition model. |
| Terraform `databricks_workspace_file` | Viable alternative with free drift detection via state; could be swapped in by re-implementing `scripts/lib/workspace_io.py`. Adds a state backend per workspace. Worth revisiting if your org already runs Terraform for Databricks. |
| Databricks CLI `workspace import-dir` | Same primitives as the SDK — less flexible for our diff/manifest logic. |
| **Python SDK** (chosen) | What the official [genie-code-skills-demo](https://github.com/databricks-solutions/genie-code-skills-demo) uses. Owns the compile + manifest logic cleanly. |

## License

TBD.
