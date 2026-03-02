import csv, json, requests, time
rows = list(csv.DictReader(open('data/day3/manifest/final_manifest.csv',encoding='utf-8')))
reject_rows = [r for r in rows if r['scenario']=='reject']
url='http://localhost:8000/api/validate/'
print('count',len(reject_rows))
for r in reject_rows:
    cid=r['case_id']
    with open(r['cleaned_path'],'rb') as f:
      resp=requests.post(url,data={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':cid,'scenario':r['scenario']})},files={'files':f},timeout=120)
    d=resp.json() if resp.ok else {'structured_result':{}}
    s=d.get('structured_result',{}) or {}
    g=s.get('gate_result',{}) or {}
    tr=s.get('validation_status') or ''
    print(cid, 'code',resp.status_code,'vstat',tr,'bank', (s.get('bank_verdict') or {}).get('verdict'),'compliance', (s.get('analytics') or {}).get('compliance_level'),'cc',g.get('critical_completeness'),'compl',g.get('completeness'),'warns',g.get('warning_issue_count'),'blocks',g.get('blocking_issue_count'))
    time.sleep(2)
