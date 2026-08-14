# Beta monitoring contract

Talaqi emits newline-delimited JSON and derives metrics from bounded event names and labels. Request events contain only timestamp, event, method, route template, status code, duration, request ID, trace ID, and level. Query strings, path values, headers, cookies, bodies, exception messages, user IDs, emails, and venue data are forbidden. Incoming valid W3C trace IDs are continued; malformed values are replaced and `X-Trace-ID` is returned.

`apps/api/src/talaqi/telemetry.py` is the source of truth for metric names and label sets. Collection must reject extra labels. In particular, UUIDs, request/trace IDs, contact data, arbitrary error text, and deduplication keys must never become metric labels. Error reporting stores the safe error code, route template, release SHA, request ID, and trace ID only.

The beta dashboard must show API request/error/latency, database pool saturation, object-storage capacity, oldest outbox job and failures, email failures, registration transitions/expiry, waitlist promotions, moderation SLA breaches, and the region-level product funnel. `dashboard.json` records that reviewable contract; the deployment adapter maps these names to the selected provider.

`alerts.yml` defines the release alerts: user-impacting API outage, migration failure, stalled queue, database or storage capacity, critical email failure, and invariant violation. Page only on sustained user impact; route warnings to the operations channel with a runbook link. Do not place private values in alert annotations.

## Synthetic exercise

Run `python -m uv run pytest -q apps/api/tests/security/test_logging.py apps/api/tests/security/test_telemetry.py`. The exercise injects a firing sample for every alert and asserts all names fire, then supplies an empty healthy sample and asserts none fire. In staging, repeat after deployment by sending provider-side synthetic series with the same names, acknowledge each notification, record timestamps and screenshots in the release evidence, and remove the synthetic series. Provider delivery and paging cannot be certified by unit tests alone.

## Incident correlation

Start with a request ID from the user-safe error envelope, locate the matching `request.completed` event, then pivot on its trace ID. Use route templates and stable error classes for aggregation. Never search by raw email, token, free-text reason, exact address, or payload. Retain operational logs for the approved short beta window and apply the deletion schedule from the recovery/lifecycle runbook.
