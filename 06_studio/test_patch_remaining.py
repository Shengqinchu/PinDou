"""Remaining-place edits use disposable databases and never rewrite gift claims."""
import json

import pytest
import app as studio
import patch_promotion as promo
from test_reservations import client, submit, admin
from test_patch_promotion import patch, state, settings, change, gift


def managed(client):
    admin()
    return client.get('/studio-api/manage/patch-promotion').json()


def edit_remaining(client, value, **overrides):
    current = managed(client)
    request = {'quota': current['quota'], 'remaining': value,
               'enabled': current['enabled'], 'version': current['version']} | overrides
    return client.put('/studio-api/manage/patch-promotion', json=request), request


def test_remaining_independent_of_total_and_awards_persists(client):
    row = submit(client, patch(10, 3)).json()
    result, _ = edit_remaining(client, 6)
    assert result.status_code == 200
    assert (result.json()['quota'], result.json()['remaining'], result.json()['allocated']) == (10, 6, 3)
    assert gift(client, row) == 3
    promo.initialize(studio.database, 'not-a-new-campaign')
    assert state(client)['remaining'] == 6
    later = submit(client, patch(12, 2)).json()
    assert state(client)['remaining'] == 4 and gift(client, later) == 2
    assert change(client, later, 'cancelled').status_code == 200
    assert state(client)['remaining'] == 6
    assert change(client, later | {'version': 2}, 'pending').status_code == 200
    assert state(client)['remaining'] == 4
    assert state(client)['quota'] == 10


def test_zero_then_reopen_does_not_revoke_or_backfill(client):
    awarded = submit(client, patch(10, 3)).json()
    assert edit_remaining(client, 0)[0].status_code == 200
    assert gift(client, awarded) == 3
    missed = submit(client, patch(12)).json()
    assert gift(client, missed) == 0
    assert edit_remaining(client, 1)[0].status_code == 200
    final = submit(client, patch(14, 4)).json()
    assert gift(client, final) == 4 and state(client)['remaining'] == 0
    assert gift(client, missed) == 0
    assert change(client, final, 'cancelled').status_code == 200
    assert state(client)['remaining'] == 1  # preserve whole-group overshoot semantics


def test_booking_or_cancellation_while_editing_rejects_stale_save(client):
    initial = managed(client)
    row = submit(client, patch()).json()
    request = {'quota': 10, 'remaining': 9, 'enabled': True, 'version': initial['version']}
    assert client.put('/studio-api/manage/patch-promotion', json=request).status_code == 409
    assert state(client)['remaining'] == 8
    request['version'] = managed(client)['version']
    assert change(client, row, 'cancelled').status_code == 200
    assert client.put('/studio-api/manage/patch-promotion', json=request).status_code == 409
    assert state(client)['remaining'] == 10


def test_lost_response_retry_does_not_reset_places_used_after_save(client):
    result, request = edit_remaining(client, 6)
    assert result.status_code == 200
    submit(client, patch(10, 2))
    before = managed(client)
    for _ in range(2):
        retry = client.put('/studio-api/manage/patch-promotion', json=request)
        assert retry.status_code == 200 and retry.json() == before
    assert before['remaining'] == 4
    with studio.database() as db:
        events = db.execute("SELECT detail FROM patch_promotion_events WHERE action='settings'").fetchall()
        assert len(events) == 1
        detail = json.loads(events[0][0])
        assert detail['before']['remaining'] == 10 and detail['after']['remaining'] == 6


def test_older_client_quota_edits_keep_manual_adjustment(client):
    edit_remaining(client, 6)
    assert settings(client, 12).json()['remaining'] == 8
    assert settings(client, 12, False).json()['remaining'] == 8
    assert settings(client, 12, True).json()['remaining'] == 8


@pytest.mark.parametrize('invalid', [-1, 1.5, '3', True, 100001])
def test_remaining_integer_validation_has_no_side_effects(client, invalid):
    before = managed(client)
    response, _ = edit_remaining(client, invalid)
    assert response.status_code == 422
    assert managed(client) == before


def test_old_schema_migration_preserves_existing_campaign_and_claims(client):
    row = submit(client, patch(10, 3)).json()
    before = managed(client)
    with studio.database() as db:
        db.execute('ALTER TABLE patch_promotion DROP COLUMN remaining_adjustment')
    promo.initialize(studio.database, 'not-a-new-campaign')
    after = managed(client)
    assert after == before
    assert gift(client, row) == 3 and state(client)['remaining'] == 7
