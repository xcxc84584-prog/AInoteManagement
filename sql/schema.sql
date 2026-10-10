create extension if not exists pgcrypto;
create table if not exists public.notes (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id) on delete cascade,
 parent_id uuid references public.notes(id) on delete cascade,
 kind text not null check (kind in ('GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE','HANDWRITE')),
 title text not null,
 content text not null default '',
 has_page boolean not null default false,
 position integer not null default 0,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists notes_owner_parent_idx on public.notes(owner_id,parent_id,position);
create table if not exists public.assets (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id) on delete cascade,
 note_id uuid references public.notes(id) on delete set null,
 storage_path text not null,
 mime_type text not null,
 created_at timestamptz not null default now()
);
alter table public.notes enable row level security;
alter table public.assets enable row level security;
create policy "notes owner read" on public.notes for select to authenticated using (owner_id = (select auth.uid()));
create policy "notes owner insert" on public.notes for insert to authenticated with check (owner_id = (select auth.uid()));
create policy "notes owner update" on public.notes for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "notes owner delete" on public.notes for delete to authenticated using (owner_id = (select auth.uid()));
create policy "assets owner read" on public.assets for select to authenticated using (owner_id = (select auth.uid()));
create policy "assets owner insert" on public.assets for insert to authenticated with check (owner_id = (select auth.uid()));
create policy "assets owner delete" on public.assets for delete to authenticated using (owner_id = (select auth.uid()));
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types) values ('note-images','note-images',false,20971520,array['image/png','image/jpeg','image/webp','image/gif']) on conflict (id) do nothing;
create policy "note images select" on storage.objects for select to authenticated using (bucket_id = 'note-images' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "note images insert" on storage.objects for insert to authenticated with check (bucket_id = 'note-images' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "note images delete" on storage.objects for delete to authenticated using (bucket_id = 'note-images' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- v1.1 additions for fresh installs
-- Execute once in Supabase SQL Editor. Preserves existing notes and assets.
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notes TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assets TO authenticated;
CREATE INDEX IF NOT EXISTS notes_owner_deleted_idx ON public.notes(owner_id,is_deleted,parent_id,position);
