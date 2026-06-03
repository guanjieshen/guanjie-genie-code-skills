---
name: data-exploration
description: Use when exploring or discovering data in Databricks — finding tables by keyword via information_schema, discovering schemas with the databricks aitools CLI, executing SQL against a SQL warehouse, or running data quality and validation checks. Triggers on phrases like "show me tables", "find tables containing", "discover schema for", "explore", "what columns are in", "query this table", or any catalog/schema/table exploration request.
tags: [data-exploration, sql, schema-discovery, unity-catalog]
owners: [data-platform-team]
---

# Data Exploration

Tools for discovering table schemas and executing SQL queries in Databricks.

## Finding Tables by Keyword

**⚠️ START HERE if you don't know which catalog/schema contains your data.**

Use `information_schema` to search for tables by keyword — do NOT manually iterate through `catalogs list` → `schemas list` → `tables list`. Manual enumeration wastes 10+ steps.

```bash
# Find tables matching a keyword
databricks experimental aitools tools query \
  "SELECT table_catalog, table_schema, table_name FROM system.information_schema.tables WHERE table_name LIKE '%keyword%'" \
  --profile <PROFILE>

# Then discover schema for the tables you found
databricks experimental aitools tools discover-schema catalog.schema.table1 catalog.schema.table2 --profile <PROFILE>
```

## Overview

The `databricks experimental aitools tools` command group provides tools for data discovery and exploration:
- **discover-schema**: Batch discover table metadata, columns, types, sample data, and statistics
- **query**: Execute SQL queries against Databricks SQL warehouses

**When to use this**: Use these commands whenever you need to:
- Discover table schemas and metadata
- Execute SQL queries against warehouse data
- Explore data structure and content
- Validate data or check table statistics

## Prerequisites

1. **Authenticated Databricks CLI** — OAuth2 setup and profile configuration
2. **Access to Unity Catalog tables** with appropriate read permissions
3. **SQL Warehouse** (for query command — auto-detected unless `DATABRICKS_WAREHOUSE_ID` is set)

## Discover Schema

Batch discover table metadata including columns, types, sample data, and null counts.

### Command Syntax

```bash
databricks experimental aitools tools discover-schema TABLE... [flags]
```

Tables must be specified in **CATALOG.SCHEMA.TABLE** format.

### What It Returns

For each table, returns:
- Column names and types
- Sample data (5 rows)
- Null counts per column
- Total row count

### Examples

```bash
# Discover schema for a single table
databricks experimental aitools tools discover-schema samples.nyctaxi.trips --profile my-workspace

# Discover schema for multiple tables
databricks experimental aitools tools discover-schema \
  catalog.schema.table1 \
  catalog.schema.table2 \
  --profile my-workspace

# Get JSON output
databricks experimental aitools tools discover-schema \
  samples.nyctaxi.trips \
  --output json \
  --profile my-workspace
```

### Common Use Cases

1. **Understanding table structure before querying**
   ```bash
   databricks experimental aitools tools discover-schema catalog.schema.customer_data --profile my-workspace
   ```

2. **Comparing schemas across multiple tables**
   ```bash
   databricks experimental aitools tools discover-schema \
     catalog.schema.table_v1 \
     catalog.schema.table_v2 \
     --profile my-workspace
   ```

3. **Identifying columns with null values**
   - The null counts help identify data quality issues

## Query

Execute SQL statements against a Databricks SQL warehouse and return results.

### Command Syntax

```bash
databricks experimental aitools tools query "SQL" [flags]
```

### Warehouse Selection

The command **auto-detects** an available warehouse unless:
- `DATABRICKS_WAREHOUSE_ID` environment variable is set
- You specify a warehouse using other configuration methods

To check which warehouse will be used:
```bash
databricks experimental aitools tools get-default-warehouse --profile my-workspace
```

### Output

Returns:
- Query results as JSON
- Row count
- Execution metadata

### Examples

```bash
# Simple SELECT query
databricks experimental aitools tools query \
  "SELECT * FROM samples.nyctaxi.trips LIMIT 5" \
  --profile my-workspace

# Aggregation query
databricks experimental aitools tools query \
  "SELECT vendor_id, COUNT(*) as trip_count FROM samples.nyctaxi.trips GROUP BY vendor_id" \
  --profile my-workspace

# With JSON output
databricks experimental aitools tools query \
  "SELECT * FROM catalog.schema.table WHERE date > '2024-01-01'" \
  --output json \
  --profile my-workspace

# Using specific warehouse
DATABRICKS_WAREHOUSE_ID=abc123 databricks experimental aitools tools query \
  "SELECT * FROM samples.nyctaxi.trips LIMIT 10" \
  --profile my-workspace
```

