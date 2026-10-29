"""Typed OULAD ingestion and transparent SQL transformations."""
from pathlib import Path
import json
import duckdb
from scripts.download import digest
ROOT=Path(__file__).resolve().parents[2]
SQL=ROOT/'sql'
TABLES=['courses','studentRegistration','vle','studentVle','studentInfo','assessments','studentAssessment']


def connect(path=':memory:'):
    c=duckdb.connect(str(path)); c.execute("SET threads=4"); c.execute("SET memory_limit='1GB'")
    return c


def load_sources(c, folder, manifest=None):
    folder=Path(folder)
    if manifest:
        for name, meta in json.loads(Path(manifest).read_text())['files'].items():
            if digest(folder/name)!=meta['sha256']: raise ValueError(f'Source hash mismatch: {name}')
    for name in TABLES:
        # ? is the documented missing-value sentinel, not a string date.
        path=str(folder/f'{name}.csv').replace("'","''")
        c.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto('{path}', nullstr=['','?'], sample_size=-1)")


def quality(c):
    cur=c.execute((SQL/'quality.sql').read_text())
    rows=cur.fetchall()+c.execute((SQL/'dimensions.sql').read_text()).fetchall()
    return sorted([dict(zip(['rule_id','severity','count'],r)) for r in rows],key=lambda r:r['rule_id'])


def build_marts(c, strict=False):
    invalid=[r[0] for r in c.execute((SQL/'dimensions.sql').read_text()).fetchall() if r[2]]
    if invalid: raise ValueError('invalid dimension: '+', '.join(invalid))
    for table,keys in [('courses','code_module,code_presentation'),('vle','code_module,code_presentation,id_site'),('studentRegistration','code_module,code_presentation,id_student')]:
        if c.execute(f'SELECT count(*)-count(DISTINCT({keys})) FROM {table}').fetchone()[0]:
            raise ValueError(f'duplicate dimension key: {table}; cannot safely JOIN')
    # DuckDB cannot parameterize several statements at once; strict is a local boolean only.
    c.execute((SQL/'marts.sql').read_text().replace('$strict','TRUE' if strict else 'FALSE'))
    return c.sql('SELECT * FROM mart ORDER BY code_module,code_presentation,id_student').df()
