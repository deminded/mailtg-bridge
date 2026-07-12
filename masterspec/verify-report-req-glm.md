<!-- GLM-4 independent blind verify, 2026-07-12; produced via z.ai, saved by Arête (GLM lacked write perm) -->

# Verification Report: mailtg-bridge Requirements Layer

## Verifier
- Verifier: GLM-4 (independent blind verifier)
- Method: masterspec verification (axes O0-O7)
- Date: 2026-07-12

## spec_ready Verdict
**NO** — not ready for design layer without addressing critical and major defects.

---

## Critical Defects (Blocking)

### CRIT-001: FloodWait Not Handled
**Artifact:** `fn-dm-batch-to-email.md`, `fn-channel-update-to-email.md`  
**What:** Telegram FloodWait exception not in exception flows  
**Why:** Bridge will loop in skip cycle without exponential backoff  
**Axis:** O5-NEG (unhandled edge states)  
**Recommendation:** Add `Telegram FloodWait → exponential backoff, next cycle no sooner than N seconds, log`

### CRIT-002: Session Revoked State Missing
**Artifact:** `fn-first-run-setup.md`, `cdm-bridge.md`  
**What:** No persistent "session invalid" state in CDM  
**Why:** Service signals error, then polling continues → loops on same error  
**Axis:** O5-NEG (edge states, unhandled refusals)  
**Recommendation:** Add state "session invalid" to CDM; service stops polling until re-init

### CRIT-003: Auth Trust Fragmented
**Artifact:** `rules-control.md`, `fn-email-reply-to-tg.md`, `fn-bridge-control-by-email.md`  
**What:** Trust predicate split across 3 places, incomplete  
**Why:** `fn-email-reply-to-tg` AC-04 only checks "sender ≠ U" → doesn't require in-reply-to. Replay attack not handled. Token validation AC missing.  
**Axis:** O1 (static coherence), O5-NEG (unhandled edge cases)  
**Recommendation:** Centralize trust predicate; add AC for token validation failure

### CRIT-004: Media Threshold Undefined
**Artifact:** `fn-media-in-email.md`, `rules-delivery.md`  
**What:** "Attachment threshold configurable" but no default or range  
**Why:** Edge cases: threshold=0? threshold > max email size? 50+ large files?  
**Axis:** O2 (completeness), O5-NEG (unhandled edge cases)  
**Recommendation:** Specify default threshold, max limit, behavior when batch exceeds email size limit

---

## Major Defects (8)

| ID | Artifact | What | Axis |
|---|---|---|---|
| MAJOR-001 | rules-delivery.md, fn-dm-batch-to-email.md AC-05 | Private DM "best-effort tg://" undefined | O1, O5-NEG |
| MAJOR-002 | rules-delivery.md | Topic link format not specified | O2 |
| MAJOR-003 | rules-integrity.md, cdm-bridge.md | Antiloop detection method missing | O2 |
| MAJOR-004 | cdm-bridge.md invariants | Cursor write failure not handled | O5-NEG |
| MAJOR-005 | fn-media-in-email.md | Email size limit not specified | O2, O5-NEG |
| MAJOR-006 | cdm-bridge.md | Ledger purge policy missing | O2, O5-NEG |
| MAJOR-007 | All functions | Concurrent access not specified | O5-NEG |
| MAJOR-008 | fn-bridge-control-by-email.md | Token validation AC missing | O1, O2 |

---

## Minor Defects (5)

| ID | Artifact | What | Axis |
|---|---|---|---|
| MINOR-001 | cdm-bridge.md line 136 | Anti-loop comment confusing | O1, O5-NEG |
| MINOR-002 | nfr-operability.md | NFR-OPS-03 not testable (no default interval) | O2, O3 |
| MINOR-003 | 00-glossary.md | Deep link definition too narrow | O1, O0 |
| MINOR-004 | adr-001-python-core-reuse.md | Existing Python core not referenced | O4 |
| MINOR-005 | tc-acc-dm-delivery.md | AC-04 coverage gap | O1, O3 |

---

## O-5: Negative Axis - What derive/evolve Missed

**derive missed:**
- FloodWait handling (Telegram specific)
- Session lifecycle beyond "invalid → signal"
- Media/email size limits interaction
- Ledger growth management
- Concurrency model

**evolve missed:**
- Trust predicate centralization
- Topic link format (deep-link evolved for DM but not topic)
- Antiloop detection mechanism (concept evolved but method not specified)

---

## Summary

**Total defects:** 20 (4 critical, 8 major, 8 minor)

**Blockers for spec_ready:** CRIT-001 through CRIT-004 MUST be addressed

**Strongest areas:** Link structure, glossary, NFR specification, guardrail fold annotations

**Weakest areas:** Exception handling, edge cases, auth model centralization

---

## Guardrail Conformance

Guardrail fold annotations present:
- `tc-acc-antiloop-dedup.md`: "exceptions-first: terminal states marked"
- `tc-acc-bridge-control.md`: "exceptions-first: untrusted sender → named observable outcome"
- `tc-acc-deploy-and-security.md`: "formality-profile: explicit C-trigger check"

Guardrails followed for exception patterns, but edge cases (FloodWait, session revoked) not fully specified.

---
