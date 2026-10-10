# SQL finishing worker core — staged only

This is a new isolated adapter core; it does not modify or run the live ERP watcher.
Run `python -m unittest discover -s . -v` in this folder.

`finishing.py` decides the next automatic lot from confirmed SQL records. It excludes TEST ONLY and closed jobs, requires unambiguous WO+JC+PP route identity, and propagates the actual partial lot. Existing links make retries no-ops; source revisions and legacy unlinked ERP output require reconciliation.
`05_finishing_queue.sql` is a staged transactional enqueue RPC for the private service worker. Its unique source-ID/target-PP mapping and transaction lock prevent duplicate lot insertion. It queues Pending SQL rows; it never declares ERP success. Authenticated mobile operators cannot call this RPC.

Example: source lots 600 and 400 produce Strapping lots 600 and 400. Only after each Strapping ERP acknowledgement can its matching OQC lot be created. An unchanged repeat does not add another lot. Source identity is not inferred from equal quantities or timestamps.

Still pending: execute and test SQL migration in the test project, a durable ERP claim/lease and acknowledgement RPC, an ERP intake/closure adapter, connecting the existing local Selenium submit functions without publishing credentials, current one-month seed/delta, and end-to-end factory-machine tests. SQL is not installed by committing this folder. Do not run an additional ERP submit watcher beside the existing live watcher.
