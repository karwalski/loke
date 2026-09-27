# gen.py K : writes t54lib.tk with K struct types (each has a field `body` at offset 0)
# and repro_import.tk, which imports std.http and t54lib and reads r.body from a $httpresp.
import sys
K=int(sys.argv[1])
ts='\n'.join('t=$l%02d{body:str;k%02d:i64};'%(i,i) for i in range(1,K+1))
open('t54lib.tk','w').write('(* T-54 helper: %d struct types, each with a field named body *)\nm=t54lib;\n%s\nf=one():i64{ <1 };\n'%(K,ts))
open('repro_import.tk','w').write('''(* T-54 via imports: std.http's types plus %d types from t54lib, all in scope.
   EXPECTED: compiles and prints the body length 0, or a diagnostic naming the 64-type limit.
   DEFECT: past 64 types in scope, $httpresp is displaced and r.body fails with a field-offset error. *)
m=t54i;
i=io:std.io;
i=http:std.http;
i=tl:t54lib;
f=blen(r:$httpresp):i64{ <r.body.len };
f=main():i64{
  io.println("one=\\(tl.one())");
  <0
};
'''%K)
