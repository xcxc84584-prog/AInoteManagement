CREATE TABLE IF NOT EXISTS public.daily_tasks (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
 no_time boolean NOT NULL DEFAULT true,
 task_time time,
 details text NOT NULL DEFAULT '',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.daily_task_checks (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 task_id uuid NOT NULL REFERENCES public.daily_tasks(id) ON DELETE CASCADE,
 task_date date NOT NULL,
 is_completed boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,task_id,task_date)
);
ALTER TABLE public.daily_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_task_checks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS daily_tasks_owner_all ON public.daily_tasks;
CREATE POLICY daily_tasks_owner_all ON public.daily_tasks FOR ALL TO authenticated
 USING(owner_id=(SELECT auth.uid())) WITH CHECK(owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS daily_task_checks_owner_all ON public.daily_task_checks;
CREATE POLICY daily_task_checks_owner_all ON public.daily_task_checks FOR ALL TO authenticated
 USING(owner_id=(SELECT auth.uid())) WITH CHECK(owner_id=(SELECT auth.uid()));
NOTIFY pgrst, 'reload schema';
