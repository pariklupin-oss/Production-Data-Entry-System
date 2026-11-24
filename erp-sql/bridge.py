"""Isolated ERP bridge protocol. No network calls or live ERP imports.

The adapter must verify a unique ERP lot receipt, not merely a submit toast.
The journal survives restart and blocks a second submit after an uncertain result.
Use one shared journal on the factory machine; cross-machine SQL claims are pending.
"""
import json
import sqlite3

class ReconcileRequired(RuntimeError):
    pass

class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT)')

    def claim(self, row):
        payload = json.dumps(row['data'], sort_keys=True, separators=(',', ':'))
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prior = self.db.execute('SELECT revision,payload,state,receipt FROM attempts WHERE id=?', (row['row_id'],)).fetchone()
            if prior:
                if prior[0] != row['revision'] or prior[1] != payload:
                    raise ReconcileRequired('Entry changed after ERP attempt; reconcile before another submission')
                result = (False, prior[2], json.loads(prior[3]) if prior[3] else None)
            else:
                self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,NULL)', (row['row_id'], row['revision'], payload, 'submitting'))
                result = (True, 'submitting', None)
            self.db.execute('COMMIT')
            return result
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def receipt(self, row_id, receipt):
        self.db.execute('UPDATE attempts SET state=?,receipt=? WHERE id=?', ('confirmed', json.dumps(receipt, sort_keys=True), row_id))

    def ack(self, row_id):
        self.db.execute('UPDATE attempts SET state=? WHERE id=?', ('acknowledged', row_id))

    def close(self):
        self.db.close()


def execute(row, journal, erp, sql):
    """erp.submit(row), erp.verify(row) -> receipt|None; sql.ack(row,receipt).

    sql.ack must atomically compare revision, verify the receipt mapping and be
    idempotent. Automatic finishing enqueue follows acknowledgement separately.
    No adapter is shipped for actual ERP writes yet.
    """
    data = row['data']
    if row.get('erp_closed') or 'TEST ONLY' in str(data.get('Remarks', '')).upper():
        return 'excluded'
    if str(data.get('ERP Status', '')).lower() not in ('pending', 'override'):
        return 'excluded'
    if not all(str(data.get(k, '')).strip() for k in ('WO No', 'JC No', 'PP Code', 'Production Date', 'Start Time', 'End Time')):
        raise ValueError('Complete job identity and timing required')
    q = data.get('Production Qty')
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q <= 0 or int(q) != q:
        raise ValueError('Positive integer production required')
    fresh, state, receipt = journal.claim(row)
    if state == 'acknowledged':
        return 'already_acknowledged'
    if fresh:
        # Journal is committed BEFORE the first possible ERP side effect.
        # Any exception means verify-only on the next call, never blind resubmit.
        erp.submit(row)
    if receipt is None:
        receipt = erp.verify(row)
        if not receipt:
            raise ReconcileRequired('ERP result uncertain; inspect ERP, do not resubmit')
        expected = {'source_id': row['row_id'], 'wo': data['WO No'], 'jc': data['JC No'], 'pp': data['PP Code'], 'quantity': q}
        if any(receipt.get(k) != v for k, v in expected.items()) or not receipt.get('erp_lot_id'):
            raise ReconcileRequired('ERP receipt does not match this exact source lot')
        journal.receipt(row['row_id'], receipt)
    sql.ack(row, receipt)
    journal.ack(row['row_id'])
    return 'acknowledged'
