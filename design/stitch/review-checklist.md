# Stitch Export Review Checklist

Run this checklist before translating any Stitch export into production React code.

- [ ] Mode badge is visible on every screen.
- [ ] Kill switch is always visible or one click away from every screen.
- [ ] No raw broker/model/API secrets are visible in text, attributes, mocks, or comments.
- [ ] No landing-page hero, marketing section, or decorative card-in-card layout.
- [ ] Body text contrast is at least 4.5:1.
- [ ] Interactive controls have visible focus states.
- [ ] Primary controls have at least 44px touch/click targets.
- [ ] Reduced-motion users can operate the interface without animation dependence.
- [ ] Tables do not overflow without horizontal scrolling on narrow screens.
- [ ] Red is reserved for blocked, killed, or critical states.
- [ ] Green is reserved for verified safe states.
- [ ] Holdout test metrics are labeled as report-only, not selection criteria.
- [ ] Paper execution controls are visibly disabled unless backend mode is `paper` and confirmation is present.
- [ ] Exported HTML/CSS is translated to semantic React components and real API contracts before use.