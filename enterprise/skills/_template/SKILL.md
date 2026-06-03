---
name: my-skill
description: REPLACE THIS — one or two sentences describing what this skill does and when Genie should use it. The description is what Genie matches on, so be specific about the triggers (e.g. "Use when the user asks about revenue, ARR, or bookings — defines our metric formulas and which tables to use").
tags: []
owners: []
---

<!--
This is a TEMPLATE — it is not deployed (the `_template/` folder is skipped
by the inheritance walker). To create a new skill:
  1. Copy this folder: `cp -r enterprise/skills/_template enterprise/skills/my-real-skill`
  2. Update `name:` to match the new folder name.
  3. Replace the description and body.
-->


# Skill Title

Brief intro: what this skill teaches Genie and why it exists.

## When to use

- Trigger phrase / topic 1
- Trigger phrase / topic 2

## Instructions

Write the actual guidance here in plain language. Genie reads this as instructions, so be direct.

1. Step one
2. Step two
3. Step three

## Examples

**Good:**
```sql
-- example query that follows the rule
SELECT ...
```

**Bad:**
```sql
-- example of what NOT to do
SELECT ...
```

## Edge cases

- Case A → do X
- Case B → do Y

## References

Link to any supporting files in this folder (loaded on demand):

- [details.md](details.md)
