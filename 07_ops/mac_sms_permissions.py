"""Read-only setup check, launched locally in the SMS user's Terminal.

This does not send messages, enumerate contacts, or read message contents.
macOS still owns permission prompts; this script never changes permission data.
"""
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time


def main():
    home = Path.home()
    if home != Path('/Users/pindou_sms'):
        print('请在 PinDou SMS 用户中运行此检查。')
        return
    directory = home / 'Library' / 'Application Support' / 'PinDouSMS'
    result = {'checked_at': time.time(), 'source': 'local_terminal',
              'messages_sent': 0, 'message_contents_read': 0}
    print('小狗短信：权限检查（不会发送短信）', flush=True)
    print('如果弹出“终端想要控制信息”，请选择允许。', flush=True)
    try:
        check = subprocess.run(
            ['/usr/bin/osascript', '-e',
             'tell application "Messages" to return count of accounts'],
            capture_output=True, text=True, timeout=45, check=False)
        result['automation_allowed'] = check.returncode == 0
        if check.returncode == 0 and check.stdout.strip().isdigit():
            result['account_count'] = int(check.stdout.strip())
        elif check.returncode:
            match = re.search(r'\((-?\d+)\)\s*$', check.stderr.strip())
            result['automation_error_code'] = int(match[1]) if match else None
    except (OSError, subprocess.TimeoutExpired):
        result['automation_allowed'] = False
        result['automation_check_incomplete'] = True

    path = home / 'Library' / 'Messages' / 'chat.db'
    try:
        result['database_file_exists'] = path.is_file()
    except OSError as error:
        result['database_stat_errno'] = error.errno
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3) as db:
            table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='message'").fetchone()
        result['messages_database_readable'] = table is not None
    except (sqlite3.Error, OSError) as error:
        result['messages_database_readable'] = False
        result['database_error_code'] = getattr(error, 'sqlite_errorcode', getattr(error, 'errno', None))

    destination = directory / 'local-permission-check.json'
    fd = os.open(str(destination), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=True)
    os.chmod(destination, 0o600)
    print('控制信息：' + ('已允许' if result['automation_allowed'] else '待允许'))
    print('读取回复：' + ('可用' if result['messages_database_readable'] else '暂不可用'))
    print('这里仅检查权限；手机号验证和短信转发仍需分别完成。')
    if not result['messages_database_readable']:
        print('收取测试回复还需要：系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 允许终端。')
        print('设置后退出终端，再次打开“小狗短信权限检查.command”。')
    print('检查结果已保存，可以回到 Codex 继续。')


if __name__ == '__main__':
    main()
