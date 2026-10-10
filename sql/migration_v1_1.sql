-- Execute once in Supabase SQL Editor. Preserves existing notes and assets.
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notes TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assets TO authenticated;
CREATE INDEX IF NOT EXISTS notes_owner_deleted_idx ON public.notes(owner_id,is_deleted,parent_id,position);
