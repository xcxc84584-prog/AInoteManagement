-- Optional: run in Supabase SQL Editor before manually syncing tagged schedule cards.
ALTER TABLE public.schedule_cards ADD COLUMN IF NOT EXISTS batch_tag text;
ALTER TABLE public.schedule_cards ADD COLUMN IF NOT EXISTS batch_id text;
CREATE INDEX IF NOT EXISTS schedule_cards_owner_batch_tag_idx ON public.schedule_cards(owner_id,batch_tag);
