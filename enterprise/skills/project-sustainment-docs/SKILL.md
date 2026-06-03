---
name: project-sustainment-docs
description: |
  Use when documenting a Databricks Spark Declarative Pipeline (Lakeflow / SDP) for
  agent-led sustainment. Generates an AGENTS.md alongside the pipeline source that
  future Genie Code sessions in that folder auto-discover and load into context.
  Triggers on phrases like "document this pipeline", "create AGENTS.md for", "write
  handoff docs", "sustainment doc", "agent context for this pipeline", "write the
  README for this pipeline so the next agent can take over".
tags: [documentation, sustainment, sdp, lakeflow, agents-md]
owners: [data-platform-team]
---

# Project Sustainment Documentation (Spark Declarative Pipelines)

You are generating an `AGENTS.md` file that future agents (and humans) will read to maintain a Lakeflow Spark Declarative Pipeline. The single most important thing this file captures is **why** the pipeline is built the way it is — the things that aren't visible in the code and would otherwise be lost when the original engineer moves on.

This skill is for **SDP / Lakeflow pipelines only in v1**. If the user asks you to document a Genie space, AI/BI dashboard, ML training job, or anything else, politely decline and say a future version of this skill will cover it.

## When to use this skill

Triggered when the user wants to document a pipeline for sustainment / handoff. Phrases include:

- "Document this pipeline"
- "Create AGENTS.md for this pipeline"
- "Write the handoff doc"
- "Write the README so the next agent can take over"
- "Sustainment doc for X"

If a pipeline folder **already** has an `AGENTS.md`, treat this as an update request — see the *Update workflow* section below.

## What you are producing, and why

A single `AGENTS.md` file written to the pipeline's source folder (next to `pipeline.yaml`, `databricks.yml`, or the `.py` / `.sql` files that define the pipeline).

**`AGENTS.md` is auto-discovered by Genie Code** — when a future user opens any file in or below this folder, the contents of `AGENTS.md` are injected into the assistant's context automatically. You don't need to do anything else for the next agent to read it. (See `https://docs.databricks.com/aws/en/genie-code/instructions` for the auto-discovery behavior.)

**Keep the final file under ~5,000 characters.** It supplements (does not replace) the 20,000-character workspace instructions. If a section grows long, summarize it inline and link out to a longer doc (e.g. a Confluence page or a sibling `RUNBOOK.md`).

## Workflow

Work in four phases. Don't skip phase 1 — inferring first means you only interrupt the user with questions you genuinely can't answer.

### Phase 1 — Infer everything you can

Read these sources in order and accumulate facts before drafting anything:

1. **Pipeline configuration** — `pipeline.yaml` or `databricks.yml` (DAB). Extract:
   - Pipeline name, target catalog/schema
   - Configured schedule (`continuous` vs triggered + cron)
   - Compute mode (serverless vs classic)
   - Photon enabled / runtime version if specified
2. **Pipeline source files** — every `*.sql` and `*.py` in the folder. Extract:
   - Each `CREATE [OR REFRESH] STREAMING TABLE` and `CREATE [OR REFRESH] MATERIALIZED VIEW` (or `@dlt.table` / `@dlt.view` in Python). For each, capture: table name, kind (streaming table vs MV), data sources it reads, expectations / data-quality rules
   - Any `APPLY CHANGES INTO` blocks (CDC patterns)
   - Schema declarations and explicit partitioning
3. **Unity Catalog metadata** for the tables this pipeline produces (compose with the `data-exploration` skill — use `databricks experimental aitools tools query` to hit `system.information_schema.tables` and `discover-schema` for column types):
   - Existence and current schema of produced tables
   - Row counts and freshness (`MAX(<timestamp_col>)`) where useful
4. **UC lineage** for upstream + downstream (when accessible):
   ```sql
   -- Upstream sources actually used
   SELECT source_table_full_name, source_type
   FROM system.access.table_lineage
   WHERE target_table_full_name = '<produced_table>'
   ORDER BY event_time DESC LIMIT 50;

   -- Downstream consumers
   SELECT target_table_full_name, target_type
   FROM system.access.table_lineage
   WHERE source_table_full_name = '<produced_table>'
   ORDER BY event_time DESC LIMIT 50;
   ```
