-- BV-Text v6.25.6: Allow sanitized SVG assets in the existing private bucket.
-- Run once in Supabase SQL Editor with project-owner permissions.
UPDATE storage.buckets
SET allowed_mime_types = ARRAY[
  'image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml'
]
WHERE id = 'note-images';
