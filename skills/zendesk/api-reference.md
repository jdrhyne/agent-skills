# Zendesk API Reference

## Authentication

All requests require:
```bash
AUTH="$EMAIL/token:$API_TOKEN"
BASE="https://$SUBDOMAIN.zendesk.com/api/v2"
```

## Tickets

### List Tickets
```bash
curl -u "$AUTH" "$BASE/tickets.json"
```

### Get Single Ticket
```bash
curl -u "$AUTH" "$BASE/tickets/$ID.json"
```

### Create Ticket
```bash
curl -X POST "$BASE/tickets.json" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket": {
      "subject": "Subject line",
      "comment": {"body": "Description"},
      "priority": "normal",
      "type": "problem",
      "tags": ["tag1", "tag2"],
      "requester": {"email": "user@example.com"}
    }
  }'
```

### Update Ticket
```bash
curl -X PUT "$BASE/tickets/$ID.json" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket": {
      "status": "solved",
      "comment": {
        "body": "Resolution message",
        "public": true
      }
    }
  }'
```

### Add Internal Note
```bash
curl -X PUT "$BASE/tickets/$ID.json" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket": {
      "comment": {
        "body": "Internal note content",
        "public": false
      }
    }
  }'
```

### Bulk Update
```bash
curl -X PUT "$BASE/tickets/update_many.json?ids=1,2,3" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"ticket": {"status": "solved"}}'
```

## Search

### Search Tickets
```bash
# By status
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+status:open"

# By assignee
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+assignee:me"

# By date range
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+created>2024-01-01"

# By priority
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+priority:urgent"

# Combined
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+status:open+priority:urgent+assignee:me"
```

### Search Operators
| Operator | Example | Meaning |
|----------|---------|---------|
| `:` | `status:open` | Equals |
| `>` | `created>2024-01-01` | Greater than |
| `<` | `updated<2024-01-01` | Less than |
| `>=` | `priority>=high` | Greater or equal |
| `-` | `-status:closed` | Not |

## Users

### Get Current User
```bash
curl -u "$AUTH" "$BASE/users/me.json"
```

### Search Users
```bash
curl -u "$AUTH" "$BASE/users/search.json?query=email:user@example.com"
```

### Create User
```bash
curl -X POST "$BASE/users.json" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "name": "User Name",
      "email": "user@example.com",
      "role": "end-user"
    }
  }'
```

### List User Tickets
```bash
curl -u "$AUTH" "$BASE/users/$USER_ID/tickets/requested.json"
```

## Organizations

### List Organizations
```bash
curl -u "$AUTH" "$BASE/organizations.json"
```

### Get Organization Tickets
```bash
curl -u "$AUTH" "$BASE/organizations/$ORG_ID/tickets.json"
```

## Views

### List Views
```bash
curl -u "$AUTH" "$BASE/views.json"
```

### Get Tickets in View
```bash
curl -u "$AUTH" "$BASE/views/$VIEW_ID/tickets.json"
```

### Count Tickets in View
```bash
curl -u "$AUTH" "$BASE/views/$VIEW_ID/count.json"
```

## Macros

### List Macros
```bash
curl -u "$AUTH" "$BASE/macros.json"
```

### Apply Macro
```bash
curl -X PUT "$BASE/tickets/$ID.json" -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"ticket": {"macro_ids": [12345]}}'
```

## Metrics

### Ticket Metrics
```bash
curl -u "$AUTH" "$BASE/ticket_metrics.json"
```

### Get Specific Ticket Metrics
```bash
curl -u "$AUTH" "$BASE/tickets/$ID/metrics.json"
```

## Pagination

All list endpoints return max 100 results. Check `next_page`:
```json
{
  "tickets": [...],
  "next_page": "https://xxx.zendesk.com/api/v2/tickets.json?page=2",
  "count": 250
}
```

Loop until `next_page` is null:
```bash
while [ -n "$NEXT" ]; do
  curl -u "$AUTH" "$NEXT" > page.json
  NEXT=$(jq -r '.next_page // empty' page.json)
done
```

## Rate Limits

| Plan | Limit |
|------|-------|
| Enterprise | 700/min |
| Professional | 400/min |
| Team | 200/min |

Check headers:
- `X-Rate-Limit`: Your limit
- `X-Rate-Limit-Remaining`: Requests left
- `Retry-After`: Seconds to wait if limited
