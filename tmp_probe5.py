import csv, json, time, requests
man={r['case_id']:r for r in csv.DictReader(open('data/day3/manifest/final_manifest.csv',encoding='utf-8'))}
ids=['forge_x_warn_001','forge_x_reject_001','forge_x_reject_002','forge_x_sanctions_tbml_shell_001']
url='http://localhost:8000/api/validate/'
for cid in ids:
  r=man[cid]
  with open(r['cleaned_path'],'rb') as f:
    for attempt in range(1,4):
      resp=requests.post(url,data={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':cid,'scenario':r['scenario']})},files={'files':f},timeout=60)
      if resp.status_code!=429:
        break
      time.sleep(1.5*(2**(attempt-1)))
    j=resp.json()
    s=j.get('structured_result',{}) if isinstance(j.get('structured_result'),dict) else {}
    print('\nCASE',cid)
    print('status',resp.status_code)
    print('keys',list(j.keys())[:20])
    print('validation_status',s.get('validation_status'),'compliance', (s.get('analytics') or {}).get('compliance_level'))
    print('completeness',s.get('gate_result',{}).get('critical_completeness'), s.get('gate_result',{}).get('completeness'))
    print('missing_required',s.get('gate_result',{}).get('missing_required'))
    print('warnings',s.get('processing_summary',{}).get('warnings'),'errors',s.get('processing_summary',{}).get('errors'))
    print('bank',s.get('bank_verdict'))
    print('issues_count',len(s.get('issues',[]) or []))
    print('raw',s.get('validation_status'))
  time.sleep(2)
