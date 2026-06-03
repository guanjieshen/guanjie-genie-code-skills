<!--
This is the AGENTS.md template. Copy it into the pipeline's source folder
as `AGENTS.md`, then fill in each section. The `<!-- TODO: ... -->` markers
indicate gaps the original engineer must answer — they cannot be inferred
from code or Unity Catalog metadata.

Keep the final file under 5,000 characters. If a section grows long,
summarize and link out (e.g. to a Confluence page or a sibling RUNBOOK.md).
-->

# `<pipeline-name>` — Sustainment Notes

> Auto-loaded by Genie Code for any session in this folder. Edit alongside the pipeline whenever you make a material change.

**Last updated:** <!-- TODO: YYYY-MM-DD --> · **Original author(s):** <!-- TODO: name(s) -->

## Purpose

<!-- TODO: 1–3 sentences. What business problem does this pipeline solve? Who consumes the output? What decision or downstream process depends on it? If it stopped running for a day, who would notice and why? -->

## Architecture

<!-- Infer this from the pipeline source. Replace with a short description or ASCII/mermaid diagram. -->

```
<source system> ──▶ bronze.<table> ──▶ silver.<table> ──▶ gold.<table> ──▶ <consumer>
```

## Tables produced

| Table | Kind | Read by | Notes |
|---|---|---|---|
| `catalog.schema.bronze_x` | Streaming Table | `silver_x` | <!-- e.g. partitioned by event_date, ingest from S3 --> |
| `catalog.schema.silver_x` | Materialized View | downstream BI | <!-- e.g. APPLY CHANGES INTO from bronze_x, deduped on order_id --> |
| `catalog.schema.gold_x` | Materialized View | `<dashboard / Genie space>` | <!-- e.g. daily aggregate, refreshed at 04:00 UTC --> |

## Implementation choices & rationale

<!-- The most valuable section for future agents. Document the WHY for each non-obvious design choice. -->

- **<!-- TODO: choice 1 -->** — <!-- TODO: rationale -->
- **<!-- TODO: choice 2 -->** — <!-- TODO: rationale -->
- **<!-- e.g. "Streaming tables for bronze, MVs for silver" --> ** — <!-- e.g. "Bronze is append-only event stream; silver needs full-refresh semantics because the source occasionally back-fills." -->

## Operational characteristics

- **Schedule:** <!-- e.g. continuous, or triggered cron 0 */1 * * * -->
- **Freshness SLA:** <!-- TODO: e.g. "P99 < 15 min from source-event to gold.* table" -->
- **Compute:** <!-- e.g. serverless, or classic cluster <id> with photon enabled -->
- **Cost profile:** <!-- TODO: rough $/day or DBU/day if known; otherwise "not tracked" -->
- **Owner / on-call:** <!-- TODO: team and contact -->

## Dependencies

**Upstream:**

- <!-- TODO: upstream table or source system 1 --> — owned by <!-- TODO: team -->. SLA: <!-- TODO -->.
- <!-- TODO: upstream 2 -->

**Downstream consumers:**

- <!-- e.g. dashboard "Orders Daily" — owned by Finance --> 
- <!-- e.g. Genie space "Sales Q&A" -->

**Secrets / credentials:** <!-- TODO: list secret SCOPES (not values), e.g. databricks/orders/sftp_password -->

**Warehouses / compute:** <!-- TODO: SQL warehouse used by downstream consumers, if any -->

## Known gotchas & failure modes

<!-- Anything that has broken at least once. Future-you will thank present-you. -->

- <!-- TODO: gotcha 1 — what broke, what to look for, how to recover -->
- <!-- e.g. "Source SFTP drops connections >100 GB; pipeline auto-retries 3× then fails with cryptic 'Connection reset' — rerun the failed update from the Pipelines UI, do NOT full-refresh." -->

## Change protocol (read before making changes)

> The single most important section. List invariants and "before changing X, consider Y" notes.

- <!-- TODO: invariant 1 — e.g. "Do not change partitioning on bronze.orders. The downstream MV assumes daily partitions for refresh efficiency." -->
- <!-- TODO: invariant 2 — e.g. "order_id is the merge key in APPLY CHANGES INTO. If the source schema ever adds a v2 order_id, do not silently switch — coordinate with the upstream team." -->
- <!-- TODO: regulated field warning — e.g. "customer_email is masked at the silver layer. Do not promote raw email to gold without re-running the privacy review." -->

## Testing & validation

<!-- How to verify a change works end-to-end before merging. -->

- **Local / dev**: <!-- e.g. "Run pipeline with target=dev_<your_name>, sample data in dev catalog, verify row counts match expectations." -->
- **Expectations**: <!-- list any inline expectations / data quality rules, ON VIOLATION setting -->
- **Smoke check**: <!-- e.g. "SELECT COUNT(*) FROM gold.orders_daily WHERE event_date = current_date() — expect non-zero after 04:30 UTC." -->
- **Test suite**: <!-- TODO: pytest path if any, or "_none_" -->

## Open questions / future work

<!-- Things you punted on. Capturing them here prevents the next agent from re-litigating the same trade-offs. -->

- <!-- TODO: known limitation 1 -->
- <!-- TODO: future enhancement someone asked about but you deferred -->

## Related docs

- <!-- TODO: link to PRD, design doc, runbook, JIRA epic, Slack channel — anything that adds context -->
