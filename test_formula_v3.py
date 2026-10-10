import unittest
from matrix_engine import calculate
C=[['0']*4 for _ in range(12)]
class TestFormula(unittest.TestCase):
    def test_legacy(self):
        self.assertEqual(calculate('f(row,column)=(row*2+column)<3>',C,(0,0,2,1)),[[0,1],[2,3],[4,5]])
    def test_simple(self):
        self.assertEqual(calculate('row/3@2',C,(1,0,2,0)),[[0.33],[0.67]])
    def test_fibonacci(self):
        self.assertEqual([r[0] for r in calculate('choose(row<=1,row,f(row-1,column)+f(row-2,column))@0',C,(0,0,9,0))],[0,1,1,2,3,5,8,13,21,34])
    def test_atomic_failure(self):
        with self.assertRaises(ValueError):calculate('1/(row-row)',C,(0,0,2,0))
        self.assertEqual(C[0][0],'0')
if __name__=='__main__':unittest.main()
