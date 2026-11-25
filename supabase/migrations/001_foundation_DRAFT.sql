-- TARGET SCHEMA DRAFT: NOT APPLIED OR VALIDATED ON SUPABASE.
-- The current runtime is SQLite. Port repository methods and API auth before using this.
begin;
create extension if not exists btree_gist;
create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  slug text not null unique,
  settings jsonb not null default '{}',
  enabled boolean not null default false,
  created_at timestamptz not null default now()
);
create table public.memberships (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check(role in ('owner','admin','staff')),
  primary key(workspace_id,user_id)
);
create table public.agents (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null, settings jsonb not null default '{}', unique(workspace_id,id)
);
create table public.agent_versions (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  agent_id uuid not null, status text not null check(status in ('draft','approved','archived')),
  rules jsonb not null default '{}', created_at timestamptz not null default now(),
  foreign key(workspace_id,agent_id) references public.agents(workspace_id,id)
);
create table public.knowledge_files (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null, sha256 text not null, private_storage_key text not null, created_at timestamptz not null default now(), unique(workspace_id,sha256)
);
create table public.conversations (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  channel text not null, external_key_hash text not null, status text not null default 'open',
  manual boolean not null default false, created_at timestamptz not null default now(), unique(workspace_id,id)
);
create table public.messages (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  conversation_id uuid not null, role text not null check(role in ('user','assistant','staff')), body text not null, created_at timestamptz not null default now(),
  foreign key(workspace_id,conversation_id) references public.conversations(workspace_id,id)
);
create table public.booking_templates (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  version integer not null check(version>0), fields jsonb not null, policy jsonb not null, unique(workspace_id,id)
);
create table public.booking_requests (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  template_id uuid not null, payload jsonb not null, status text not null, customer_confirmed_at timestamptz,
  payment_verified_at timestamptz, created_at timestamptz not null default now(), unique(workspace_id,id),
  foreign key(workspace_id,template_id) references public.booking_templates(workspace_id,id)
);
create table public.bookings (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  request_id uuid not null unique, resource_id uuid not null, start_at timestamptz not null, end_at timestamptz not null,
  status text not null check(status in ('confirmed','cancelled','completed')), payload jsonb not null default '{}',
  foreign key(workspace_id,request_id) references public.booking_requests(workspace_id,id), check(end_at>start_at),
  exclude using gist(workspace_id with =,resource_id with =,tstzrange(start_at,end_at,'[)') with &&) where(status='confirmed')
);
create table public.subscriptions (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  provider_id text unique, plan text not null, status text not null, period_start timestamptz, period_end timestamptz
);
create table public.entitlements (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  sku text not null, valid_until timestamptz, primary key(workspace_id,sku)
);
create table public.credit_ledger (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  delta bigint not null, reason text not null, idempotency_key text not null, created_at timestamptz not null default now(), unique(workspace_id,idempotency_key)
);
create table public.usage_ledger (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  period_start timestamptz not null, idempotency_key text not null, state text not null check(state in ('reserved','committed','released')),
  created_at timestamptz not null default now(), unique(workspace_id,idempotency_key)
);
create table public.webhook_events (
  provider text not null,event_id text not null, received_at timestamptz not null default now(), status text not null, primary key(provider,event_id)
);
-- All mutations are through trusted backend. Only read access for authenticated members.
create function public.is_workspace_member(w uuid) returns boolean language sql stable security definer set search_path='' as $$
  select exists(select 1 from public.workspaces x where x.id=w and x.owner_id=auth.uid())
  or exists(select 1 from public.memberships m where m.workspace_id=w and m.user_id=auth.uid())
$$;
revoke all on function public.is_workspace_member(uuid) from public;
grant execute on function public.is_workspace_member(uuid) to authenticated;
alter table public.workspaces enable row level security;
create policy workspace_read on public.workspaces for select to authenticated using(public.is_workspace_member(id));
do $$ declare t text; begin
  foreach t in array array['memberships','agents','agent_versions','knowledge_files','conversations','messages','booking_templates','booking_requests','bookings','subscriptions','entitlements','credit_ledger','usage_ledger'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('create policy member_read on public.%I for select to authenticated using(public.is_workspace_member(workspace_id))',t);
  end loop;
end $$;
alter table public.webhook_events enable row level security;
-- TODO: production booking/credit atomic RPCs, grants by role, storage RLS, PII access,
-- customer session tokens, retention/deletion, full schema coverage, migration rehearsals.
commit;
