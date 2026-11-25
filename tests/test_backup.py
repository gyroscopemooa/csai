import sqlite3
import pytest
from backup import backup

def test_backup_consistent_and_no_overwrite(tmp_path):
    src=tmp_path/'source.sqlite3'; dest=tmp_path/'copy.sqlite3'
    with sqlite3.connect(src) as c:
        c.execute('CREATE TABLE sample(value TEXT)');c.execute("INSERT INTO sample VALUES('test')")
    backup(src,dest)
    with sqlite3.connect(dest) as c:assert c.execute('SELECT value FROM sample').fetchone()==('test',)
    with pytest.raises(ValueError):backup(src,dest)
    with pytest.raises(ValueError):backup(src,src)
