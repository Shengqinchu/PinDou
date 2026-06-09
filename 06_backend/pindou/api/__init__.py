"""API router registry."""

from fastapi import APIRouter

from pindou.api import admin, artwork, cdk, generate, pattern, payment, upload, user, wallet

api_router = APIRouter()

for router in (
    upload.router,
    generate.router,
    generate.preview_router,
    pattern.router,
    artwork.router,
    user.router,
    payment.router,
    payment.webhook_router,
    cdk.router,
    wallet.router,
    admin.router,
):
    api_router.include_router(router)
