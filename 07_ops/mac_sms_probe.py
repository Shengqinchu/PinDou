"""A single explicitly authorized SMS test through the owner's existing Mac.

Default mode checks the tool only. The recipient is read from a private local
file, never accepted from a public endpoint. A dispatch is journaled before
calling Messages; ambiguous outcomes are not automatically repeated.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

TEST_TEXT = '小狗拼豆铺短信测试，无需回复，不会创建预约。'
DEFAULT_DIRECTORY = Path.home() / 'Library' / 'Application Support' / 'PinDouSMS'
DEFAULT_TOOL = Path('/opt/homebrew/bin/imsg')


def check(tool=DEFAULT_TOOL):
    if sys.platform != 'darwin':
        return {'ready': False, 'reason': 'mac_required'}
    if not Path(tool).is_file():
        return {'ready': False, 'reason': 'imsg_missing'}
    try:
        result = subprocess.run([str(tool), '--version'], capture_output=True,
                                text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {'ready': False, 'reason': 'imsg_unavailable'}
    version = result.stdout.strip()
    if result.returncode or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        return {'ready': False, 'reason': 'imsg_version_unavailable'}
    return {'ready': True, 'imsg_version': version,
            'sms_forwarding': 'requires_device_confirmation',
            'delivery_verified': False}


def dispatch(directory, tool=DEFAULT_TOOL, runner=subprocess.run):
    directory = Path(directory)
    config = directory / 'test-recipient.json'
    if not config.is_file():
        raise ValueError('test_recipient_required')
    if os.name != 'nt' and config.stat().st_mode & 0o077:
        raise ValueError('private_config_permissions_required')
    value = json.loads(config.read_text(encoding='utf-8'))
    recipient = value.get('recipient', '')
    chat_guid = value.get('chat_guid')
    request_id = value.get('request_id', '')
    approved_at = value.get('approved_at')
    if (value.get('approved_text') != TEST_TEXT
            or type(approved_at) not in (int, float)
            or not 0 < approved_at <= time.time() + 300):
        raise ValueError('explicit_test_authorization_required')
    if not re.fullmatch(r'(?:\+1[2-9][0-9]{9}|\+861[3-9][0-9]{9})', recipient):
        raise ValueError('supported_test_phone_required')
    if chat_guid is not None and (not isinstance(chat_guid, str)
            or not re.fullmatch(r'SMS;[+-];' + re.escape(recipient), chat_guid)):
        raise ValueError('matching_direct_sms_chat_required')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{16,80}', request_id):
        raise ValueError('request_id_required')
    if not Path(tool).is_file():
        raise ValueError('imsg_missing')

    journal = directory / 'probe.sqlite3'
    with sqlite3.connect(str(journal), timeout=10) as db:
        os.chmod(journal, 0o600)
        db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, created REAL NOT NULL, state TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT state FROM attempts WHERE id=?', (request_id,)).fetchone()
        if previous:
            return {'dispatched': False, 'state': previous[0],
                    'reason': 'request_already_attempted', 'delivery_verified': False}
        db.execute('INSERT INTO attempts VALUES (?,?,?)', (request_id, time.time(), 'started'))
        db.commit()
        target = ['--chat-guid', chat_guid] if chat_guid else ['--to', recipient]
        command = [str(tool), 'send', *target, '--text', TEST_TEXT,
                   '--service', 'sms', '--region', 'CN' if recipient.startswith('+86') else 'CA', '--json']
        try:
            completed = runner(command, capture_output=True, text=True,
                               timeout=45, check=False)
            state = 'tool_reported_sent' if completed.returncode == 0 else 'outcome_unknown'
        except (OSError, subprocess.TimeoutExpired):
            state = 'outcome_unknown'
        # Tool output can contain the recipient. Do not log it or infer delivery.
        db.execute('UPDATE attempts SET state=? WHERE id=?', (state, request_id))
        db.commit()
    return {'dispatched': True, 'state': state, 'delivery_verified': False,
            'next': 'recipient_must_confirm_sms_and_sender_number'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument('--send-approved-test', action='store_true')
    args = parser.parse_args()
    try:
        result = dispatch(args.directory) if args.send_approved_test else check()
    except (ValueError, OSError, sqlite3.Error):
        result = {'dispatched': False, 'state': 'preparation_incomplete'}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
