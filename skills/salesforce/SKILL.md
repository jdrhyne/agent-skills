---
name: salesforce
description: Query and manage Salesforce orgs via the official Salesforce MCP server or SF CLI.
permissions:
  - credential_access: "Reads Salesforce CLI auth context for org access"
  - network: "HTTPS calls to Salesforce APIs via sf CLI or MCP server"
  - system_modification: "Requires npm install -g @salesforce/cli as prerequisite"
---

# Salesforce Skill

Query and manage your Salesforce org with full context of your business logic.

## Setup

### Prerequisites
1. **Salesforce CLI** installed: `npm install -g @salesforce/cli`
2. **Authenticated org**: `sf org login web --alias my-prod`
3. **MCP Server** (optional): [Salesforce MCP](https://github.com/salesforce/mcp) for tool-based access

### Configuration
Update the connection info below with your org details:

```yaml
Org Alias: my-prod
Username: your-user@company.com
Org ID: 00Dxxxxxxxxx
```

## Reference Documentation

**See [SALESFORCE_STRUCTURE.md](./SALESFORCE_STRUCTURE.md)** for a template covering:
- Object relationships and hierarchy
- Field definitions and API names
- Business logic (multi-year deals, renewals, usage-based pricing)
- Record types and their purposes
- Org-specific customizations

> **Tip:** Fill in `SALESFORCE_STRUCTURE.md` with your org's actual objects, fields, and business logic. The more context you provide, the better the AI can write queries and understand your data.

## Key Concepts (Customize These)

### Lines of Business
Update with your company's product lines:
- **Product A** — Description
- **Product B** — Description
- **Product C** — Description

### Opportunity Record Types
Common record types (adjust to your org):
- **New** — First-time purchase
- **Renewal** — Subscription continuation
- **Upsell** — Adding to existing subscription
- **Expansion** — Similar to upsell
- **Professional Services** — Services deals

### Critical Custom Fields
Document your key custom fields:
- **ACV** (Annual Contract Value) — API name: `ACV__c`
- **ARR** (Annual Recurring Revenue) — API name: `ARR__c`
- **TCV** (Total Contract Value) — API name: `TCV__c`
- **LOB** (Line of Business) — API name: `LOB__c`

## Quick Commands

### Run SOQL Query via MCP
```bash
mcporter call salesforce.run_soql_query \
  query="SELECT Id, Name FROM Account LIMIT 10" \
  usernameOrAlias="my-prod" \
  directory="$HOME"
```

### Run SOQL Query via SF CLI
```bash
sf data query \
  --query "SELECT Id, Name FROM Account LIMIT 5" \
  --target-org my-prod
```

### Common Queries

**Open opportunities by stage:**
```sql
SELECT Id, Name, StageName, Amount, CloseDate, Account.Name
FROM Opportunity
WHERE IsClosed = false
ORDER BY CloseDate
```

**Renewals closing this quarter:**
```sql
SELECT Id, Name, Amount, CloseDate, Account.Name
FROM Opportunity
WHERE RecordType.Name = 'Renewal'
  AND IsClosed = false
  AND CloseDate = THIS_QUARTER
ORDER BY CloseDate
```

**New deals by product line:**
```sql
SELECT LOB__c, COUNT(Id), SUM(Amount)
FROM Opportunity
WHERE RecordType.Name = 'New'
  AND StageName = 'Closed Won'
  AND CloseDate = THIS_YEAR
GROUP BY LOB__c
```

**ARR by Account (Top 20):**
```sql
SELECT Account.Name, SUM(ARR__c)
FROM Opportunity
WHERE StageName = 'Closed Won'
GROUP BY Account.Name
ORDER BY SUM(ARR__c) DESC
LIMIT 20
```

**Recent closed-won deals:**
```sql
SELECT Id, Name, Amount, CloseDate, Account.Name
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND CloseDate = LAST_N_DAYS:30
ORDER BY CloseDate DESC
```

**Account search:**
```sql
SELECT Id, Name, Industry, AnnualRevenue, Website
FROM Account
WHERE Name LIKE '%SearchTerm%'
```

**Contact lookup:**
```sql
SELECT Id, Name, Email, Title, Account.Name
FROM Contact
WHERE Email = 'user@example.com'
```

## MCP Tools Available

When using the Salesforce MCP server:
- `run_soql_query` — Run SOQL queries against your org
- `list_all_orgs` — List configured Salesforce orgs
- `open_org` — Open org in browser
- `get_username` — Resolve org username/alias

## Tips

### Writing Good SOQL
- Always include `Account.Name` in opportunity queries for context
- Use date literals: `TODAY`, `THIS_WEEK`, `THIS_QUARTER`, `THIS_YEAR`, `LAST_N_DAYS:30`
- Use `RecordType.Name` to filter by record type
- `LIMIT` your queries to avoid timeouts on large orgs
- Use `COUNT()` and `GROUP BY` for aggregations

### Common Patterns
- **Pipeline report:** Filter by `IsClosed = false` and group by `StageName`
- **Revenue analysis:** Sum `Amount` or `ACV__c` grouped by time period or product
- **Customer health:** Join Opportunities with Cases or custom health objects
- **Renewal tracking:** Filter `RecordType.Name = 'Renewal'` with `CloseDate` ranges

### Multi-Year Deal Handling
If your org uses multi-year deals:
- Track subscription start/end dates separately from contract end
- TCV (Total Contract Value) = full multi-year value
- ACV (Annual Contract Value) = annualized value
- Consider creating annual recognition events for revenue recognition

## Extending This Skill

Add your own reference docs alongside this SKILL.md:
- `SALESFORCE_STRUCTURE.md` — Your org's complete object/field documentation
- `BUSINESS_LOGIC.md` — How your org uses Salesforce (deal flow, approval processes)
- `COMMON_QUERIES.md` — Frequently used queries specific to your team
