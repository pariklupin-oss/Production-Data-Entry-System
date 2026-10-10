# Confirmed production flow

ERP → Planning Job Cards → Supabase SQL → GitHub Mobile App → Supabase SQL → ERP Entry.

## Responsibilities
- ERP intake worker fetches job cards and upserts planning metadata into SQL using a stable ERP job/process identifier.
- Intake must not overwrite operator quantities, times, remarks or revision changes. No whole-table replacement.
- GitHub mobile app reads SQL jobs and saves entries directly to SQL using authenticated, revision-checked requests.
- ERP entry worker consumes eligible saved entries. It verifies ERP success before marking the same SQL record Submitted.
- Ambiguous ERP responses must be marked Check ERP and reconciled before retrying. No blind retry that could duplicate production.
- Workers run on the existing ERP-accessible machine. A durable claim/lease and acknowledgement are required before enabling a second worker or cutting over.
- TEST ONLY records are excluded from ERP submission.
- Keep a current one-calendar-month seed for Extend. Hide all ERP-closed Work Orders and Job Cards from the mobile app; retain their SQL records. ERP status worker must atomically stamp erp_closed on all matching rows and increment revision. Do not import the full History archive or delete old SQL records.

## Current state
The direct mobile Planning code and staged access SQL are implemented in this branch.
ERP intake adapter, ERP submission adapter, durable worker claims, fresh one-month import,
database installation, and authenticated end-to-end testing remain pending. The owner-provided publishable key is configured.
The live floor app and its ERP watcher remain unchanged.
