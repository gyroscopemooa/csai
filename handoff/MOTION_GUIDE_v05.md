# CS AI v0.4 — motion and interaction guide

## References for Codex / Claude Code
- MotionSites: https://www.motionsites.ai/ — landing/page motion inspiration; official MCP: https://www.motionsites.ai/mcp
- Motion AI Kit: https://motion.dev/docs/ai-kit — motion patterns and agent guidance
- 21st: https://21st.dev/ — component references
- Motion Primitives: https://motion-primitives.com/
- React Bits: https://reactbits.dev/
- Aceternity UI: https://ui.aceternity.com/
- Magic UI: https://magicui.design/

Current stack is FastAPI + plain JavaScript/CSS. The implemented v0.4 effects are original CSS/JS; no premium prompts, external assets, MCP installation or React dependencies are included. Before introducing libraries, check framework compatibility, licensing, bundle size and accessibility. Do not rewrite the backend or change the pricing, entitlements, data storage, or authorization to adopt visual components.

## Implemented
- Landing hero: soft blue-white radial backdrop, staged text and login controls.
- Buttons: short press/hover feedback; keyboard focus retained.
- Admin route heading: restrained entry motion.
- Modal and toast: brief transitions.
- Chat: pending indicator tied to the actual in-flight request; remove on success or failure; animate newly added messages only. No fake progress or response text.
- AI education: pending indicator tied to actual analysis; recoverable error UI.
- Reduced motion: CSS disables animations and transitions for OS preference.

## Design rules
Toss-inspired clean light surfaces, #3182F6 accent, round corners, readable typography. 150–240 ms micro-interactions; a single initial hero reveal under 600 ms. Favor opacity and transform. No forced scrolling, video backgrounds, continuous decoration, artificial waiting, or motion that obstructs mobile customer chat. Keep QR, auth, pricing, booking and upload controls fully usable. For future design work, select a relevant reference rather than copying whole pages or gated assets.

## Acceptance
Run `node --check web/app.js`, `python -m pytest -q`, and `python tests/browser_check.py` (Playwright/Chromium required for the last). Check at 390px and desktop, verify keyboard and reduced-motion preference, actual pending state, failed network retry and all paid-feature restrictions. External service credentials are still required for live integration.
