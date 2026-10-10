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
- Keep a current 15-calendar-day seed for Extend, plus older open jobs. Do not import the full History archive or delete old SQL records.

## Current state
The direct mobile Planning code and staged access SQL are implemented in this branch.
ERP intake adapter, ERP submission adapter, durable worker claims, fresh 15-day import,
correct project publishable key, database installation, and authenticated end-to-end testing remain pending.
The live floor app and its ERP watcher remain unchanged.
