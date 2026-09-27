#!/usr/bin/env python3
"""Recompute toke's selective stdlib source list (resolve_stdlib_deps_imports_only in
src/stdlib_deps.c) without toke's 8192-byte buffer, which truncates when the checkout
path is long. Usage: deps.py TOKE_DIR mod1 mod2 ...  -> prints one source path per line."""
import re,sys,os
td=sys.argv[1]; mods=sys.argv[2:]
full=open(os.path.join(td,'src/stdlib_deps.c')).read()
i0=full.index('stdlib_table[] =')
src=full[i0:full.index('sentinel',i0)]
tab={}
for m in re.finditer(r'\{\s*"(\w+)",\s*"([^"]*)",\s*"([^"]*)",\s*(?:"[^"]*"|\w+)\s*\}',src):
    tab[m.group(1)]=(m.group(2).split(),m.group(3).split())
cm=re.search(r'cmark_files\[\]\s*=\s*\{(.*?)NULL',full,re.S)
cmark=re.findall(r'"([^"]+)"',cm.group(1)) if cm else []
core=['str','collections','args'] if 'core_modules[]' in full else []
needed=[]
def close():
    ch=True
    while ch:
        ch=False
        for n in list(needed):
            for d in tab.get(n,([],[]))[1]:
                if d not in needed: needed.append(d); ch=True
for m in mods:
    if m not in needed: needed.append(m)
close()
for c in core:
    if c not in needed: needed.append(c)
close()
sd=os.path.join(td,'src/stdlib'); vd=os.path.join(td,'stdlib/vendor')
out=[sd+'/tk_runtime.c']
if os.path.exists(sd+'/capabilities.c'): out.append(sd+'/capabilities.c')
for n in needed:
    if n not in tab: continue
    for f in tab[n][0]:
        p=sd+'/'+f
        if p not in out: out.append(p)
    if n=='toml': out.append(vd+'/tomlc99/toml.c')
    if n=='md': out+= [vd+'/cmark/src/'+f for f in cmark]
print('\n'.join(out))
