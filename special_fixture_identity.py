"""Versioned daily identity for the local synthetic evaluation only."""
import hashlib
import json


def fixture_identity(report, stamp):
    if type(stamp) is not int or not 0 <= stamp <= 2**63-1:
        raise ValueError('invalid timestamp')
    if not isinstance(report, dict) or report.get('complete') is not True:
        raise ValueError('incomplete fixture report')
    parts = [report.get(k) for k in ('revision', 'suite', 'evaluator_version')]
    if not all(isinstance(x, str) and 0 < len(x) <= 256 for x in parts):
        raise ValueError('invalid fixture version')
    day = stamp // 86400
    version = hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()
    return 'fixture-'+version+'-'+str(day), day*86400
