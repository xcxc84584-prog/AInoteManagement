-- Run in Supabase SQL Editor. Safe for existing notes; no rows are deleted.
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;
ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notes TO authenticated;
NOTIFY pgrst, 'reload schema';
-- Verify migration:
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='public' AND table_name='notes'
AND column_name IN ('is_deleted','deleted_at');
