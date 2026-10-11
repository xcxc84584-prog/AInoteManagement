-- Execute in Supabase SQL Editor after reviewing the existing schema.
BEGIN;
ALTER TABLE public.notes DROP CONSTRAINT IF EXISTS notes_kind_check;
ALTER TABLE public.notes ADD CONSTRAINT notes_kind_check
 CHECK (kind IN ('GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE','HANDWRITE','COMPOSITE'));
COMMIT;
