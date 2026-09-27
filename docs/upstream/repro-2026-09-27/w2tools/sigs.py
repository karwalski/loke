import json,sys
d=json.load(open(sys.argv[1]))
for e in d['exports']:
  if e['kind']=='type': 
    if len(sys.argv)>2 and sys.argv[2]=='t': print('type',e['name'],json.dumps(e.get('fields') or e.get('variants')))
    continue
  pn=e.get('param_names')
  print(e['name'],'(',', '.join(e.get('params',[])),') ->',e.get('return'),'[abi]' if e.get('gen')=='abi' else '')
