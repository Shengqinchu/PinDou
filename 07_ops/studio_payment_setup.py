"""Scope the existing PinDou merchant configuration to the independent studio.

Run on the PinDou origin. Never prints credentials or signed cashier URLs.
--create-check creates ONE unpaid RMB 0.01 gateway diagnostic, without opening
public checkout or changing the original generator's payment integration.
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

SHARED = Path('/opt/pindou/studio/shared')
TARGET = SHARED / '.env'
SOURCE = Path('/opt/pindou/shared/.env')


def read_env(path):
    values = {}
    for line in path.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def sign(params, secret):
    return hashlib.md5(('&'.join(k + '=' + str(v) for k, v in sorted(params.items()) if k != 'hash' and v is not None and v != '') + secret).encode()).hexdigest()


def call(values, endpoint, body):
    params = {'appid': values['HUPIJIAO_APP_ID'], 'time': str(int(time.time())), 'nonce_str': secrets.token_hex(16), **body}
    params['hash'] = sign(params, values['HUPIJIAO_APP_SECRET'])
    base = values.get('HUPIJIAO_API_BASE_URL', 'https://api.xunhupay.com').rstrip('/')
    if urlparse(base).scheme != 'https':
        raise SystemExit('An HTTPS payment gateway is required.')
    request = Request(base + endpoint, data=urlencode(params).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read(32000))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--create-check', action='store_true')
    args = parser.parse_args()
    values = read_env(TARGET if TARGET.exists() else SOURCE)
    for name in ['HUPIJIAO_APP_ID', 'HUPIJIAO_APP_SECRET']:
        if not values.get(name):
            raise SystemExit('Required merchant configuration is missing: ' + name)
    if args.configure and not TARGET.exists():
        SHARED.mkdir(parents=True, exist_ok=True)
        SHARED.chmod(0o700)
        keys = ['HUPIJIAO_APP_ID', 'HUPIJIAO_APP_SECRET', 'HUPIJIAO_API_BASE_URL']
        output = {key: values[key] for key in keys if values.get(key)}
        output['STUDIO_PUBLIC_ORIGIN'] = 'https://pindoupuppy.com'
        fd = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            for key, value in output.items():
                f.write(key + '=' + json.dumps(value) + '\n')
        shutil.chown(TARGET, user='pindou', group='pindou')
    result = {'configured_file': TARGET.exists(), 'source_service_unchanged': True}
    if args.create_check:
        marker = SHARED / 'gateway-diagnostic.json'
        if marker.exists():
            diagnostic = json.loads(marker.read_text())
            order_id = diagnostic['order_id']
            result['existing_diagnostic'] = True
        else:
            order_id = 'PSCHECK' + time.strftime('%Y%m%d%H%M%S', time.gmtime()) + secrets.token_hex(3).upper()
            diagnostic = {'order_id': order_id, 'created_at': time.time(), 'cny_fen': 1}
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f: json.dump(diagnostic, f)
            data = call(values, '/payment/do.html', {
                'version': '1.1', 'trade_order_id': order_id, 'total_fee': '0.01',
                'title': 'PinDou Studio connection check', 'plugins': 'pindou-studio-diagnostic',
                'notify_url': 'https://pindoupuppy.com/studio-api/payments/hupijiao/notify',
            })
            inner = data.get('data') if isinstance(data.get('data'), dict) else data
            result['create'] = {'errcode': data.get('errcode'), 'signature_valid': data.get('hash') == sign(data, values['HUPIJIAO_APP_SECRET']), 'cashier_host': urlparse(str(inner.get('url', ''))).hostname, 'qr_host': urlparse(str(inner.get('url_qrcode', ''))).hostname, 'response_fields': list(data)}
            if data.get('errcode') not in (0, '0'):
                result['create']['message'] = str(data.get('errmsg', ''))[:120]
        data = call(values, '/payment/query.html', {'out_trade_order': order_id})
        inner = data.get('data', {})
        result['query'] = {'errcode': data.get('errcode'), 'status': inner.get('status') if isinstance(inner, dict) else None, 'fields': list(inner) if isinstance(inner, dict) else [], 'unpaid_diagnostic_only': True,
                           'diagnostic_total_amount': inner.get('total_amount'), 'payment_method': inner.get('payment_method')}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
