-- Run once in Supabase SQL Editor before deploying v2.5.
ALTER TABLE public.notes DROP CONSTRAINT IF EXISTS notes_kind_check;
ALTER TABLE public.notes ADD CONSTRAINT notes_kind_check CHECK (kind IN ('GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE','HANDWRITE'));
