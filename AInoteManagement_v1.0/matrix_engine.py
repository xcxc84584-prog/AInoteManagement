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
    """Safe bounded recursion, zero-based indices, and atomic grid calculation."""
    raw=formula.strip()
    precision=None
    # v3.0: optional f(row,column)= prefix; optional <digits> precision suffix.
    # Legacy f(row,column)=(expression)<digits> is accepted as well.
    raw=re.sub(r'^f\s*\(\s*row\s*,\s*column\s*\)\s*=\s*','',raw,count=1)
    suffix=re.search(r'(?:@\s*(\d{1,2})|<\s*(\d{1,2})\s*>)\s*$',raw)
    if suffix:
        precision=int(suffix.group(1) or suffix.group(2))
        if precision>15:raise ValueError('浮點數精度必須介於 0–15')
        raw=raw[:suffix.start()].strip()
    expression=raw
    if expression.startswith('(') and expression.endswith(')'):
        # Remove only one balanced outer pair.
        try:
            if ast.parse(expression,mode='eval'): expression=expression[1:-1].strip()
        except SyntaxError:
            pass
    if not expression or len(expression)>1000:raise ValueError('運算式長度必須介於 1–1000')
    # A stop predicate belongs to the preceding recursive f(...) call.
    expression=re.sub(r'\&\&',' and ',expression)
    expression=re.sub(r'\|\|',' or ',expression)
    expression=re.sub(r'(?<![<>=!])=(?!=)','==',expression)
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
    try:tree=ast.parse(expression,mode='eval')
    except SyntaxError as exc:raise ValueError('運算式語法錯誤') from exc
    if sum(1 for _ in ast.walk(tree))>180:raise ValueError('運算式過於複雜')
    def ev(node,row,column,depth,steps):
        steps[0]+=1
        if steps[0]>20000:raise ValueError('運算步驟超出上限，已終止')
        if isinstance(node,ast.Expression):return ev(node.body,row,column,depth,steps)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float,bool):return int(node.value) if isinstance(node.value,bool) else node.value
        if isinstance(node,ast.Name):
            if node.id=='row':return row
            if node.id=='column':return column
            if re.fullmatch(r'_m\d+',node.id) and int(node.id[2:])<len(ranges):return ranges[int(node.id[2:])]
            raise ValueError('未知變數：'+node.id)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd,ast.Not,ast.Invert)):
            v=ev(node.operand,row,column,depth,steps)
            if isinstance(node.op,ast.USub):return -v
            if isinstance(node.op,ast.UAdd):return +v
            if isinstance(node.op,ast.Not):return int(not v)
            return ~int(v)
        if isinstance(node,ast.BoolOp) and isinstance(node.op,(ast.And,ast.Or)):
            if isinstance(node.op,ast.And):
                for v in node.values:
                    if not ev(v,row,column,depth,steps):return 0
                return 1
            for v in node.values:
                if ev(v,row,column,depth,steps):return 1
            return 0
        if isinstance(node,ast.Compare):
            left=ev(node.left,row,column,depth,steps)
            for op,part in zip(node.ops,node.comparators):
                right=ev(part,row,column,depth,steps)
                operators={ast.Lt:lambda a,b:a<b,ast.LtE:lambda a,b:a<=b,ast.Eq:lambda a,b:a==b,ast.GtE:lambda a,b:a>=b,ast.Gt:lambda a,b:a>b,ast.NotEq:lambda a,b:a!=b}
                if type(op) not in operators or isinstance(left,Matrix) or isinstance(right,Matrix):raise ValueError('不支援的比較式')
                if not operators[type(op)](left,right):return 0
                left=right
            return 1
        if isinstance(node,ast.Call):
            if node.keywords:raise ValueError('函數不支援命名參數')
            if isinstance(node.func,ast.Name) and node.func.id in ('if','choose'):
                if len(node.args)!=3:raise ValueError('choose(條件,成立值,否則值) 需要三個參數')
                return ev(node.args[1] if ev(node.args[0],row,column,depth,steps) else node.args[2],row,column,depth,steps)
            stop_condition=None
            stop_value=None
            inner=node
            if isinstance(node.func,ast.Attribute) and node.func.attr=='stop':
                inner=node.func.value
                if len(node.args) not in (1,2):raise ValueError('stop(條件,回傳值) 最多兩個參數')
                stop_condition=node.args[0]
                stop_value=node.args[1] if len(node.args)==2 else None
            if not isinstance(inner,ast.Call) or not isinstance(inner.func,ast.Name) or inner.func.id!='f' or len(inner.args)!=2 or inner.keywords:
                raise ValueError('僅允許 choose(...)、f(row,column) 和 f(...).stop(...)')
            nr=ev(inner.args[0],row,column,depth,steps)
            nc=ev(inner.args[1],row,column,depth,steps)
            if not all(isinstance(x,(int,float)) and math.isfinite(x) and x==int(x) for x in (nr,nc)):
                raise ValueError('遞迴座標必須為整數')
            nr,nc=int(nr),int(nc)
            if stop_condition is not None and ev(stop_condition,nr,nc,depth,steps):
                return ev(stop_value,nr,nc,depth,steps) if stop_value is not None else 0
            if depth>=64:raise ValueError('遞迴超過 64 層，可能缺少有效終止條件')
            return ev(tree.body,nr,nc,depth+1,steps)
        if isinstance(node,ast.BinOp):
            a=ev(node.left,row,column,depth,steps);b=ev(node.right,row,column,depth,steps)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
            if isinstance(a,Matrix) or isinstance(b,Matrix):raise ValueError('矩陣只支援加、減、乘')
            if isinstance(node.op,ast.Div):return a/b
            if isinstance(node.op,ast.FloorDiv):return a//b
            if isinstance(node.op,ast.Mod):return a%b
            if isinstance(node.op,ast.BitAnd):return int(a)&int(b)
            if isinstance(node.op,ast.BitOr):return int(a)|int(b)
            if isinstance(node.op,ast.Pow):
                if abs(b)>20:raise ValueError('指數過大')
                return a**b
        raise ValueError('不支援的運算式')
    t,l,b,r=selection
    if t<0 or l<0 or b<t or r<l or (b-t+1)*(r-l+1)>2000:raise ValueError('選取範圍無效')
    def check(value):
        if isinstance(value,Matrix):return value
        if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('計算結果不是有限數值')
        return round(value,precision) if precision is not None else value
    try:
        first=ev(tree,t,l,0,[0])
        if isinstance(first,Matrix):
            rows,cols=first.shape
            return [[check(first.values[i][j]) if i<rows and j<cols else math.nan for j in range(r-l+1)] for i in range(b-t+1)]
        result=[]
        for i in range(t,b+1):
            line=[]
            for j in range(l,r+1):
                value=first if i==t and j==l else ev(tree,i,j,0,[0])
                if isinstance(value,Matrix):raise ValueError('同一公式不能混用矩陣與純量結果')
                line.append(check(value))
            result.append(line)
        return result
    except (ZeroDivisionError,OverflowError,RecursionError) as exc:raise ValueError('運算失敗：除以零、數值溢位或遞迴過深') from exc
