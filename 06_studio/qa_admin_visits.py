"""Disposable loopback-only browser fixture; no notification workers or live credentials."""
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException, Request
import app as studio
import customer_auth
import reservations
import content
from auth_fixture import fake_upstream

studio.DB_PATH = Path(tempfile.mkdtemp(prefix='pindou-admin-visits-')) / 'qa.sqlite3'
customer_auth.upstream = fake_upstream
reservations.COOKIE_SECURE = False
content.SITE_PATH = Path(__file__).resolve().parents[1] / '05_studio/dist/index.html'


def local_admin(request: Request):
    if request.headers.get('authorization') != 'Bearer local-admin-visits':
        raise HTTPException(401, 'Administrator sign-in required')
    return 'local-admin-visits'


@asynccontextmanager
async def local_lifespan(_app):
    studio.initialize()
    yield


studio.app.dependency_overrides[studio.admin_actor] = local_admin
studio.app.router.lifespan_context = local_lifespan

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(studio.app, host='127.0.0.1', port=8127, access_log=False)
