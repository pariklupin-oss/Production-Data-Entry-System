# Direct Production Planning — isolated test

Target: https://axgyeppfrcmhwrpxztvv.supabase.co (pariklupin account).
This route uses Supabase Auth and REST directly. No Apps Script, iframe, or automatic reload.
Live root index.html and the floor ERP watcher are unchanged.

## Setup still required
1. Install the existing isolated test table and private mutation RPC if absent. Then execute 03_auth.sql in the target project SQL editor once. Policies intentionally fail on repeat installation rather than silently overwriting unknown policies.
2. Create a password test user in Supabase Authentication, then explicitly enable its UUID in planning_direct_members (example at SQL file bottom). Do not share passwords in chat. Operators may save/extend; override requires admin.
3. Set config.js to THIS project's sb_publishable_ key. Never use a secret or service-role key. The provided old project key is deliberately excluded.
4. Serve this folder over HTTP / isolated GitHub Pages preview. Opening HTML via file:// will not work with modules. No live deployment is included.
5. Test login rejection, two-operator revision conflict, retry after lost response, Extend, reload draft recovery, logout and separate-account drafts. Verify SQL rows independently.

Only Production Planning is enabled. Boardline/Production reports remain disabled pending their server validation. SQL API grants no report writes. Existing test records and TEST ONLY remarks must stay out of live ERP.
The job list retains recent closed records for one calendar month, excluding closed jobs. Historical SQL rows are not deleted. A fresh last-month import/delta and ERP SQL worker are still required before cutover.

Browser syntax and fake-REST adapter tests do not replace SQL execution and authenticated end-to-end tests. Database installation has not been performed by this change.

ERP intake/status worker must set erp_closed=true for every row belonging to a closed ERP Work Order or Job Card, and increment revision atomically. It must refresh statuses before mobile rollout; defaults are not proof of ERP open status. Closed records remain in SQL. Pending older jobs are outside the new one-month mobile window.

## Verified setup on 10 October 2026
Staged access SQL was applied in axgyeppfrcmhwrpxztvv with owner approval. SQL verification confirms RLS enabled, anonymous mutation denied and direct authenticated UPDATE denied. Two owner-approved test memberships are enabled: one admin and one operator. The owner-provided publishable key is configured. Browser login/save end-to-end verification and ERP adapters remain pending. This folder may be published as a separate test route; the root live app is unchanged.
