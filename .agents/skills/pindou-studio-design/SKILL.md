---
name: pindou-studio-design
description: Design and refine the PinDou Puppy Hamilton studio website, its bilingual visit and pickup flows, and photo-led editorial sections while preserving the existing pattern generator. Use for this project's studio frontend and design reviews.
---

# PinDou Puppy studio design

Current product contract: read 02_product/STUDIO_VISION.md and the 46-item STUDIO_VISION_PROGRESS.md first. The owner now requests a cool palette, stacked single-photo hero, six-photo studio carousel, studio details, a paused shop/cart, and manual host-confirmed reservations. Public booking uses reservations.ts, ReservationCalendar.vue and 06_studio/reservations.py, not the payment cart. Its two-week window and weekday restrictions are enforced on the server. Unspecified unit/floor text is omitted. Earlier commerce requirements below are historical where they conflict.

The project root is `C:/Users/123/Desktop/PinDou`. Read `02_product/STUDIO_V1.md` for business truth and `03_design/STUDIO_DESIGN.md` for the current visual direction there. The studio frontend lives in `05_studio`; the incumbent generator is in `05_web` and must remain accessible.

Use the owner's actual photographs. Observe their spatial rhythm and colour relationships before choosing layout. A photo plus abstract colour composition may support the page, but must not redraw or misrepresent the studio. Image editing or new bitmap compositions use the available imagegen tool.

Design the landing as an invitation to make something: spacious photography and purposeful text. Design booking and pickup as practical forms: visible labels, clear validation, an honest summary, and a real completion state. These two surfaces need different density.

Keep Vue for this project. Source and install a library before importing it; use GSAP with a scoped context / matchMedia and dispose it on unmount. Preserve native scroll, readable content without animation, and prefers-reduced-motion.

Use project colour and typography tokens. Draw imagery and supporting colours from the supplied room and materials. Check Chinese wrapping and English length separately; switching languages must preserve the in-progress form and selection.

For interaction or host administration work, read `03_design/STUDIO_MOTION_AND_DESK.md`. The verified sources are the current local T-Check motion standard and the owner's `Shengqinchu/saas-playbook` frontend/admin specs on the `master` branch. Reuse the project's motion.ts clocks (300ms ease-in-out controls and selection, separate narrative/panel travel), `SegmentedControl`, `ToggleSwitch`, `SlideOver` and `StudioToast`. The host desk is an independent application surface: overview, searchable orders, calendar, products, checkout settings and activity. Keep editing drafts mounted across navigation; use server totals rather than calculating metrics from one paginated list. Read `03_design/STUDIO_0830_REVIEW.md` and `STUDIO_0830_RESPONSE.md` for concrete failures and corrected component ownership. Measure rendered fonts, title/badge sizes and real touch targets. Do not equate test counts with design acceptance. Bead assembly starts only after its parent is visible; short taps never retain an artificial pressed state. Respect reduced motion, native dialog focus, mobile navigation inertness and disabled/busy states. Dialog panels and scrims animate separately with reversible current-frame transitions. Use browser.ts visual-viewport and shared scroll-lock helpers for keyboard, rotation and WeChat webviews; keep touch inputs at least 16px and safe areas clear. Do not change the payment presentation from QR to cashier URL after it has been shown. Load admin code and styles only when visiting the host desk.

Booking dates are Hamilton local dates, with timezone America/Toronto. The owner has requested actual online checkout: select an available time, add to the shopping bag, pay through Hupijiao, then automatically confirm seats. Read `02_product/STUDIO_COMMERCE_V1.md` for the current transaction contract. Do not invent capacity, schedules, inventory or paid orders. Unpriced products remain drafts; unconfigured opening hours expose no available slots. The owner selected a fixed rate of 1 CAD = 5 CNY. Tax treatment still needs an explicit merchant setting. Server quotes own prices; payment confirmation requires provider evidence and atomic inventory fulfillment.

Preserve old generator routes, shared API routes and existing uncommitted work. Deploy studio previews additively under /studio/ on the existing server. Read the current ops runbook and verify the live Nginx rules before routing changes.

Verify desktop and phone layouts together, including keyboard focus, modal closing if used, failed submissions, cart persistence and timezone boundaries. Inspect the screenshots, batch fixes, then confirm only the changed or uncertain behavior. Record real unresolved business decisions separately from implementation defects.

Research provenance and upstream sources are in `03_design/STUDIO_DESIGN.md`; this skill is a project-specific adaptation, not a copy of the upstream skill packages.

The second review is `03_design/STUDIO_0830_REREVIEW.md`. Its N1–N6 establish specific finishing rules: fine-pointer-only hover; stationary host content coordinated with navigation; continuous photo reversal from the current opacity; same-item mobile navigation must close; inspect actual Chinese line endings; localize transport failures and accessible names without discarding meaningful business errors. Preserve the frozen reviewer evidence and verify these states directly after changes.
