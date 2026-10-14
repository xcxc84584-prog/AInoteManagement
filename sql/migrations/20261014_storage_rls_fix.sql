-- Apply in Supabase SQL Editor. Keeps storage private and scoped to authenticated user UUID.
DROP POLICY IF EXISTS "note images select" ON storage.objects;
DROP POLICY IF EXISTS "note images insert" ON storage.objects;
DROP POLICY IF EXISTS "note images update" ON storage.objects;
DROP POLICY IF EXISTS "note images delete" ON storage.objects;
CREATE POLICY "note images select" ON storage.objects FOR SELECT TO authenticated USING (bucket_id='note-images' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY "note images insert" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id='note-images' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY "note images update" ON storage.objects FOR UPDATE TO authenticated USING (bucket_id='note-images' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text) WITH CHECK (bucket_id='note-images' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY "note images delete" ON storage.objects FOR DELETE TO authenticated USING (bucket_id='note-images' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
