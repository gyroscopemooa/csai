# DesignBookmark motion integration
User supplied full standalone HTML source for Date Range and Star Rating (https://designbookmark.com/motion).
- Date Range: actual business dates, no demo autoplay or disabled historical days; inclusive range selection, hover/drag preview, 0.19s fade-in/out with original cubic curves, clipped endpoint circles, spring month slide (420/41), height (260/24), rollers (420/32). Preserve calendar booking counts, statuses, date filters and manual booking.
- Star Rating: original path, fill 300/24, pop 520/13, text roll 260/22, 50ms per-star stagger, pointer hover and committed selection; separate ratings and explicit submission. Native keyboard radios, no demo autoplay.
- Shared physics uses original semi-implicit integration and four substeps, stops at rest/unmount; reduced motion snaps. Scope styles and remove demo global theme/parent-message/autoplay code. CSAI blue for range, original yellow for ratings, existing system font and radii.
- Browser/production verification remains required. No production deployment.