5. **Pipeline run history** (optional): if accessible via the Jobs/Pipelines API, note the observed schedule and recent success/failure rate. Don't get stuck here if the API isn't available — drop a `_(no run history available)_` placeholder.

After Phase 1 you should have a confident answer for: **Architecture, Tables produced, Dependencies (upstream + downstream), Operational characteristics (configured schedule + compute), Testing (if pytest / expectations exist)**.

You should NOT have an answer for: **Purpose, Implementation choices & rationale, Known gotchas, Change protocol, SLA, Open questions**. These come from Phase 3.

### Phase 2 — Draft

Read `template.md` from this skill folder. Copy it. Fill in every section you have evidence for from Phase 1. For each section you can't fill, leave the `<!-- TODO: ... -->` markers in place — they make the gaps explicit.

Show the draft to the user. Say something like:

> "Here's the draft. I've filled in everything I could infer from the pipeline source and Unity Catalog. The TODO markers below show where I need your input. I'll ask you a few targeted questions next."

### Phase 3 — Interview

Ask the user in small batches — 2 or 3 questions at a time, not the full list at once. The user will tune out a wall of questions and give shallow answers.

**Critical questions (ask these even if you think you can infer them):**

- **Purpose**: "Who consumes this pipeline's output, and what business decision does it support? If it stopped running for a day, who would notice and why?"
- **Implementation choice**: "What was the most non-obvious design decision you made building this — something a future agent would change if they didn't know better?"
- **Gotchas**: "What's already broken once that future-you would want flagged? Anything that took you more than an hour to debug?"
- **Change protocol**: "What's the one thing a future agent must NOT do without checking with a human? An invariant, an SLA constraint, an upstream contract, a regulated field?"
- **SLA**: "How fresh does the output need to be, and who notices if it's late?"

**Conditional questions** (only ask if relevant from Phase 1 inference):

- If you saw streaming tables AND materialized views in the same pipeline: "Why streaming for X but MV for Y?"
- If you saw `APPLY CHANGES INTO`: "What's the source-of-truth for the merge key, and what happens if you see a duplicate?"
- If you saw expectations / data-quality rules: "Are those expectations enforced (`ON VIOLATION FAIL`) or advisory? What's the recovery if they fail in prod?"
- If upstream tables include any catalog you don't own: "Who owns `<catalog>` and what's the SLA they offered?"

### Phase 4 — Finalize

1. Write the completed `AGENTS.md` to the pipeline's folder.
2. Confirm the final character count is **under 5,000**. If over: tell the user, ask them which sections to summarize, and link out to a longer doc.
3. Tell the user: "Open a fresh Genie Code chat in this folder — your next session will auto-load this file."

## Update workflow

When `AGENTS.md` already exists in the folder:

1. **Read it first**. Do not regenerate from scratch.
2. Re-run Phase 1 inference and compare to what's documented. Look for:
   - New tables added to the pipeline that aren't in the doc
   - Tables removed from the pipeline that are still in the doc
   - Schedule / configuration changes
   - New CDC blocks, expectations, or partitioning changes
3. Show the user a targeted diff: "Here's what's changed since the AGENTS.md was last written. The `Purpose` and `Change protocol` sections look unchanged — I won't touch them. The `Tables produced` section needs these updates: ..."
4. Apply only the targeted changes after user confirmation.

If the user explicitly says "regenerate from scratch", do so — but warn them they'll lose the interview-derived content unless they answer those questions again.

## What NOT to do

- **Don't document anything other than SDP/Lakeflow pipelines in v1.** Politely refuse and say a future version covers Genie spaces and dashboards.
- **Don't fabricate "why" content.** If the user can't tell you, write `_unknown — original engineer not available_` rather than inventing a rationale.
- **Don't include secrets, credentials, or raw PII values.** Reference them by name (e.g. "uses secret `databricks/orders/sftp_password`") and let workspace permissions resolve.
- **Don't exceed 5,000 characters in the final file.** Link out to longer docs instead.
- **Don't ask all interview questions at once.** Batch into 2–3 at a time.
- **Don't overwrite an existing AGENTS.md without reading it first.** That's the update workflow.

## References

- [`template.md`](template.md) — the AGENTS.md skeleton to copy and fill in
- [`example.md`](example.md) — a worked example of a completed AGENTS.md for a fictional `orders_ingest` pipeline
