# Salesforce Skill

Query and manage Salesforce orgs via the official Salesforce MCP server or SF CLI.

## What This Skill Does

Gives your AI agent the ability to:
- Run SOQL queries against your Salesforce org
- Understand your org's object model and business logic
- Pull pipeline, revenue, customer, and deal data
- Write accurate queries using your custom fields

## Setup

### 1. Install Salesforce CLI
```bash
npm install -g @salesforce/cli
```

### 2. Authenticate Your Org
```bash
sf org login web --alias my-prod
```

### 3. (Optional) Install Salesforce MCP Server
```bash
# See https://github.com/salesforce/mcp
```

### 4. Customize the Skill

1. Edit `SKILL.md` — Update connection info, product lines, and custom fields
2. Fill in `SALESFORCE_STRUCTURE.md` — Document your org's objects, fields, and business logic

The more context you provide in these files, the better the AI will understand your Salesforce data.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill instructions, queries, and commands |
| `SALESFORCE_STRUCTURE.md` | Template for documenting your org's structure |
| `README.md` | This file |

## Example Queries

```sql
-- Pipeline by stage
SELECT StageName, COUNT(Id), SUM(Amount)
FROM Opportunity
WHERE IsClosed = false
GROUP BY StageName

-- Top accounts by ARR
SELECT Account.Name, SUM(ARR__c)
FROM Opportunity
WHERE StageName = 'Closed Won'
GROUP BY Account.Name
ORDER BY SUM(ARR__c) DESC
LIMIT 20

-- Renewals due this quarter
SELECT Id, Name, Amount, CloseDate, Account.Name
FROM Opportunity
WHERE RecordType.Name = 'Renewal'
  AND IsClosed = false
  AND CloseDate = THIS_QUARTER
```

## Extending

Add your own reference docs:
- `BUSINESS_LOGIC.md` — Deal flow, approval processes, automation rules
- `COMMON_QUERIES.md` — Frequently used queries for your team
- `INTEGRATIONS.md` — How Salesforce connects to other systems
