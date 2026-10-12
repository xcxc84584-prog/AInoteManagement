import unittest
from v6_core import Document, extract_toc, split_document, source_digest
from v6_core.toc_store import create_entry, locate_entry
class TestV61(unittest.TestCase):
 def test_legacy_markers_are_plain_text(self):
  s='//[old]//\n\\[\\frac{a}{b}\\]\n'
  d=Document('x',s)
  self.assertEqual(d.toc,[])
  self.assertEqual(extract_toc(s),[])
  for _ in range(100): self.assertEqual(d.digest,source_digest(s))
 def test_toc_does_not_change_source(self):
  s='alpha\nbeta target\ngamma';digest=source_digest(s)
  entry=create_entry('doc1',s,s.index('target'),s.index('target')+6)
  self.assertEqual((entry.line_start,entry.column_start),(2,5))
  self.assertEqual(locate_entry(s,entry),(2,5))
  self.assertEqual(source_digest(s),digest)
 def test_relocation_unique_and_ambiguity(self):
  s='one\ntarget';e=create_entry('doc',s,4,10)
  self.assertEqual(locate_entry('new\none\ntarget',e),(3,0))
  self.assertIsNone(locate_entry('target\nother\ntarget',e))
 def test_split_lossless(self):
  d=Document('x','one\n\\(x\\)\n')
  a,b=split_document(d,4)
  self.assertEqual(a.source+b.source,d.source)
if __name__=='__main__':unittest.main()
