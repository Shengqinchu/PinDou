"""One authorized SMS test and an exact-marker reply check in local Terminal."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

MARKER = 'PINDOU-5680-0911'


def save(path, value):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=True)
    os.chmod(path, 0o600)


def read_reply_counts(db, recipient, started_at, marker=MARKER):
    """Only return counts for the exact test marker from the selected sender."""
    columns = {row[1] for row in db.execute('PRAGMA table_info(message)')}
    if not {'handle_id', 'date', 'service', 'is_from_me', 'text'} <= columns:
        raise ValueError('unsupported_messages_schema')
    marker_match = 'm.text=?'
    args = [recipient, recipient.lstrip('+'), started_at, marker]
    if 'attributedBody' in columns:
        marker_match += ' OR instr(m.attributedBody,?)>0'
        args.append(marker.encode('utf-8'))
    rows = db.execute('''SELECT m.service,COUNT(*) FROM message m
        JOIN handle h ON h.ROWID=m.handle_id
        WHERE h.id IN (?,?) AND m.is_from_me=0 AND
        (CASE WHEN m.date>100000000000 THEN m.date/1000000000.0 ELSE m.date END)+978307200>=?
        AND (''' + marker_match + ') GROUP BY m.service', args).fetchall()
    return {service: count for service, count in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receive', action='store_true')
    parser.add_argument('--test-folder', default='canada-test-20260911')
    args = parser.parse_args()
    home = Path.home()
    if home != Path('/Users/pindou_sms'):
        print('请在 PinDou SMS 用户中运行。')
        return
    folder = home / 'Library' / 'Application Support' / 'PinDouSMS'
    if not re.fullmatch(r'[a-z0-9-]{8,64}', args.test_folder):
        raise ValueError('invalid_test_folder')
    directory = folder / args.test_folder
    if directory.resolve().parent != folder.resolve():
        raise ValueError('invalid_test_folder')
    config = json.loads((directory / 'test-recipient.json').read_text(encoding='utf-8'))
    recipient = config.get('recipient', '')
    if not re.fullmatch(r'(?:\+1[2-9][0-9]{9}|\+861[3-9][0-9]{9})', recipient):
        raise ValueError('invalid_test_recipient')
    marker = config.get('reply_marker', MARKER)
    if not re.fullmatch(r'PINDOU-[A-Z0-9-]{4,48}', marker):
        raise ValueError('invalid_reply_marker')

    if args.receive:
        scope_path = directory / 'reply-scope.json'
        if not scope_path.is_file():
            print('请先完成这次发送测试，再检查回复。')
            return
        scope = json.loads(scope_path.read_text(encoding='utf-8'))
        if scope['request_id'] != config['request_id'] or scope['marker'] != marker:
            raise ValueError('test_scope_mismatch')
        result = {'checked_at': time.time(), 'marker': marker}
        try:
            path = home / 'Library' / 'Messages' / 'chat.db'
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3) as db:
                counts = read_reply_counts(db, recipient, scope['started_at'], marker)
            result['matching_reply_counts'] = counts
            print('普通短信回复：' + ('已收到' if counts.get('SMS', 0) else '尚未查到'))
            if counts.get('iMessage', 0):
                print('查到了 iMessage 回复，仍需另核对普通短信回复。')
        except (sqlite3.Error, OSError, ValueError):
            result['reply_check_unavailable'] = True
            print('无法读取测试回复，请核对终端的完全磁盘访问权限。')
        save(directory / 'reply-check.json', result)
        return

    print('小狗短信测试：收件号码尾号 ' + recipient[-4:], flush=True)
    print('如果出现控制“信息”的提示，请选择允许。', flush=True)
    try:
        check = subprocess.run(
            ['/usr/bin/osascript', '-e', 'tell application "Messages" to return count of accounts'],
            capture_output=True, text=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired):
        save(directory / 'send-check.json', {'dispatched': False, 'state': 'permission_check_incomplete'})
        print('权限检查尚未完成，本次没有发送短信。')
        return
    if check.returncode or not check.stdout.strip().isdigit() or int(check.stdout.strip()) < 1:
        save(directory / 'send-check.json', {'dispatched': False, 'state': 'permission_or_account_required'})
        print('尚未取得控制权限或信息账号不可用，本次没有发送短信。')
        return
    spec = importlib.util.spec_from_file_location('pindou_sms_probe', folder / 'mac_sms_probe.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    scope = directory / 'reply-scope.json'
    if not scope.exists():
        save(scope, {'request_id': config['request_id'], 'started_at': time.time(), 'marker': marker})

    def runner(command, **kwargs):
        try:
            run = subprocess.run(command, **kwargs)
            save(directory / 'tool-check.json', {
                'exit_code': run.returncode, 'timed_out': False,
                'automation_denied': '-1743' in run.stderr,
                'error_codes': re.findall(r'\((-\d{1,6})\)', run.stderr),
                'error_terms': [word for word in ('permission', 'operation not permitted',
                    'authorization', 'access', 'apple', 'sms', 'service', 'account',
                    'database', 'chat.db', 'not found', 'failed') if word in run.stderr.lower()]})
            return run
        except subprocess.TimeoutExpired:
            save(directory / 'tool-check.json', {'timed_out': True})
            raise

    result = probe.dispatch(directory, runner=runner)
    save(directory / 'send-check.json', result)
    if result.get('reason') == 'request_already_attempted':
        print('这条测试已尝试过，未重复发送。')
    elif result['state'] == 'tool_reported_sent':
        print('工具已提交发送，请在收件手机核对短信及发件号码。')
    else:
        print('发送结果尚不确定，请核对收件手机；不要重复发送。')
    print('收到后，测试回复内容为：' + marker)


if __name__ == '__main__':
    main()
