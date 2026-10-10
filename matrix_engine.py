"""Safe spreadsheet range formula evaluation. No eval or executable Python."""
import ast
import math
import re
from dataclasses import dataclass

RANGE = re.compile(r'A\[(\d+)\s*,\s*(\d+)\]\[(\d+)\s*,\s*(\d+)\]')

@dataclass
class Matrix:
    values: list
    @property
    def shape(self): return len(self.values), len(self.values[0]) if self.values else 0
    def __mul__(self, other):
        if isinstance(other, Matrix):
            m,k=self.shape;k2,n=other.shape
            if k!=k2: raise ValueError(f'矩陣維度不相容：{m}×{k} 無法乘以 {k2}×{n}')
            return Matrix([[sum(self.values[i][p]*other.values[p][j] for p in range(k)) for j in range(n)] for i in range(m)])
        return Matrix([[v*other for v in row] for row in self.values])
    def __rmul__(self,other): return self*other
    def __add__(self,other):
        if isinstance(other,Matrix):
            if self.shape!=other.shape: raise ValueError('矩陣相加的維度必須相同')
            return Matrix([[a+b for a,b in zip(ra,rb)] for ra,rb in zip(self.values,other.values)])
        return Matrix([[v+other for v in row] for row in self.values])
    def __radd__(self,other): return self+other
    def __sub__(self,other): return self+(-1*other)
    def __rsub__(self,other): return -1*self+other

def calculate(formula, cells, selection):
    """0-based coordinates. selection=(top,left,bottom,right). Return a rectangular grid of numbers/NaN."""
    expression=formula.strip()
    expression=re.sub(r'^f\s*\(\s*row\s*,\s*column\s*\)\s*=\s*','',expression)
    if not expression or len(expression)>500: raise ValueError('請輸入長度不超過 500 字元的計算式')
    ranges=[]
    def replace(m):
        r1,c1,r2,c2=map(int,m.groups())
        if r2<r1 or c2<c1 or r2-r1>100 or c2-c1>100:raise ValueError('矩陣範圍無效或過大')
        vals=[]
        for r in range(r1,r2+1):
            line=[]
            for c in range(c1,c2+1):
                try:line.append(float(cells[r][c]))
                except (IndexError,TypeError,ValueError):raise ValueError(f'矩陣 A[{r},{c}] 必須包含數值')
            vals.append(line)
        ranges.append(Matrix(vals))
        return f'_m{len(ranges)-1}'
    expression=RANGE.sub(replace,expression)
    tree=ast.parse(expression,mode='eval')
    allowed={ast.Add,ast.Sub,ast.Mult,ast.Div,ast.FloorDiv,ast.Mod,ast.Pow}
    def ev(node,row,column):
        if isinstance(node,ast.Expression):return ev(node.body,row,column)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.Name):
            if node.id=='row':return row
            if node.id=='column':return column
            if re.fullmatch(r'_m\d+',node.id) and int(node.id[2:])<len(ranges):return ranges[int(node.id[2:])]
            raise ValueError('未知變數：'+node.id)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            v=ev(node.operand,row,column);return -v if isinstance(node.op,ast.USub) else v
        if isinstance(node,ast.BinOp) and type(node.op) in allowed:
            a,b=ev(node.left,row,column),ev(node.right,row,column)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
            if isinstance(a,Matrix) or isinstance(b,Matrix):raise ValueError('矩陣目前只支援乘法與加減')
            if isinstance(node.op,ast.Div):return a/b
            if isinstance(node.op,ast.FloorDiv):return a//b
            if isinstance(node.op,ast.Mod):return a%b
            if isinstance(node.op,ast.Pow):
                if abs(b)>20:raise ValueError('指數過大')
                return a**b
        raise ValueError('不支援的運算式（禁止函式呼叫與任意程式碼）')
    t,l,b,r=selection
    if t<0 or l<0 or b<t or r<l or (b-t+1)*(r-l+1)>2000:raise ValueError('選取範圍無效')
    first=ev(tree,t,l)
    if isinstance(first,Matrix):
        rows,cols=first.shape
        return [[first.values[i][j] if i<rows and j<cols else math.nan for j in range(r-l+1)] for i in range(b-t+1)]
    return [[ev(tree,i,j) for j in range(l,r+1)] for i in range(t,b+1)]
