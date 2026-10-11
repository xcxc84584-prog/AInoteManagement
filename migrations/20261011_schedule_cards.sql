-- Run once in Supabase SQL Editor. Cards are private per authenticated user.
create table if not exists public.schedule_cards (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 200),
  scheduled_at timestamptz not null,
  details text not null default '' check (char_length(details) <= 10000),
  created_at timestamptz not null default now()
);
create index if not exists schedule_cards_owner_time_idx on public.schedule_cards(owner_id, scheduled_at);
alter table public.schedule_cards enable row level security;
drop policy if exists schedule_cards_owner_all on public.schedule_cards;
create policy schedule_cards_owner_all on public.schedule_cards for all to authenticated
  using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
