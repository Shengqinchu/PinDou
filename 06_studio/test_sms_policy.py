from concurrent.futures import ThreadPoolExecutor

import pytest

from sms_policy import CAPS, OTP_TTL, SmsLedger

READY = ("firebase", "descope")
SUBJECT = "a" * 64
NOW = 1788998400


def key(n):
    return f"server-request-{n:012d}"


def test_no_accounts_keeps_sending_disabled(tmp_path):
    plan = SmsLedger(tmp_path / "sms.sqlite").reserve(key(1), SUBJECT, now=NOW)
    assert plan.provider == "email" and not plan.dispatch


def test_free_allowances_fall_through_and_concurrent_requests_do_not_overspend(tmp_path):
    path = tmp_path / "sms.sqlite"
    SmsLedger(path)
    def reserve(n):
        return SmsLedger(path).reserve(key(n), SUBJECT, eligible=READY, now=NOW)
    with ThreadPoolExecutor(max_workers=12) as pool:
        plans = list(pool.map(reserve, range(150)))
    assert sum(p.provider == "firebase" and p.dispatch for p in plans) == 10
    assert sum(p.provider == "descope" and p.dispatch for p in plans) == 100
    assert sum(p.provider == "email" and not p.dispatch for p in plans) == 40


def test_priority_not_caller_order_and_unconfigured_provider_skipped(tmp_path):
    ledger = SmsLedger(tmp_path / "sms.sqlite")
    assert ledger.reserve(key(1), SUBJECT, eligible=reversed(READY), now=NOW).provider == "firebase"
    assert ledger.reserve(key(2), SUBJECT, eligible=("descope",), now=NOW).provider == "descope"


def test_restart_or_same_request_cannot_resend_or_switch_provider(tmp_path):
    path = tmp_path / "sms.sqlite"
    ledger = SmsLedger(path)
    first = ledger.reserve(key(1), SUBJECT, eligible=READY, now=NOW)
    assert first.dispatch
    for n in range(2, 11):
        ledger.reserve(key(n), SUBJECT, eligible=READY, now=NOW)
    duplicate = SmsLedger(path).reserve(key(1), SUBJECT, eligible=("descope",), now=NOW + 30)
    assert duplicate.provider == "firebase" and not duplicate.dispatch
    assert ledger.verification_provider(key(1), SUBJECT, now=NOW + 30) == "firebase"
    expired = ledger.reserve(key(1), SUBJECT, eligible=READY, now=NOW + OTP_TTL + 1)
    assert not expired.dispatch


@pytest.mark.parametrize("outcome", ["sent", "failed", "unknown"])
def test_failed_or_uncertain_sends_are_not_refunded(tmp_path, outcome):
    ledger = SmsLedger(tmp_path / "sms.sqlite")
    for n in range(10):
        ledger.reserve(key(n), SUBJECT, eligible=READY, now=NOW)
        ledger.record_outcome(key(n), SUBJECT, outcome)
    assert ledger.reserve(key(11), SUBJECT, eligible=READY, now=NOW).provider == "descope"


def test_quota_does_not_reset_at_site_midnight_or_when_codes_expire(tmp_path):
    ledger = SmsLedger(tmp_path / "sms.sqlite")
    for n in range(110):
        ledger.reserve(key(n), SUBJECT, eligible=READY, now=NOW)
    assert ledger.reserve(key(111), SUBJECT, eligible=READY, now=NOW + 86400).provider == "email"
    assert ledger.reserve(key(112), SUBJECT, eligible=READY, now=NOW + CAPS['firebase'][1] + 1).provider == "firebase"
    assert ledger.reserve(key(113), SUBJECT, eligible=('descope',), now=NOW + 31 * 86400).provider == "email"
    assert ledger.reserve(key(114), SUBJECT, eligible=('descope',), now=NOW + CAPS['descope'][1] + 1).provider == "descope"


def test_verification_is_bound_to_subject_and_expires(tmp_path):
    ledger = SmsLedger(tmp_path / "sms.sqlite")
    ledger.reserve(key(1), SUBJECT, eligible=READY, now=NOW)
    with pytest.raises(ValueError, match="subject_mismatch"):
        ledger.reserve(key(1), 'b' * 64, eligible=READY, now=NOW)
    for subject, at in [('b' * 64, NOW), (SUBJECT, NOW + OTP_TTL)]:
        with pytest.raises(ValueError, match="unavailable"):
            ledger.verification_provider(key(1), subject, now=at)


def test_plain_phone_is_not_accepted_as_ledger_key(tmp_path):
    with pytest.raises(ValueError, match="opaque_server_keys"):
        SmsLedger(tmp_path / "sms.sqlite").reserve(key(1), '+15555555555', eligible=READY, now=NOW)
