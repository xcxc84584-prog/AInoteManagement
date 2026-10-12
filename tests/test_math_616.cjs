const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const part of ['composite_editor','composite_reader']){
 const html=fs.readFileSync(`components/${part}/index.html`,'utf8');
 const start=html.indexOf('function bvMathNormalizeNested(source){');
 const end=html.indexOf('function mathMarkup(',start);
 assert(start>=0&&end>start);
 const code=html.slice(start,end);
 const context={hrcImageTokens:(s)=>({prepared:s,tokens:[]})};vm.createContext(context);vm.runInContext(code,context);
 const samples=[
  [String.raw`\[$$CPI=1+0.2\times0.4\times3$$\]`,String.raw`\[CPI=1+0.2\times0.4\times3\]`],
  [String.raw`\[$$CPI=\frac{\text{Total Clock Cycles}}{\text{Instruction Count}}$$\]`,String.raw`\[CPI=\frac{\text{Total Clock Cycles}}{\text{Instruction Count}}\]`],
  [String.raw`$$P(A\mid B)=\frac{P(B\mid A)P(A)}{P(B)}$$`,String.raw`$$P(A\mid B)=\frac{P(B\mid A)P(A)}{P(B)}$$`]
 ];
 for(const [input,expected] of samples)assert.strictEqual(context.bvMathNormalizeNested(input),expected);
 const fenced='```\n'+samples[0][0]+'\n```';assert.strictEqual(context.bvMathNormalizeNested(fenced),fenced);
 console.log(part+': 4 math normalization checks passed');
}
