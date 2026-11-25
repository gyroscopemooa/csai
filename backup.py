"""Local operator backup: SQLite online backup with integrity check; never overwrites.
The copy contains private data. Store on an encrypted volume, never commit or share it.
"""
import argparse, os, sqlite3, tempfile
from pathlib import Path

def backup(source: Path, dest: Path):
    source, dest = source.resolve(), dest.resolve()
    if not source.is_file() or source == dest or dest.exists():
        raise ValueError('Source must exist; destination must be a new file.')
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.csai-backup-', suffix='.sqlite3', dir=dest.parent)
    os.close(fd)
    try:
        src = sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('Backup integrity check failed.')
        finally:
            dst.close(); src.close()
        # Exclusive target creation, no overwrite even if another backup races.
        os.link(tmp, dest)
        return dest
    finally:
        Path(tmp).unlink(missing_ok=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    args=p.parse_args()
    from store import DATA
    print('Backup created:',backup(DATA/'csai.sqlite3',args.destination))
