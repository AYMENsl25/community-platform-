# ADR 0004: No online payments in the MVP

- Status: Accepted
- Date: 2026-07-11

## Decision

MVP registration methods are exactly `free` and `cash_organizer_confirmed`. Online payments and refunds are deferred. The MVP contains no checkout routes or UI, payment/provider tables, provider adapters, webhooks, reconciliation, disputes, refund flows, or provider selection.

Preserve only the registration-method boundary and external-adapter architecture so a later phase can add country-scoped payment support without changing club, event, capacity, or registration ownership.

## Consequences

Cash reservations expire according to event-country policy and release capacity for FIFO promotion. Any future payment work requires product-owner approval, a new bounded plan, legal/operational review, provider research, signed webhook and reconciliation design, idempotency, sandbox verification, and an ADR.
