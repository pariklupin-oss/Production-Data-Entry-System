# SQL finishing worker core — staged only

This is a new isolated adapter core; it does not modify or run the live ERP watcher.
Run `python -m unittest discover -s . -v` in this folder.

`finishing.py` decides the next automatic lot from confirmed SQL records. It excludes TEST ONLY and closed jobs, requires unambiguous WO+JC+PP route identity, and propagates the actual partial lot. Existing links make retries no-ops; source revisions and legacy unlinked ERP output require reconciliation.
`05_finishing_queue.sql` is a staged transactional enqueue RPC for the private service worker. Its unique source-ID/target-PP mapping and transaction lock prevent duplicate lot insertion. It queues Pending SQL rows; it never declares ERP success. Authenticated mobile operators cannot call this RPC.

Example: source lots 600 and 400 produce Strapping lots 600 and 400. Only after each Strapping ERP acknowledgement can its matching OQC lot be created. An unchanged repeat does not add another lot. Source identity is not inferred from equal quantities or timestamps.

Still pending: execute and test SQL migration in the test project, a durable ERP claim/lease and acknowledgement RPC, an ERP intake/closure adapter, connecting the existing local Selenium submit functions without publishing credentials, current one-month seed/delta, and end-to-end factory-machine tests. SQL is not installed by committing this folder. Do not run an additional ERP submit watcher beside the existing live watcher.

## Durable attempt protocol

`bridge.py` adds a local SQLite WAL journal and injected ERP/SQL adapter contracts. An attempt is committed before a possible ERP side effect. Restart or timeout causes verify-only recovery; no blind second submission. A unique ERP lot receipt must match source row, WO, JC, PP and quantity before SQL acknowledgement. SQL acknowledgement failure retries acknowledgement without re-submitting ERP. Closed and TEST ONLY entries are excluded. Thirteen offline tests pass across bridge and finishing logic.

This is a protocol core, not a working ERP connector. The real ERP read/submit adapter and idempotent revision-aware SQL acknowledgement RPC remain unimplemented. A single shared journal protects workers on one machine only; distributed SQL claims and coordination with the existing live watcher remain required before deployment. No secret, credential, live ERP invocation or factory installation is included.
