# 2026-09-09 · Responsive interactions and in-page sign-in

The owner reported undersized booking content on large displays, clipped input
focus rings, incomplete title and motif interactions, flickering duo offers,
and a login drawer that redirected to the hosted Authing page. Email codes are
now explicitly reserved for account recovery.

## Interaction and layout

- Booking width grows from the compact 950 px layout to a maximum of 1480 px.
  Spacious displays get larger type and controls. Very tall screens cap the
  working area's height so the action does not drift far below the content.
- Short windows retain an internal scrolling area and visible actions; input
  focus outlines draw inside the field. Picker clipping only applies while a
  date/details transition is actually running.
- Refreshing availability retains the duo card's element and full opacity.
  Selecting it checks the currently published offer; the next time selection
  and final submission still revalidate availability and the offer revision.
- Guest choices, plans and time buttons use the existing 300 ms tactile clock.
  Public and generator display headings share grapheme-level lift/hold/return.
  The original puppy and star artwork uses the existing layered squeeze effect.
- OS/site reduced-motion preference remains authoritative.

## Sign-in

The drawer offers WeChat and password choices. The QR is generated and shown in
the current page. Only the Studio server polls its QR ID and exchanges the
provider-issued ticket; the browser supplies its own random state and HttpOnly
same-origin cookie. It cannot supply an Authing user, ticket or QR ID. Existing
OIDC callbacks retain issuer/audience/nonce/signature/PKCE checks for flows that
started before the upgrade.

The provider integration follows Authing's documented `WXAPP_AUTH` generation,
status and ticket exchange APIs. The application ID and HTTPS provider host are
fixed server configuration. Authorized identity data comes directly from that
app's provider response. Provider credentials and tickets never reach URLs,
local storage or user-facing errors.

Sources: [Authing QR SDK reference](https://docs.authing.cn/v2/reference/sdk-for-node/authentication/QrCodeAuthenticationClient.html),
[Authing mini-program QR flow](https://docs.authing.cn/v2/guides/connections/social/wechat-miniprogram-qrconnect/).
This configured mini-program flow requires a WeChat scan/confirmation. It does
not expose a way for the site to reuse the desktop WeChat app's logged-in state.

An already-bound identity returns to the same shared account. A first-time QR
offers explicit existing-account binding (password proof first) or new-account
creation. New WeChat accounts use a deterministic, separately named generator
identity. Legacy development `wx_` identities remain ineligible for Studio.
No matching or merging by nickname, contact email or phone is performed.

Email code login/registration routes return 410. Public generator equivalents
are also blocked at Nginx. Recovery uses a separate code table, a five-minute
expiry, five verification attempts, resend/email/IP/global limits, and an atomic
password update. Unknown addresses receive the same response without sending
mail. A recovery code neither registers a customer nor issues a session.

## Deployment and verification

Only two generator backend files change: `api/studio_session.py` and the new
`services/studio_accounts.py`. The deployer overlays them onto the captured live
release and checks that every other existing source/asset is byte-identical.
The workstation's unrelated `05_web` and `06_backend` edits are excluded. Both
databases are backed up; release links and services have a rollback path.

Evidence is recorded under `artifacts/ui-auth-refinement/`. Tests cover server
identity/state/origin isolation, existing-account preservation, new-account
idempotency, recovery failure/expiry/replay, multi-viewport booking states,
continuous-frame offer stability, tactile/motif/title interactions, English
and Chinese UI, cancellation/draft preservation, and Chromium/WebKit. Email
delivery and paid generation are mocked in local tests; real WeChat confirmation
can only be completed by the owner on their phone.
