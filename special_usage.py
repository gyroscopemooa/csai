"""Isolated SQLite usage pilot; not the production credit ledger."""
import sqlite3
from contextlib import contextmanager


class UsageLedger:
    def __init__(self, path):
        self.path = path
        with self._tx() as db:
            db.execute('CREATE TABLE IF NOT EXISTS budget(ws TEXT, period TEXT, credits INTEGER NOT NULL, ceiling INTEGER NOT NULL, PRIMARY KEY(ws,period))')
            db.execute('CREATE TABLE IF NOT EXISTS usage(ws TEXT, period TEXT, job TEXT, credits INTEGER NOT NULL, estimate INTEGER NOT NULL, state TEXT NOT NULL, charged INTEGER, actual INTEGER, PRIMARY KEY(ws,period,job))')

    @contextmanager
    def _tx(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _scope(*values):
        if not all(isinstance(v, str) and 0 < len(v) <= 128 and v.strip() for v in values):
            raise ValueError('invalid scope')

    @staticmethod
    def _amounts(*values):
        if any(type(v) is not int or not 0 <= v <= 10**12 for v in values):
            raise ValueError('invalid amount')

    def provision(self, ws, period, credits, ceiling):
        self._scope(ws, period)
        self._amounts(credits, ceiling)
        with self._tx() as db:
            db.execute('INSERT INTO budget VALUES(?,?,?,?)', (ws, period, credits, ceiling))

    def reserve(self, ws, period, job, credits, estimate):
        self._scope(ws, period, job)
        self._amounts(credits, estimate)
        with self._tx() as db:
            prior = db.execute('SELECT * FROM usage WHERE ws=? AND period=? AND job=?', (ws, period, job)).fetchone()
            if prior:
                if (prior['credits'], prior['estimate']) != (credits, estimate):
                    raise ValueError('reservation conflict')
                return False  # replay never authorizes another execution
            budget = db.execute('SELECT * FROM budget WHERE ws=? AND period=?', (ws, period)).fetchone()
            if not budget:
                raise ValueError('budget missing')
            used = db.execute("SELECT COALESCE(SUM(CASE WHEN state='reserved' THEN credits ELSE charged END),0), COALESCE(SUM(CASE WHEN state='reserved' THEN estimate ELSE actual END),0) FROM usage WHERE ws=? AND period=?", (ws, period)).fetchone()
            if used[0] + credits > budget['credits'] or used[1] + estimate > budget['ceiling']:
                raise ValueError('budget exceeded')
            db.execute("INSERT INTO usage VALUES(?,?,?,?,?,'reserved',NULL,NULL)", (ws, period, job, credits, estimate))
            return True

    def settle(self, ws, period, job, charged, actual):
        self._scope(ws, period, job)
        self._amounts(charged, actual)
        with self._tx() as db:
            row = db.execute('SELECT * FROM usage WHERE ws=? AND period=? AND job=?', (ws, period, job)).fetchone()
            if not row or charged > row['credits']:
                raise ValueError('invalid settlement')
            if row['state'] == 'settled':
                if (charged, actual) != (row['charged'], row['actual']):
                    raise ValueError('settlement conflict')
                return False
            db.execute("UPDATE usage SET state='settled',charged=?,actual=? WHERE ws=? AND period=? AND job=?", (charged, actual, ws, period, job))
            return True

    def snapshot(self, ws, period):
        """Trusted operator reconciliation view; no job content or customer data."""
        self._scope(ws, period)
        with self._tx() as db:
            budget = db.execute('SELECT * FROM budget WHERE ws=? AND period=?', (ws, period)).fetchone()
            if not budget:
                raise ValueError('budget missing')
            reserved, settled = {}, {}
            for row in db.execute("SELECT state, COUNT(*) AS n, SUM(CASE WHEN state='reserved' THEN credits ELSE charged END) AS c, SUM(CASE WHEN state='reserved' THEN estimate ELSE actual END) AS cost FROM usage WHERE ws=? AND period=? GROUP BY state", (ws, period)):
                target = reserved if row['state'] == 'reserved' else settled
                target.update(n=row['n'], credits=row['c'], cost=row['cost'])
            used_credits = reserved.get('credits', 0) + settled.get('credits', 0)
            used_cost = reserved.get('cost', 0) + settled.get('cost', 0)
            return {'pending_jobs': reserved.get('n', 0), 'settled_jobs': settled.get('n', 0),
                    'reserved_credits': reserved.get('credits', 0), 'charged_credits': settled.get('credits', 0),
                    'reserved_cost': reserved.get('cost', 0), 'actual_cost': settled.get('cost', 0),
                    'remaining_credits': max(0, budget['credits'] - used_credits),
                    'remaining_cost': max(0, budget['ceiling'] - used_cost),
                    'cost_overrun': max(0, used_cost - budget['ceiling'])}
