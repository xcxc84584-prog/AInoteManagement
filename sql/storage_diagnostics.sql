-- Read-only checks for existing private note-images bucket and policies.
SELECT id,name,public FROM storage.buckets WHERE id='note-images';
SELECT policyname,cmd,roles,qual,with_check FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname LIKE 'note images %';
-- Expected object path: <authenticated-user-uuid>/<random-filename>.webp
-- No RLS policy replacement required if existing policies enforce this pattern.
