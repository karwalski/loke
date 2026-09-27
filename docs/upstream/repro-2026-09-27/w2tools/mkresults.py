import re,os,sys
O=sys.argv[1]
def parse(f):
    d={}
    for l in open(f):
        m=re.match(r'^(T-\d+[ab]?|R\d)\s+\|\s+(\S+)\s+\|\s?(.*)$',l.rstrip('\n'))
        if m: d[m.group(1)]=(m.group(2),m.group(3))
    return d
P=parse(O+'/run2_pin.txt'); H=parse(O+'/run2_head.txt')
N={
'T-31':("`mt` binds a stdlib result's arms by position, not label","",""),
'T-32':("std.json cannot read a nested value; the untyped json.getval handle passed to json.i64 segfaults","HEAD's json.tki has no typed `json.obj(Json,str)`; the only `json.obj` is `json.obj ( i64 ) -> i64 [abi]` on both.",""),
'T-33':("numeric/bool std.json accessors report `$jsonerr` for 0 / 0.0 / false","Side observation (R8 probe, both compilers): `row.i64(w;\"n\")` on a COUNT of 0 took the `$err` arm too (std.db analogue).",""),
'T-34':("`http.res.err` lowers to a call of libc `err(3)` (exits the process); `http.res.json` to undefined `_json`","HEAD IR: `call i64 @tk_http_res_err(...)`; PIN IR: `call i64 @err(...)`. PIN exit status here is 96 (the low byte of the string pointer passed as err's eval), not 144 as in the filed text, because the one-argument form passes a pointer.",""),
'T-35':("emitted IR silently truncated (670 x 38-char constants; one 300,000-char constant), toke exits 0","`--emit-llvm` sizes identical on both: 204,289 bytes (670) vs 203,997 (669 control); 66,258 bytes for the 300k string. clang: `constant expression type mismatch: got type '[56 x i8]' but expected '[38 x i8]'` / `'[65506 x i8]' but expected '[300001 x i8]'`.",""),
'T-36':("str.tki gen:abi block declares members as untyped i64, so wrong arguments type-check","HEAD now rejects `str.len(<array>)` (E4031, 'argument 1 of std.str.len is read by the runtime as a C string'). Still defective on HEAD: `str.compare` never negative (a,b=1; b,a=1), `str.padleft(\"7\";3;\"0\")` pads with non-printable bytes (pad is a char code), `str.tof32(12345)` compiles and segfaults (rc 139). str.tki: 77 abi members on both; members declared `-> i64`: 77 (PIN) vs 55 (HEAD).",""),
'T-37':("a declared `@f64` array handle gets the scalar f64 conversion (fptosi/bitcast double), IR invalid","",""),
'T-38':("a later `let` retypes an earlier same-named binder; E4031 attributed to the wrong line with a wrong fix hint","",""),
'T-39':("unused-import lint ignores type-only use; `--lint --fix` deletes the import and breaks the build","Only the type-only case was tested; the field-resolution-only case from the filed text was not reproduced standalone.",""),
'T-40':("`db.exec` runs only the first statement of a multi-statement string and returns ok","Verified with the sqlite3 CLI on the file the program wrote. Side observation: on PIN the program's own interpolation of the nested-mt row.str result printed an address (the sqlite3 CLI result is the evidence used).",""),
'T-41':("interpolating a std.str result prints the string's address","`sha256prefix` was dropped from the repro: HEAD rejects a str argument to it (E4031, it takes an array). HEAD still declares `str.frombool ( i64 ) -> i64` and `str.replaceall ( i64, i64, i64 ) -> i64`, the two that still print an address.",""),
'T-42':("struct literal of an undeclared type is accepted and read positionally","",""),
'T-43':("no API chooses a server's bind address; servers listen on all interfaces","`tk_web_glue.c` calls `http_serve_workers(NULL, NULL, port, workers)` on both. `http.listen(\"127.0.0.1:11442\";...)` also bound `*:11442`. Servers were run with `--allow-net` (without it: CAP001).",""),
'T-44':("json.str turns an escaped \\n into the letter n","Same defect as T-47a.",""),
'T-45':("json.enc escapes only quote and backslash; raw control bytes in output","",""),
'T-46':("annotated `let g:str=str.fromi64(...)` used as an array element is compiled as a spread (element vanishes / garbage / crash)","PIN: randhex case gave len=3 on one run and SIGSEGV (rc 139) on another; nondeterministic garbage length as filed.",""),
'T-47a':("json.str unescape drops the backslash (\\n \\t \\r \\u0041 read back as letters)","Same defect as T-44.",""),
'T-47b':("`str.nowunix()` returns a string handle, declared i64","HEAD declares `str.nowunix (  ) -> str`; interpolation now prints the seconds, but `a/86400` and `b-a` on the str still compile silently and compute on the heap handle (b-a=32 while a and b print the same second).",""),
'T-48':("`http.postheaders(client;\"\";body;headers)` (loke's provider shape) sends nothing, takes $err","Measured over http against a local recorder on 127.0.0.1:11443 only; https to any real provider was NOT attempted: **https unmeasured**. The C glue is `tk_http_postheaders_w(url, body, headers, extra)` (extra ignored) on both; the URL-first call `http.postheaders(url;body;headersjson;\"\")` arrived with x-api-key and content-type headers on both (content-type appears twice: the glue's own plus the custom one).",""),
'T-49':("`net.listen(port)` segfaults","",""),
'T-50':("`mt` on `process.wait` (plain i32) sends exit 0 to the $err arm","HEAD rejects the match at compile time: E4031 \"expected an error union 'T!E', got 'i32' - a '$ok'/'$err' match tests the value against 0\". `process.wait(h) as i64` returns 0 correctly on PIN.",""),
'T-51':("json.dec accepts `{not json` and reading the value crashes","With the `$ok` arm first, `{not json` takes `$jsonerr` on both compilers, as do `{not`, `{a:1}`, `{\"a\":}`, `{\"a\":1`, `garbage`, and empty (repro_more.tk). `{\"a\":1}x` (trailing garbage) is accepted on both. With the `$jsonerr` arm written first (repro_errfirst.tk) the `$ok` arm runs — that is T-31, and json.str on the value then took its err arm, no crash. The loke site is packages/mcp-toke/src/server.tk (the `wellformed` pre-check comment citing T-51); the standalone decoder does not reproduce the filed behaviour.","NO-STANDALONE-REPRO"),
'T-52':("struct with a field of type @$self crashes the compiler","",""),
'T-53':("struct capped at 16 fields; --max-params does not raise it; error names neither","R3 probe (w2probes/fieldsN.tk): HEAD compiles and runs structs of 40, 64, 65, 70 fields correctly; PIN fails at f17 (and at f65 for 65/70 fields).",""),
'T-54':("past 64 struct types in scope, a type (here std.http's $httpresp) is displaced; the error blames a field","Bisected with gen.py: via imports, K=57 lib types already fails on HEAD, K=58 on PIN (K=56 ok on both). Declaring 70 types directly in one file gives a loud E9010 on both. `--max-structs=256` makes K=58 compile, link and run on both (the displacement is silent only at the default).",""),
'T-55':("str.charat does strlen per call; byte loop is quadratic","`tk_str_charat_w` still calls `strlen(p)` on HEAD (str_glue.c:206-211). HEAD adds `str.indexfrom ( str, str, i64 ) -> i64`, not a byteat.",""),
'T-56':("a module may import at most 32 others (E9010), capping an ooke handler registry","31 page imports + std.io compiles, 32 + std.io fails, on both. `--max-imports=64` compiles, links and runs a 35-page registry on both (sum=630). The diagnostic does not name the flag.",""),
'T-57':("`http.get(client;path)` registers a GET route (sends nothing); returns read as $err, then $ok after the 256-entry table fills","Recorder on 127.0.0.1:11445 logged only the one-argument control `GET /control`; zero `/health` requests from 300 two-argument calls. First `$ok` at call 257 (256 registrations), ok on the remaining 44, identical on both.",""),
}
for k,(defect,extra,force) in N.items():
    d=O+'/'+k
    p=P.get(k,('?','?')); h=H.get(k,('?','?'))
    files=sorted(f for f in os.listdir(d) if f.endswith('.tk') or f=='gen.py')
    s='# %s result\n\nDefect: %s\n\nReproducer(s): %s (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.\n\n| compiler | status | observed |\n|---|---|---|\n| PIN 0b0bc4e | %s | %s |\n| HEAD 4a50b87 | %s | %s |\n'%(k,defect,', '.join(files),force or p[0],p[1].replace('|','/'),force or h[0],h[1].replace('|','/'))
    if extra: s+='\nNotes: %s\n'%extra
    s+='\nBuild note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.\n'
    open(d+'/result.md','w').write(s)
print('ok')
