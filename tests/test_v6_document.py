import unittest
from v6_core import Document, extract_toc, split_document, source_digest

class TestLosslessDocument(unittest.TestCase):
    def test_toc_and_math_unchanged(self):
        s='//[CPI]//\n$$\\frac{\\text{Cycles}}{\\text{Instructions}}$$\n//[CPI]//\n'
        doc=Document('pipeline',s)
        self.assertEqual(len(doc.toc),2)
        self.assertEqual([t['title'] for t in doc.toc],['CPI','CPI'])
        for _ in range(100):
            self.assertEqual(doc.source,s)
            self.assertEqual(doc.digest,source_digest(s))
    def test_split_preserves_bytes(self):
        d=Document('x','one\n//[two]//\n$$x_1$$')
        a,b=split_document(d,4)
        self.assertEqual(a.source+b.source,d.source)
    def test_revision_only_on_change(self):
        d=Document('x','hello')
        d.update('hello')
        self.assertEqual(d.revision,0)
        d.update('hello!')
        self.assertEqual(d.revision,1)

if __name__=='__main__': unittest.main()
