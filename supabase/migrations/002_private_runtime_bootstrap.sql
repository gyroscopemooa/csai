-- Run once in the dedicated CS AI Supabase project before enabling PostgreSQL.
-- Does not touch public tables or the earlier draft migration.
BEGIN;
CREATE SCHEMA IF NOT EXISTS csai_private;
REVOKE ALL ON SCHEMA csai_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA csai_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA csai_private FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA csai_private REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA csai_private REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
COMMIT;
-- Server startup creates its own tables in csai_private and enables RLS.
-- Never add this schema to Supabase exposed API schemas.
