# Multi-brand phase 1 (development only)
- Quantity-based sandbox subscription, 9,900 KRW per extra brand, technical checkout ceiling 1,000. Existing one-unit subscriptions remain compatible. No real PG changes.
- Slot migration must be checked with both SQLite and private PostgreSQL on a backup before deployment. Downward changes retain stored profiles but disable access to slots outside purchased quantity.
- Independent basic profile, public link, private admin test, FAQ training target, files and history filter. The main business data is not inherited.
- Booking, CRM, quote catalog, lead/work requests and external channel configuration remain workspace-level. Extra-brand automation must fail closed until each of those data paths, recovery and webhook routing is explicitly scoped. Do not advertise complete feature sharing yet.
- Existing quotas and credits are account-level. No production deployment.
