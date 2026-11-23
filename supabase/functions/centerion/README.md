# Centerion Edge Function source mirror

This source mirrors deployed Centerion Edge Function v12 as audited on 2026-11-23, with the shared strict request guard applied for review.

- Platform JWT verification must remain enabled: `verify_jwt = true`.
- The handler still calls Supabase Auth `getUser()` and derives the user ID from the verified JWT.
- No request-body owner ID is accepted.
- No secrets or environment values are committed.
- The strict request reader enforces the 32 KB body limit on streamed UTF-8 bytes before full buffering.
- Oversized strings are rejected; they are no longer silently truncated.
- Rate limiting is still not implemented and remains a separate hardening task.\n- This branch is a review candidate only. It has not been deployed to Supabase production.
- The separate `kolai-bridge` function remains a security blocker because its deployed platform setting is `verify_jwt=false`; this PR does not change it.
