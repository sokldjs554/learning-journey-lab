"""Download complete histories for a deterministic, outcome-blind EdNet KT4 sample.

The official archive stays remote. HTTP Range retrieves its ZIP index and selected
members; ZIP CRC and SHA-256 verify downloaded content. No Kaggle credentials.
Raw histories and member-level hashes are local-only, never published.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import time
import urllib.request
import zipfile
import zlib

KT4_URL = 'https://drive.usercontent.google.com/download?id=1HHZwpeqMSowWhgEu0URBQQ3FizR9o9mT&export=download&confirm=t'
CONTENT_URL = 'https://drive.usercontent.google.com/download?id=117aYJAWG3GU48suS66NPaB82HwFj6xWS&export=download&confirm=t'
SEED = 'learning-journey-lab-ednet-kt4-v1'

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from journey.ednet_integrity import (
    DEFAULT_SNAPSHOT, assert_snapshot, public_manifest, read_snapshot, verify_cache,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def select_members(names, n, seed=SEED):
    valid = sorted(set(name for name in names if re.fullmatch(r'KT4/u\d+\.csv', name)))
    if not 1 <= n <= len(valid):
        raise ValueError('sample size must be between 1 and population size')
    return sorted(valid, key=lambda name: (digest((seed + ':' + name).encode()), name))[:n]


class RangeReader(io.RawIOBase):
    def __init__(self, fetch, size):
        self.fetch, self.size, self.position, self.cache = fetch, size, 0, []

    def seek(self, offset, whence=0):
        self.position = offset + (self.size if whence == 2 else self.position if whence == 1 else 0)
        if self.position < 0:
            raise ValueError('negative seek')
        return self.position

    def tell(self):
        return self.position

    def read(self, n=-1):
        start = self.position
        end = self.size if n < 0 else min(self.size, start + n)
        if end <= start:
            return b''
        for cached_start, chunk in self.cache:
            if cached_start <= start and end <= cached_start + len(chunk):
                data = chunk[start - cached_start:end - cached_start]
                break
        else:
            data = self.fetch(start, end - 1)
            if len(data) != end - start:
                raise ValueError('truncated range')
            self.cache.append((start, data))
        self.position = end
        return data


def read_index(fetch, size):
    with zipfile.ZipFile(RangeReader(fetch, size)) as archive:
        return archive.infolist()


def extract_member(info, chunk):
    if len(chunk) < 30 or chunk[:4] != b'PK\x03\x04':
        raise ValueError('invalid ZIP local header')
    header = struct.unpack('<4s5H3I2H', chunk[:30])
    name_length, extra_length = header[-2:]
    if chunk[30:30 + name_length].decode() != info.filename:
        raise ValueError('ZIP member name mismatch')
    offset = 30 + name_length + extra_length
    compressed = chunk[offset:offset + info.compress_size]
    if len(compressed) != info.compress_size:
        raise ValueError('truncated ZIP member')
    if info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompress(compressed, -15)
    elif info.compress_type == zipfile.ZIP_STORED:
        data = compressed
    else:
        raise ValueError('unsupported compression')
    if len(data) != info.file_size or zlib.crc32(data) != info.CRC:
        raise ValueError('ZIP size or CRC mismatch')
    return data


def group_ranges(infos, archive_size, gap=65536):
    groups = []
    for info in sorted(infos, key=lambda i: i.header_offset):
        # The central and local extra field lengths can differ. The additional
        # 65535 bytes cover the format's maximum local extra length, safely.
        end = min(archive_size - 1, info.header_offset + 30 + len(info.filename.encode()) + 65535 + info.compress_size - 1)
        if groups and info.header_offset <= groups[-1][1] + gap:
            start, previous_end, members = groups[-1]
            groups[-1] = start, max(end, previous_end), members + [info]
        else:
            groups.append((info.header_offset, end, [info]))
    return groups


def get_range(url, start, end, size=None):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}', 'User-Agent': 'LearningJourneyLab-research/1.0'})
            with urllib.request.urlopen(request, timeout=90) as response:
                content_range = response.headers.get('Content-Range', '')
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', content_range)
                if response.status != 206 or not match:
                    raise ValueError(f'server did not honor Range: {response.status}')
                first, last, total = map(int, match.groups())
                if (first, last) != (start, end) or (size is not None and total != size):
                    raise ValueError('server returned different range/archive size')
                data = response.read()
                if len(data) != end - start + 1:
                    raise ValueError('truncated HTTP range')
                return data, total
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def _download_new(output, n, workers, expected):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    _, size = get_range(KT4_URL, 0, 0)
    if size != expected['archive_bytes']:
        raise ValueError('published snapshot mismatch: archive_bytes')
    ranges = []
    def fetch(start, end):
        data, _ = get_range(KT4_URL, start, end, size)
        ranges.append({'start': start, 'end': end, 'sha256': digest(data)})
        return data
    infos = read_index(fetch, size)
    index_sha256 = max(ranges, key=lambda r: r['end'] - r['start'])['sha256']
    if index_sha256 != expected['zip_index_sha256']:
        raise ValueError('published snapshot mismatch: zip_index_sha256')
    names = select_members([i.filename for i in infos], n)
    if digest(('\n'.join(sorted(names)) + '\n').encode()) != expected['selected_members_sha256']:
        raise ValueError('published snapshot mismatch: selected_members_sha256')
    chosen = set(names)
    selected = [i for i in infos if i.filename in chosen]
    groups = group_ranges(selected, size)
    population = sum(bool(re.fullmatch(r'KT4/u\d+\.csv', i.filename)) for i in infos)
    print(f'Population {population:,}; sample {n:,}; {len(groups)} ranges, {sum(e-s+1 for s,e,_ in groups)/1e6:.1f} MB', flush=True)
    records = []
    def download_group(group):
        start, end, members = group
        data = fetch(start, end)
        result = []
        for info in members:
            content = extract_member(info, data[info.header_offset - start:])
            (output / Path(info.filename).name).write_bytes(content)
            result.append({'member': info.filename, 'sha256': digest(content), 'bytes': len(content), 'crc32': f'{info.CRC:08x}'})
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download_group, group) for group in groups]
        for j, future in enumerate(as_completed(futures), 1):
            records.extend(future.result())
            if j % 100 == 0:
                print(f'{j}/{len(groups)} ranges downloaded', flush=True)
    _, content_size = get_range(CONTENT_URL, 0, 0)
    content_zip, _ = get_range(CONTENT_URL, 0, content_size - 1, content_size)
    (output / 'contents.zip').write_bytes(content_zip)
    with zipfile.ZipFile(io.BytesIO(content_zip)) as archive:
        for info in archive.infolist():
            if re.fullmatch(r'contents/[a-z_]+\.csv', info.filename):
                (output / Path(info.filename).name).write_bytes(archive.read(info))
    records.sort(key=lambda record: record['member'])
    manifest = {
        'dataset': 'EdNet-KT4', 'source': 'https://github.com/riiid/ednet',
        'source_archive_url': KT4_URL, 'contents_archive_url': CONTENT_URL,
        'license': 'CC BY-NC 4.0; research purposes',
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'archive_bytes': size, 'archive_sha256': None, 'zip_index_sha256': index_sha256,
        'archive_sha256_note': 'Full archive not downloaded. Each fetched range and extracted selected member hashed locally; ZIP CRC verified.',
        'population_user_files': sum(bool(re.fullmatch(r'KT4/u\d+\.csv', i.filename)) for i in infos),
        'sample_users': n, 'seed': SEED,
        'sampling': 'Take n smallest SHA256(seed + colon + exact ZIP member name), complete histories. Selection uses only filenames, never behavior or future activity.',
        'selected_members_sha256': digest(('\n'.join(sorted(names)) + '\n').encode()),
        'sample_content_sha256': digest(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()),
        'sample_uncompressed_bytes': sum(record['bytes'] for record in records),
        'contents_zip_bytes': content_size, 'contents_zip_sha256': digest(content_zip),
        'kt4_transferred_bytes': sum(record['end'] - record['start'] + 1 for record in ranges),
        'member_records': records, 'range_records': sorted(ranges, key=lambda record: record['start']),
    }
    public = public_manifest(manifest)
    assert_snapshot(public, expected)
    (output / 'download_manifest.local.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'download_manifest.json').write_text(json.dumps(public, indent=2) + '\n')
    return public


def download_sample(output, n=2048, workers=8, expected_manifest=DEFAULT_SNAPSHOT):
    """Reuse verified bytes; never overwrite an existing or incomplete cache."""
    output = Path(output)
    expected = read_snapshot(expected_manifest)
    if n != expected['sample_users'] or SEED != expected['seed']:
        raise ValueError('requested sample size/seed differs from published snapshot')
    if output.exists() and any(output.iterdir()):
        verified = verify_cache(output, expected_manifest)
        print('Reusing pinned, verified cache; no network download.', flush=True)
        return verified
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ednet-download-', dir=output.parent) as temporary:
        staged = Path(temporary) / 'payload'
        _download_new(staged, n, workers, expected)
        verified = verify_cache(staged, expected_manifest)
        if output.exists():
            output.rmdir()  # fails if anything appeared; no replacement of files
        staged.rename(output)
    return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/raw/ednet'))
    parser.add_argument('--users', type=int, default=2048)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--expected-manifest', type=Path, default=DEFAULT_SNAPSHOT)
    args = parser.parse_args()
    print(json.dumps(download_sample(args.output, args.users, args.workers, args.expected_manifest), indent=2))