### Common Use Cases

1. **Exploratory data analysis**
   ```bash
   databricks experimental aitools tools query \
     "SELECT COUNT(*) FROM catalog.schema.table" \
     --profile my-workspace
   ```

2. **Data validation**
   ```bash
   databricks experimental aitools tools query \
     "SELECT COUNT(*) FROM catalog.schema.table WHERE column IS NULL" \
     --profile my-workspace
   ```

3. **Quick analytics**
   ```bash
   databricks experimental aitools tools query \
     "SELECT category, COUNT(*), AVG(value) FROM catalog.schema.table GROUP BY category" \
     --profile my-workspace
   ```

## Workflow: Complete Data Exploration

```bash
# 1. Discover the schema first
databricks experimental aitools tools discover-schema \
  samples.nyctaxi.trips \
  --profile my-workspace

# 2. Based on discovered columns, run targeted queries
databricks experimental aitools tools query \
  "SELECT vendor_id, payment_type, COUNT(*) as trips, AVG(fare_amount) as avg_fare
   FROM samples.nyctaxi.trips
   GROUP BY vendor_id, payment_type
   ORDER BY trips DESC
   LIMIT 10" \
  --profile my-workspace
```

## Genie Code-Specific Tips

Each Bash command in Genie Code runs in a separate shell:

```bash
# ✅ RECOMMENDED: Use --profile flag
databricks experimental aitools tools discover-schema samples.nyctaxi.trips --profile my-workspace

# ✅ ALTERNATIVE: Chain with &&
export DATABRICKS_CONFIG_PROFILE=my-workspace && \
  databricks experimental aitools tools query "SELECT * FROM samples.nyctaxi.trips LIMIT 5"

# ❌ DOES NOT WORK: Separate export
export DATABRICKS_CONFIG_PROFILE=my-workspace
databricks experimental aitools tools query "SELECT * FROM samples.nyctaxi.trips LIMIT 5"
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--profile` | Profile name from ~/.databrickscfg | Default profile |
| `--output` | Output format: `text` or `json` | `text` |
| `--debug` | Enable debug logging | `false` |
| `--target` | Bundle target to use (if applicable) | - |

## Troubleshooting

### Table Not Found

**Symptom**: `Error: TABLE_OR_VIEW_NOT_FOUND`

**Solution**:
1. Verify table name format: `CATALOG.SCHEMA.TABLE`
2. Check read permissions on the table
3. List available tables: `databricks tables list <catalog> <schema> --profile my-workspace`

### Warehouse Not Available

**Symptom**: `Error: No available SQL warehouse found`

**Solution**:
1. Check default: `databricks experimental aitools tools get-default-warehouse --profile my-workspace`
2. List warehouses: `databricks warehouses list --profile my-workspace`
3. Set explicit: `DATABRICKS_WAREHOUSE_ID=<id> ...`
4. Start stopped: `databricks warehouses start --id <id> --profile my-workspace`

### Permission Denied

**Symptom**: `Error: PERMISSION_DENIED`

**Solution**:
1. Check grants: `databricks grants get --full-name catalog.schema.table --principal <user-email> --profile my-workspace`
2. Request SELECT permission from your workspace administrator
3. Verify warehouse USAGE permission

### SQL Syntax Error

**Symptom**: `Error: PARSE_SYNTAX_ERROR`

**Solution**:
1. Use standard SQL
2. Verify column names with `discover-schema` first
3. Quote string literals properly
4. Test incrementally

## Best Practices

1. **Always discover schema first** — use `discover-schema` before complex queries.
2. **Use LIMIT for exploration** on large tables to avoid long-running queries.
3. **JSON output for parsing** — `--output json | jq` for programmatic use.
4. **Check table existence** before querying: `databricks tables get --full-name catalog.schema.table`.
5. **Always specify `--profile`** in Genie Code to avoid authentication issues.

## Attribution

Seeded from [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-core/data-exploration.md). Frontmatter added for Genie Code workspace deployment.
