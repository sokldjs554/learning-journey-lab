"""Download the official OULAD archive. Never replace different local source data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

URL = 'https://archive.ics.uci.edu/static/public/349/open%2Buniversity%2Blearning%2Banalytics%2Bdataset.zip'
SHA256 = 'f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4'
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def extract_verified(archive, destination, expected_hash):
    archive, destination = Path(archive), Path(destination)
    if digest(archive) != expected_hash:
        raise ValueError('SHA256 mismatch; source changed or download corrupted')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            p=PurePosixPath(member.filename)
            if p.is_absolute() or '..' in p.parts or len(p.parts)!=1 or member.is_dir():
                raise ValueError('unsafe archive path')
            target=destination/member.filename
            if target.exists() and digest(target)!=hashlib.sha256(z.read(member)).hexdigest():
                raise ValueError(f'existing source differs: {target}')
        destination.mkdir(parents=True,exist_ok=True)
        for member in z.infolist():
            target=destination/member.filename
            if not target.exists(): target.write_bytes(z.read(member))
    return {p.name: {'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(destination.glob('*.csv'))}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--archive',type=Path)
    a=parser.parse_args(); p=a.archive or ROOT/'work/oulad.zip'; p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        tmp=p.with_suffix('.partial'); urllib.request.urlretrieve(URL,tmp)
        if digest(tmp)!=SHA256: raise ValueError('SHA256 mismatch; not using download')
        tmp.replace(p)
    files=extract_verified(p,ROOT/'data/raw',SHA256)
    manifest={'source':'OULAD','url':URL,'archive_sha256':SHA256,'license':'CC BY 4.0',
              'citation':'Kuzilek, Hlosta, Zdrahal (2017), doi:10.1038/sdata.2017.171',
              'checked_date':'2026-10-29','files':files}
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Verified and extracted',len(files),'CSV files')

if __name__=='__main__': main()
