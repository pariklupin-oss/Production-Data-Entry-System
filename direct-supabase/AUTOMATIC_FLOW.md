# Automatic downstream stages — confirmed rules

Pending: only eligible manual entry processes. Strapping Bundling and Outward Quality Check never appear for operator entry.
All Jobs: show every process belonging to the visible job card, including automatic pending, partial and submitted stages; automatic stages are read-only.
Submitted: show automatic stages only after ERP acknowledgement, read-only.
Partial: show automatic stages whose upstream partial lot has been successfully entered in ERP; automatic stages remain read-only.
Authoritative ERP Work Order/Job Card closure hides all related mobile records regardless of process or status. Records remain in SQL.

For each manual partial lot, propagate its actual output quantity to the following Strapping and OQC stages in ERP route order. Example: plan 1000, lots 600 then 400 => each downstream stage has matching lots 600 and 400, cumulative production 1000. Do not substitute plan quantity for actual output or copy cumulative quantity twice.
Each automatic lot needs an immutable source Row ID/lot key plus destination PP/process identity. Retries must reuse the same identity. A job card can have multiple manual and automatic lots; never match by JC number alone.
Only a confirmed predecessor ERP entry may enqueue its next automatic stage. OQC follows confirmed Strapping. Failed or uncertain ERP submissions remain pending/reconciliation until verified; do not label them Submitted early. Submitted vs Partial must preserve the actual cumulative completion and ERP status.

Current implementation: UI visibility/read-only behavior and SQL operator-write denial. Automatic lot propagation, ERP acknowledgement and aggregate completion are pending ERP worker implementation and tests. The full pipeline is not enabled by this PR.
