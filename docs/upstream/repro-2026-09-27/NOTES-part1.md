# Part 1 (T-1..T-30, O-1) — analyst notes, PIN 0b0bc4e / HEAD 4a50b87

Status PIN/HEAD: T-1..T-6 FIXED/FIXED; T-7 REPRO/FIXED (E4036); T-8 REPRO/FIXED; T-9 REPRO/REPRO;
T-10 CHANGED (declared once, route only; 4-arg E4026 never mentions route; 2-arg compiles, sends nothing);
T-11 CHANGED (tls real, mdns implemented; infer/mlx stubs unchanged; .tki arity != impl; load arm flips with arm order = T-31);
T-12 CHANGED (4 listed now in .tki; json.getregulations len 0; str.padright with str pad pads garbage);
T-13 REPRO/CHANGED (mut.$x E4033 on HEAD; struct-field l:$internal still SIGTRAP 133);
T-14 REPRO/REPRO; T-15 CHANGED (2-arg http.get = route; $err on closed AND on live server with 0 requests; http.get(url) closed port -> "" no error channel);
T-16..T-18 REPRO/REPRO; T-19 FIXED/FIXED; T-20 REPRO/REPRO (declare fastcc i64 @lib_f64abs(double));
T-21 REPRO/REPRO (prints address, not truncation — T-41 mechanism; HEAD fixed process.homedir only; std.homedir needs std.process import to link);
T-22 CHANGED (no crash; stored 0.0 reads as $err); T-23 REPRO/FIXED (E4031); T-24..T-30 REPRO/REPRO;
O-1: PIN compiles; HEAD E4071 at store.tk:174:3 and :183:3 (first fn is storeslug, not storeget; c07c503 is the tag object, commit d4acc03).

Stale in toke-issues.md: T-1 filed program now E4071 (ends in bare mt); T-5 $ok(void) E4033 on HEAD; T-2 PIN refuses annotated struct-field 3-arm (E9005) — works on HEAD only; T-10/T-11/T-12/T-15/T-17/T-21/T-22 as above.

New defects found: (a) HEAD: 8192-byte buffer for clang source list / --emit-deps (llvm.c:12553, main.c) -> std.http programs from a long checkout path fail E9003 on a truncated path; (b) PIN: `toke --out b a.tk b.tk` passes "m0.ll m1.ll" as ONE path (HEAD fixed); (c) `<$ok()` E9003 undefined value '@ok' on both.
Runtime: db/net repros need --allow-all / --allow-net.
