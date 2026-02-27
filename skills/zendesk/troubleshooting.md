# Troubleshooting — Zendesk

## Authentication Errors

### 401 Unauthorized
**Cause:** Invalid credentials format or inactive token.

**Fix:**
1. Verify email is correct
2. Ensure format is `email/token:TOKEN` (not just token)
3. Check token is active in Admin > Channels > API
4. Ensure API access is enabled for the account

```bash
# Correct format
curl -u "admin@company.com/token:abcd1234" "$BASE/users/me.json"

# Wrong - missing /token
curl -u "admin@company.com:abcd1234" "$BASE/users/me.json"
```

### 403 Forbidden
**Cause:** User doesn't have permission for this operation.

**Fix:**
1. Check user role (Admin, Agent, End-user)
2. Some endpoints require Admin
3. Check if IP restrictions are enabled

## Search Issues

### Empty Results for Valid Queries
**Cause:** Special characters not encoded.

**Fix:**
```bash
# Wrong
curl "$BASE/search.json?query=subject:user@email.com"

# Correct - URL encode
curl "$BASE/search.json?query=subject:user%40email.com"
```

### Search Returns Old Data
**Cause:** Search index updates are not instant.

**Fix:** Wait 1-2 minutes for index refresh. For real-time, use `/tickets/$ID.json` directly.

## Ticket Operations

### Cannot Update Ticket
**Cause:** Ticket is closed or merged.

**Fix:**
- Closed tickets cannot be updated. Create new ticket referencing the old one.
- Check `status` field first.

### Missing Fields in Response
**Cause:** Some fields require specific plans or custom field setup.

**Fix:**
- Standard fields available on all plans
- Custom fields need Admin setup
- Some metrics require Enterprise plan

### Ticket Creation Fails
**Cause:** Missing required fields or invalid values.

**Required fields:**
- `subject` (string)
- `comment.body` (string)

**Common validation errors:**
- `priority` must be: urgent, high, normal, low
- `status` must be: new, open, pending, hold, solved
- `type` must be: problem, incident, question, task

## Rate Limiting

### 429 Too Many Requests
**Cause:** Exceeded rate limit.

**Fix:**
```bash
# Check headers
curl -I -u "$AUTH" "$BASE/tickets.json"
# Look for: X-Rate-Limit-Remaining

# Add delays for bulk operations
for id in $IDS; do
  curl -X PUT "$BASE/tickets/$id.json" ...
  sleep 0.1  # 100ms delay
done
```

### Bulk Operations Failing Partially
**Cause:** Some tickets in batch have issues.

**Fix:** Check response for individual errors:
```json
{
  "job_status": {
    "results": [
      {"id": 1, "success": true},
      {"id": 2, "success": false, "error": "Ticket is closed"}
    ]
  }
}
```

## Pagination Issues

### Getting Duplicate Results
**Cause:** Data changed between page requests.

**Fix:** Use cursor-based pagination when available:
```bash
curl "$BASE/tickets.json?page[size]=100"
# Use the cursor from response for next page
```

### Missing Results
**Cause:** Default limit is 100, not checking `next_page`.

**Fix:**
```bash
NEXT="$BASE/tickets.json"
while [ -n "$NEXT" ]; do
  RESP=$(curl -s -u "$AUTH" "$NEXT")
  echo "$RESP" | jq '.tickets[]'
  NEXT=$(echo "$RESP" | jq -r '.next_page // empty')
done
```

## Connection Issues

### Timeout Errors
**Cause:** Network issues or heavy queries.

**Fix:**
- Add timeout: `curl --connect-timeout 10 --max-time 30`
- Reduce query scope
- Use pagination with smaller page size

### SSL Certificate Errors
**Cause:** Outdated CA certificates or proxy issues.

**Fix:**
```bash
# Update CA certs (macOS)
brew install ca-certificates

# If behind proxy, may need to add cert
curl --cacert /path/to/cert.pem ...
```

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Hardcoding subdomain | Fails for different accounts | Use variable |
| Not checking ticket status | Cannot update closed | Check before update |
| Ignoring pagination | Missing data | Loop until next_page null |
| No rate limit handling | 429 errors | Add delays, check headers |
| Plain password auth | Security risk | Always use API token |
