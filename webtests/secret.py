"""Load sensitive information from secret.json. Create a default one if failed.

Attributes:
    SECRET (dict): Sensitive data. Fields including `username`, `password` and `requests_kwargs`.
"""

import json
from pathlib import Path

from jsonschema import validate

SECRET_FILE = Path(__file__).parent.parent / 'secret.json'
SECRET_SCHEMA = {
    'type': 'object',
    'properties': {
        'username': {'type': 'string'},
        'password': {'type': 'string'},
        'requests_kwargs': {'type': 'object'},
    },
    'required': [
        'username',
        'password',
        'requests_kwargs',
    ],
}
SECRET = {
    'username': 'USERNAME',
    'password': 'PASSWORD',
    'requests_kwargs': {},
}
validate(instance=SECRET, schema=SECRET_SCHEMA)


def _save_secret(secret):
    with SECRET_FILE.open('wt', encoding='utf-8') as f:
        json.dump(secret, f, indent=2, sort_keys=True)


def _load_secret():
    with SECRET_FILE.open('rt', encoding='utf-8') as f:
        secret = json.load(f)
    validate(instance=secret, schema=SECRET_SCHEMA)
    return secret


try:
    SECRET = _load_secret()
except FileNotFoundError:
    _save_secret(SECRET)
    raise RuntimeError('secret.json not found. A default secret.json has been created.')
except json.JSONDecodeError:
    _save_secret(SECRET)
    raise RuntimeError('Invalid json file. A default secret.json has been created.')
except ValueError:
    _save_secret(SECRET)
    raise RuntimeError('Invalid secret.json format. A default secret.json has been created.')

__all__ = (
    'SECRET',
)
