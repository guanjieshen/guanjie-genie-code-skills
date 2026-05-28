# Guanjie's Genie Code Skills

Personal collection of [Genie Code skills](https://docs.databricks.com/aws/en/genie-code/skills) for Databricks workspaces.

## What's here

```
guanjie-genie-code-skills/
├── skills/
│   └── genie-skill-template/     # starter template — copy this to make a new skill
│       └── SKILL.md
└── install_genie_code_skills.py  # Databricks notebook installer
```

Each skill is a folder with a `SKILL.md` (frontmatter + markdown body) plus any supporting files referenced from `SKILL.md`. See the [Agent Skills Spec](https://agentskills.io/specification) and the [Genie Code Skills docs](https://docs.databricks.com/aws/en/genie-code/skills).

## Install from a Databricks notebook

No local terminal required — works on any compute, including serverless.

1. Open your Databricks workspace.
2. Import [`install_genie_code_skills.py`](./install_genie_code_skills.py) as a notebook (`Workspace → Import → File → URL` and paste the raw GitHub URL, or drag-drop the file).
3. Set the widgets at the top:
   - **github_owner** — your GitHub username/org
   - **github_repo** — `guanjie-genie-code-skills`
   - **branch** — `main`
   - **scope** — `user` (only you) or `workspace` (everyone, needs admin)
   - **skills** — `all` or a comma-separated list of skill names
   - **github_token** — only needed for private repos
   - **dry_run** — `true` to preview without uploading
4. Run all cells.
5. Open Genie Code in a **new chat** — your skills are picked up automatically. (Edits to existing skills only apply in new chats.)

### Install locations

| Scope | Path | Visibility |
|---|---|---|
| `user` (default) | `/Workspace/Users/<your-email>/.assistant/skills/` | Just you |
| `workspace` | `/Workspace/.assistant/skills/` | Everyone in the workspace (admin required) |

## Add a new skill

1. Copy `skills/genie-skill-template/` to `skills/<your-skill-name>/`.
2. Edit `SKILL.md`:
   - `name` — kebab-case, matches the folder name
   - `description` — be specific about triggers; Genie matches on this
   - Body — direct instructions, examples, edge cases
3. Commit, push, re-run the installer notebook.

### Frontmatter

```yaml
---
name: my-skill
description: One or two sentences. What does this teach Genie, and when should it use it? Include trigger phrases.
---
```

## Tips

- **Be specific in `description`** — Genie uses it to decide when to load the skill. Vague descriptions = skill never fires.
- **Reference supporting files** with relative paths in `SKILL.md`. They're loaded on demand, not always.
- **Start a new chat** after editing — running chats don't reload skills.
- Invoke manually with `@<skill-name>` in a Genie Code prompt.

## License

TBD.
