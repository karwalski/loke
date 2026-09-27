# T-10 - `http.post` declared twice in http.tki; misleading arity error

Files: repro.tk, client2.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-10`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | CHANGED | http.post entries in http.tki=1; 4-arg client call: compile rc=1: error[E4026]: wrong number of arguments for 'std.http.post': the implementation takes 2 arguments, the call passes 4 // 2-arg http.post(url;body): build rc=0 exit=0 (it registers a route; nothing is sent) |
| HEAD 4a50b87 | CHANGED | http.post entries in http.tki=1; 4-arg client call: compile rc=1: error[E4026]: wrong number of arguments for 'std.http.post': the implementation takes 2 arguments, the call passes 4 // 2-arg http.post(url;body): build rc=0 exit=0 (it registers a route; nothing is sent) |

Only ONE `http.post` entry now (kind route, params str,funcdecl) on both; the 4-arg client form is gone, not duplicated. A 4-arg call gives E4026 "the implementation takes 2 arguments, the call passes 4" - still no mention that http.post is a route registration. A 2-arg `http.post(url;body)` (client2.tk) compiles and runs exit 0 on both, i.e. silently registers a route.
