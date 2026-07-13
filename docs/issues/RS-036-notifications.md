# RS-036: Notification adapters and email

**Objective:** Deliver deduplicated policy-triggered notifications through an adapter framework, implementing email first.  
**Rationale:** Operators need timely action on critical findings and scan/connector failure.  
**Dependencies:** RS-033/035/037; OD-014.  
**Scope:** Channel/event models, critical/score/security/failure/stalled triggers, preferences, email adapter/templates, retry/dedup/audit/delivery state.  
**Out of scope:** Slack/Teams implementation (ports only), marketing email, raw evidence attachments.  
**Implementation guidance:** Evaluate policy after committed scan; stable event idempotency; link to authenticated detail; rate-limit/digest storms.  
**Security considerations:** No secrets/raw content/unsafe HTML; tenant recipients and verified addresses; webhook future signing; unsubscribe/preferences and anti-abuse.  
**Acceptance criteria:** Each trigger testable; duplicate events do not duplicate delivery; failures retry/dead-letter visibly; email accessible and minimized.  
**Tests:** Policy unit, adapter fake/integration, dedup/retry, template injection, tenant recipients, preference/rate-limit.  
**Documentation changes:** Notifications/privacy/operations.  
**Completion checklist:** [ ] Trigger policy [ ] Dedup tested [ ] Template security [ ] Delivery audit [ ] Docs updated

