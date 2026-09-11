"""Offline tests: no Messages invocation and no real SMS recipients."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('mac_sms_probe', Path(__file__).with_name('mac_sms_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def prepare(tmp_path, **changes):
    config = tmp_path / 'test-recipient.json'
    value = {'recipient': '+14165550100', 'approved_text': probe.TEST_TEXT,
             'approved_at': time.time(), 'request_id': 'offline-test-123456789'}
    value.update(changes)
    config.write_text(json.dumps(value), encoding='utf-8')
    config.chmod(0o600)
    tool = tmp_path / 'imsg'
    tool.write_text('not executable: mocked tests only', encoding='utf-8')
    return tool


@pytest.mark.parametrize('changes', [
    {'approved_text': 'different message'},
    {'approved_at': None},
    {'recipient': '+14165550100; echo injected'},
    {'request_id': '../../unsafe'},
])
def test_invalid_config_cannot_dispatch(tmp_path, changes):
    tool = prepare(tmp_path, **changes)
    with pytest.raises(ValueError):
        probe.dispatch(tmp_path, tool, lambda *a, **k: pytest.fail('must not dispatch'))


def test_dispatch_is_sms_only_and_replay_does_not_send(tmp_path):
    tool = prepare(tmp_path)
    calls = []
    def runner(command, **options):
        calls.append(command)
        assert options['timeout'] == 45
        return SimpleNamespace(returncode=0, stdout='sensitive provider output')
    result = probe.dispatch(tmp_path, tool, runner)
    assert result['state'] == 'tool_reported_sent' and not result['delivery_verified']
    assert calls[0][calls[0].index('--service') + 1] == 'sms'
    assert 'sensitive' not in json.dumps(result)
    again = probe.dispatch(tmp_path, tool, runner)
    assert not again['dispatched'] and len(calls) == 1


def test_uncertain_timeout_is_not_retried(tmp_path):
    tool = prepare(tmp_path)
    def runner(command, **options):
        raise subprocess.TimeoutExpired(command, 45)
    result = probe.dispatch(tmp_path, tool, runner)
    assert result['state'] == 'outcome_unknown'
    again = probe.dispatch(tmp_path, tool, lambda *a, **k: pytest.fail('no retry after timeout'))
    assert not again['dispatched']


def test_crash_after_dispatch_started_does_not_resend(tmp_path):
    tool = prepare(tmp_path)
    def runner(command, **options):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        probe.dispatch(tmp_path, tool, runner)
    again = probe.dispatch(tmp_path, tool, lambda *a, **k: pytest.fail('no retry after crash'))
    assert again['state'] == 'started' and not again['dispatched']
