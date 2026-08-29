# Google Ads API Read and Reporting Reference

Load this file only for API-mode authentication checks, queries, and read-only reports. Load `mutation-workflow.md` separately only after the user explicitly requests an account change.

## Compatibility Check

The examples are version-neutral and were reviewed on 2026-08-29 against the then-current Google Ads API v25.1 documentation and Python client patterns.

Before modifying code or publishing:

1. Check the official [release notes](https://developers.google.com/google-ads/api/docs/release-notes) and [upgrade guide](https://developers.google.com/google-ads/api/docs/upgrade).
2. Confirm the installed `google-ads` client supports a currently available API version.
3. Prefer the client default. Specify a version only when a tested compatibility constraint requires it.
4. Re-run offline contract tests and a read-only test-account query.

## Authentication Safety

API mode requires a developer token, OAuth client credentials, a refresh token, and the intended customer context. These must already exist in protected local configuration or environment-backed secret storage.

Never:

- ask the user to paste a secret into chat;
- display a credential file;
- print environment-variable values;
- print a refresh or access token from an OAuth helper;
- commit a credential file or downloaded OAuth client secret;
- send a credential file through email, chat, or an artifact upload.

Safe readiness checks:

```bash
python3 -c "from google.ads.googleads.client import GoogleAdsClient; print('google-ads client available')"
test -r "$HOME/.google-ads.yaml" && echo "Google Ads config file is readable"
```

If authentication is missing, direct the user to Google's official OAuth setup and credential-security documentation. Let the user complete the interactive authorization locally. Verify only whether a harmless read request succeeds.

Use a secret manager when possible. If a local configuration file is used, restrict its permissions and keep it outside the repository.

## Initialize a Read-Only Client

```python
import os

from google.ads.googleads.client import GoogleAdsClient


def load_client():
    config_path = os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH")
    if config_path:
        return GoogleAdsClient.load_from_storage(path=config_path)
    return GoogleAdsClient.load_from_storage()


client = load_client()
google_ads_service = client.get_service("GoogleAdsService")
```

Do not log the client configuration. Keep customer IDs out of public reports; use a user-confirmed ID supplied through local configuration or a protected runtime input.

## Read-Only Query Pattern

Confirm customer identity, date range, timezone, and requested fields before querying.

```python
def campaign_performance(google_ads_service, customer_id):
    query = """
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign_budget.amount_micros,
          metrics.impressions,
          metrics.clicks,
          metrics.cost_micros,
          metrics.conversions,
          metrics.conversions_value
        FROM campaign
        WHERE segments.date DURING LAST_30_DAYS
          AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
    """
    return google_ads_service.search(customer_id=customer_id, query=query)
```

Keep reporting queries separate from mutation code. Select only fields needed for the question, page through the complete response, and retain the API request ID in diagnostic logs without exposing account data.

## Investigation Queries

### Candidate Keywords or Search Terms

Use spend and zero recorded conversions only to identify candidates for investigation. Before recommending action, examine match type, search terms, negatives, conversion lag, primary actions, attribution, geography, and sample size.

```sql
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  ad_group_criterion.criterion_id,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM keyword_view
WHERE segments.date DURING LAST_90_DAYS
  AND ad_group_criterion.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
```

Apply spend or volume thresholds only after the user supplies an account-appropriate threshold or the analysis derives and explains one.

### Conversion Configuration

Query conversion-action configuration and metrics in compatible views. Distinguish primary and secondary actions and document any attribution or import delays before concluding that tracking is broken.

## Error and Quota Handling

Catch `GoogleAdsException` and report only safe diagnostics:

- request ID;
- error code and message;
- affected field path;
- retryability;
- whether any requested page was not retrieved.

Never include authorization headers, tokens, credential objects, or raw configuration in errors.

For retryable quota or transient failures, use bounded exponential backoff with jitter and honor provider guidance. Do not describe queries as unlimited. Consult the current [API limits and quotas](https://developers.google.com/google-ads/api/docs/best-practices/quotas) before batch work.

## Reporting Checklist

- Confirmed customer and manager context
- Confirmed date range and timezone
- Stated business goal and primary conversion actions
- Complete pagination or explicitly disclosed truncation
- Separated observations from interpretations
- Redacted customer IDs and sensitive search terms where appropriate
- No mutation service called

If the user later requests a change, return to `SKILL.md` and load `mutation-workflow.md`; do not improvise a write from these read examples.
