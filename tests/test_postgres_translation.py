from postgres_store import translate,validate_dsn,checked_name
import pytest

def test_query_translation_preserves_literals_and_case():
    q="UPDATE booking SET end=?,status=CASE WHEN ?='end?' THEN 'end' ELSE status END WHERE id=?"
    assert translate(q)=="""UPDATE booking SET "end"=%s,status=CASE WHEN %s='end?' THEN 'end' ELSE status END WHERE id=%s"""
    assert translate("UPDATE usage SET n=MAX(0,n-1) WHERE ws=?")=="UPDATE usage SET n=GREATEST(0,n-1) WHERE ws=%s"
    assert translate("INSERT OR IGNORE INTO usage VALUES(?,?,?)")=="INSERT INTO usage VALUES(%s,%s,%s) ON CONFLICT DO NOTHING"
    assert translate("CREATE TABLE IF NOT EXISTS test(id TEXT,end INTEGER,cost REAL)")=='CREATE TABLE IF NOT EXISTS test(id TEXT,"end" BIGINT,cost DOUBLE PRECISION)'

def test_dsn_requires_credentials_and_ssl():
    for v in ('','sqlite:///dev','postgres://host/db','postgres://user:pass@host/db?sslmode=disable'):
        with pytest.raises(RuntimeError):validate_dsn(v)
    assert validate_dsn('postgresql://test:secret@host/db?sslmode=require').endswith('sslmode=require')
    with pytest.raises(ValueError):checked_name('workspace; DROP TABLE')
