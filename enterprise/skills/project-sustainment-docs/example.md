<!--
A worked example. This is what a completed AGENTS.md for a Lakeflow pipeline
should look like — the level of detail, the tone, the kinds of "why" notes
that justify the file existing. Refer to it when you're not sure how much
to write or how to phrase a section.

The pipeline in this example is fictional (`orders_ingest`).
-->

# `orders_ingest` — Sustainment Notes

> Auto-loaded by Genie Code for any session in this folder. Edit alongside the pipeline whenever you make a material change.

**Last updated:** 2026-05-12 · **Original author(s):** Guanjie Shen, Priya N.

## Purpose

Ingests raw order events from the legacy SFTP drop and lands them in `prod.orders.*` so the Finance BI team can run their daily revenue-recognition dashboard. If this pipeline stops for >12h, Finance's daily revenue close at 09:00 UTC the next morning slips.

## Architecture

```
sftp://legacy-orders/<date>/*.json
        │
        ▼
prod.orders.bronze_orders_raw   (Streaming Table)
        │
        ▼
prod.orders.silver_orders       (Streaming Table, APPLY CHANGES INTO)
        │
        ▼
prod.orders.gold_orders_daily   (Materialized View, daily aggregation)
        │
        ▼
"Finance Revenue Daily" dashboard · "Sales Q&A" Genie space
```

## Tables produced

| Table | Kind | Read by | Notes |
|---|---|---|---|
| `prod.orders.bronze_orders_raw` | Streaming Table | `silver_orders` | Append-only landing, partitioned by `event_date`. Source files retained 30 days for replay. |
| `prod.orders.silver_orders` | Streaming Table | `gold_orders_daily`, ad-hoc | `APPLY CHANGES INTO` on `order_id`; PII columns (`email`, `phone`) hash-masked. |
| `prod.orders.gold_orders_daily` | Materialized View | Finance dashboard, Genie space | Daily aggregate by `order_date × region`; refreshed at 04:00 UTC. |

## Implementation choices & rationale

- **Streaming Table for bronze, MV for gold** — bronze must capture every source event including duplicates and late arrivals (audit requirement); gold is aggregated and can fully refresh.
- **Hash-mask PII at silver, not bronze** — legal asked for an unmasked audit copy that's queryable only by Compliance. The masked silver is what every other team reads.
- **Continuous schedule, not triggered** — the SFTP source pushes throughout the day in irregular bursts; latency-sensitive consumers (Finance close) need <15 min from source-write to gold. A triggered schedule made the worst-case latency unpredictable.
- **Serverless compute** — bursty load made cluster sizing wasteful; serverless's per-second billing cut DBU spend ~40% vs the prior classic cluster.

## Operational characteristics

- **Schedule:** continuous
- **Freshness SLA:** P99 < 15 min from source-file landing to `gold_orders_daily` row
- **Compute:** serverless, Photon enabled
- **Cost profile:** ~$80/day (tracked in `system.billing.usage` dashboard "orders-pipeline-cost")
- **Owner / on-call:** Data Platform team, #data-platform-oncall (Slack)

## Dependencies

**Upstream:**

- `sftp://legacy-orders/` — owned by Order Management team. SLA: files land within 5 min of order creation. Contact: #order-mgmt-eng.

**Downstream consumers:**

- Dashboard **Finance Revenue Daily** — owned by Finance BI (#finance-bi).
- Genie space **Sales Q&A** — used by sales leadership for ad-hoc queries.
- `prod.compliance.orders_audit_view` — Compliance's read-only view over bronze.

**Secrets / credentials:** `databricks/orders/sftp_password` (scope: `orders-pipeline`)

**Warehouses:** `wh-finance-bi` (SQL warehouse used by the Finance dashboard; not managed here).

## Known gotchas & failure modes

- **SFTP drops connections on files >100 GB.** Pipeline auto-retries 3× then fails with a cryptic `Connection reset by peer`. Fix: rerun the failed update from the Pipelines UI. **Do NOT full-refresh** — bronze must remain append-only for the audit trail.
- **Daylight savings transitions** cause silver→gold reconciliation drift for ~2 hours twice a year. We log it; Finance has accepted the gap.
- **Bronze partition pruning** breaks if any `event_date` value lands as a string instead of a date. The source-system change in 2025-Q4 already caused this once; we added a `CAST(event_date AS DATE)` in bronze defensively.

## Change protocol (read before making changes)

- **Do not change partitioning on `bronze_orders_raw`.** Compliance's `orders_audit_view` depends on daily-partition predicate pushdown for cost reasons.
- **`order_id` is the merge key in silver's `APPLY CHANGES INTO`.** If the source ever introduces `order_id_v2`, do not silently switch. Coordinate with Order Management — they have downstream systems keyed on the original.
- **`email` and `phone` are masked at silver.** Do not promote raw values to gold or any new table without re-running the privacy review with Legal (#privacy-review).
- **The Finance close depends on `gold_orders_daily` being current by 04:30 UTC.** Any schema change to gold needs to be deployed before 18:00 UTC the prior day, or coordinated with Finance to skip a close.

## Testing & validation

- **Local / dev**: deploy pipeline with `target=dev_<your_name>`. The DAB config provisions a dev catalog. Sample data in `dev_orders.bronze_orders_raw` is a 1% sample of last week's prod.
- **Expectations**: `silver_orders` has `EXPECT (order_id IS NOT NULL) ON VIOLATION DROP ROW`. `gold_orders_daily` has `EXPECT (daily_revenue >= 0) ON VIOLATION FAIL UPDATE`.
- **Smoke check**: after deploy, `SELECT COUNT(*) FROM prod.orders.gold_orders_daily WHERE order_date = current_date() - 1` — should match the Finance dashboard headline number for yesterday within 0.1%.
- **Test suite**: `tests/test_orders_ingest.py` (pytest, runs in CI on PR).

## Open questions / future work

- We deferred backfilling pre-2024 orders into bronze — Compliance asked for it but Order Management's archive is on tape. Tracked: JIRA `ORD-1842`.
- The `region` field is inferred from `billing_address.country` and is wrong for ~3% of EU orders (regional vs country mismatch). Finance accepted; replacing it requires a source-system change.

## Related docs

- Design doc: [Confluence — Orders Ingest v3](#)
- Runbook: sibling `RUNBOOK.md`
- Privacy review: [Confluence — Orders PII Handling 2025-Q1](#)
- Slack: #data-platform-oncall
