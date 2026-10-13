-- Run once in Supabase SQL Editor as the project owner.
-- Table grants are separate from row-level security policies.
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.daily_tasks TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.daily_task_checks TO authenticated;
ALTER TABLE public.daily_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_task_checks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS daily_tasks_owner_all ON public.daily_tasks;
CREATE POLICY daily_tasks_owner_all ON public.daily_tasks FOR ALL TO authenticated
 USING (owner_id = (SELECT auth.uid())) WITH CHECK (owner_id = (SELECT auth.uid()));
DROP POLICY IF EXISTS daily_task_checks_owner_all ON public.daily_task_checks;
CREATE POLICY daily_task_checks_owner_all ON public.daily_task_checks FOR ALL TO authenticated
 USING (owner_id = (SELECT auth.uid())) WITH CHECK (owner_id = (SELECT auth.uid()));
NOTIFY pgrst, 'reload schema';
