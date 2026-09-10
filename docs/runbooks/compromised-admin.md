# Respond to a compromised admin or session

1. Treat suspected admin compromise as high severity. Disable the account or MFA factor, revoke every session family, freeze sensitive operations if needed, and preserve immutable audit evidence.
2. Rotate affected credentials and provider tokens through their owners. Do not paste old or new values into logs, issues, pull requests, or chat.
3. Review protected actions by request ID, trace ID, target, reason, and safe before/after data. Check moderation, policy, feature-flag, outbox-retry, and audit-access activity.
4. Reverse harmful application changes through normal audited actions; never mutate audit or registration history directly.
5. Require verified identity, password reset, fresh MFA enrollment, and security-owner approval before restoring access. Record scope, timeline, notifications, and follow-up controls.
