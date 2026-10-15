"""Read-only consistency verification of owned local publication artifacts."""
import hashlib
import json
import math
from pathlib import Path
import re

from .pipeline import METRICS


def _integer(value):
    return type(value) is int and value >= 0


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _json(raw):
    def invalid_constant(value):
        raise ValueError(f'nonfinite JSON value: {value}')
    def finite_float(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError('JSON number overflows finite float range')
        return value
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                          parse_constant=invalid_constant, parse_float=finite_float)
    except RecursionError as exc:
        raise ValueError('JSON nesting is too deep') from exc


def verify_manifest(manifest_path):
    """Check one local snapshot; unsigned manifests provide no authentication.

    Metrics bytes are read once for hashing and parsing. No filesystem locking,
    adversarial race protection, business-quality revalidation or writes.
    """
    path = Path(manifest_path)
    manifest = _json(path.read_bytes())
    if not isinstance(manifest, dict):
        raise ValueError('manifest must be an object')
    filename = manifest.get('metrics_file')
    if (not isinstance(filename, str) or not filename or filename in ('.', '..')
            or '/' in filename or '\\' in filename or '\x00' in filename
            or Path(filename).is_absolute()):
        raise ValueError('metrics_file must be a local basename')
    digest = manifest.get('sha256')
    if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
        raise ValueError('sha256 must be a lowercase 64-character hex digest')
    counts = manifest.get('counts')
    if (not isinstance(counts, dict) or counts.keys() != METRICS.keys()
            or not all(_integer(value) for value in counts.values())):
        raise ValueError('counts must contain all six nonnegative integer mart counts')
    revenue = manifest.get('revenue_cents')
    if not _integer(revenue):
        raise ValueError('revenue_cents must be a nonnegative integer')
    target = path.parent / filename
    if target.is_symlink():
        raise ValueError('metrics file must not be a symlink')
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('metrics SHA256 mismatch')
    metrics = _json(raw)
    if (not isinstance(metrics, dict) or metrics.keys() != METRICS.keys()
            or not all(isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
                       for rows in metrics.values())):
        raise ValueError('metrics must contain six mart arrays of objects')
    actual_counts = {key: len(rows) for key, rows in metrics.items()}
    if actual_counts != counts:
        raise ValueError('metrics row counts mismatch')
    amounts = [row.get('revenue_cents') for row in metrics['monetization']]
    if not all(_integer(amount) for amount in amounts):
        raise ValueError('monetization revenue_cents must be nonnegative integers')
    if sum(amounts) != revenue:
        raise ValueError('metrics revenue mismatch')
    return {'status': 'verified', 'sha256': digest, 'counts': actual_counts, 'revenue_cents': revenue}
