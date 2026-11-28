"""Isolated persistent store for completed SPECIAL evaluation checks."""
import json
import sqlite3
from contextlib import closing
from special_dashboard import dashboard


class EvaluationStore:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path, timeout=10)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS special_eval_run (ws TEXT NOT NULL, run TEXT NOT NULL, finished INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(ws,run))')

    @staticmethod
    def _id(value):
        if not isinstance(value, str) or not 0 < len(value) <= 256 or not value.strip():
            raise ValueError('invalid identifier')
        return value

    def save(self, workspace, run_id, report, finished_at):
        """Trusted simulation adapter only; never accept a customer report payload."""
        self._id(workspace)
        self._id(run_id)
        if not isinstance(report, dict) or report.get('workspace') != workspace or report.get('complete') is not True:
            raise ValueError('invalid report scope or state')
        if type(finished_at) is not int or not 0 <= finished_at <= 2**63-1:
            raise ValueError('invalid time')
        revision, suite, version = (self._id(report.get(k)) for k in ('revision', 'suite', 'evaluator_version'))
        total, passed, outcomes = (report.get(k) for k in ('total', 'passed', 'outcomes'))
        if type(total) is not int or not 1 <= total <= 100 or type(passed) is not int or not 0 <= passed <= total or not isinstance(outcomes, list) or len(outcomes) != total:
            raise ValueError('invalid counts')
        clean, seen = [], set()
        for item in outcomes:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError('invalid outcome')
            ident, status = item
            self._id(ident)
            if ident in seen or status not in ('passed', 'failed'):
                raise ValueError('invalid outcome')
            seen.add(ident)
            clean.append([ident, status])
        if sum(s == 'passed' for _, s in clean) != passed:
            raise ValueError('inconsistent results')
        payload = json.dumps(dict(workspace=workspace, run_id=run_id, revision=revision,
                                  suite=suite, evaluator_version=version, finished_at=finished_at,
                                  complete=True, total=total, passed=passed, outcomes=sorted(clean)),
                             ensure_ascii=False, sort_keys=True)
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                prior = db.execute('SELECT payload FROM special_eval_run WHERE ws=? AND run=?', (workspace, run_id)).fetchone()
                if prior:
                    if prior[0] != payload:
                        raise ValueError('run identifier conflict')
                    db.commit()
                    return False
                db.execute('INSERT INTO special_eval_run VALUES(?,?,?,?)', (workspace, run_id, finished_at, payload))
                db.commit()
                return True
            except BaseException:
                db.rollback()
                raise

    def read_dashboard(self, *, workspace, grants, now, enabled=False):
        from special_entitlements import entitled_features
        if 'learning_simulation' not in entitled_features(grants, workspace=workspace, now=now, enabled=enabled):
            return None
        self._id(workspace)
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            rows = db.execute('SELECT payload FROM special_eval_run WHERE ws=? AND finished<=? ORDER BY finished DESC, run DESC LIMIT 500', (workspace, now)).fetchall()
        return dashboard([json.loads(row[0]) for row in rows], workspace=workspace, grants=grants, now=now, enabled=enabled)

    def purge_workspace(self, workspace):
        """Trusted retention/deletion worker only."""
        self._id(workspace)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            return db.execute('DELETE FROM special_eval_run WHERE ws=?', (workspace,)).rowcount
