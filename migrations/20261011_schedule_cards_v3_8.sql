-- BV-Text v3.8: run once in Supabase SQL Editor after v3.6 migration.
-- Retain date independently of optional time; existing cards keep their Taiwan-local calendar date.
ALTER TABLE public.schedule_cards ADD COLUMN IF NOT EXISTS schedule_date date;
ALTER TABLE public.schedule_cards ADD COLUMN IF NOT EXISTS is_completed boolean NOT NULL DEFAULT false;
UPDATE public.schedule_cards SET schedule_date=(scheduled_at AT TIME ZONE 'Asia/Taipei')::date
WHERE schedule_date IS NULL AND scheduled_at IS NOT NULL;
ALTER TABLE public.schedule_cards ALTER COLUMN scheduled_at DROP NOT NULL;
ALTER TABLE public.schedule_cards ALTER COLUMN schedule_date SET NOT NULL;
CREATE INDEX IF NOT EXISTS schedule_cards_owner_date_idx ON public.schedule_cards(owner_id,schedule_date);
NOTIFY pgrst, 'reload schema';
