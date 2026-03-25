# UX & design notes (Voice2Sign web app)

## Role-specific dashboards

- **Hearing:** Voice → Sign is listed first — optimized for speech input and reading sign output.
- **Deaf / HoH:** Sign → Voice is listed first — camera and signing prioritized; voice input is secondary.
- **Admin:** Extra **Admin** section with DB-backed stats (`GET /api/admin/stats`). Admins are created via environment seed (`ADMIN_EMAIL` / `ADMIN_PASSWORD`), not public signup.

## Responsiveness

- Sidebar collapses to an overlay on small screens; use the header menu button.
- Touch targets stay ≥ 44px where possible (nav items, pipeline buttons).
- Header wraps (`flex-wrap`) so mic status + auth links stack cleanly on narrow phones.
- Prefer **single column** pipeline grids below ~900px (already in CSS).

## Microphone feedback

- **Web Audio API** drives level bars when a mic stream is active (chat composer or Voice → Sign pipeline).
- Respects **reduced motion** (`prefers-reduced-motion` / preference toggle) for calmer animations.

## Accessibility & inclusion

- Keep **high contrast** and **reduced motion** toggles in Preferences.
- Ensure captions / transcripts remain visible for deaf users when voice features are used.
- Test with OS screen readers and browser zoom at 200%.

## Recommended next design steps

1. **Larger sign video** on the deaf-first layout (full-width on mobile).
2. **Consistent iconography** for “sound on/off” vs “mic active” (already partially separated).
3. **Offline banner** when `/api/health` fails.
4. **Skeleton loaders** for admin stats and chat history.
5. **Dark mode** contrast audit (WCAG AA for text on `--bg-primary`).

## Database

- Roles are stored in `users.user_type` (`hearing` | `deaf` | `admin`). Use Alembic when you evolve the schema in production.
