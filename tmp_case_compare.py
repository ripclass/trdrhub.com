import csv, json, requests, time
url='http://localhost:8000/api/validate/'
manifest = list(csv.DictReader(open('data/day3/manifest/final_manifest.csv',encoding='utf-8')))
for target in ['pass','warn','reject','blocked','sanctions_tbml_shell']:
    picks=[r for r in manifest if r['scenario']==target][:3]
    print('\n',target)
    for p in picks:
        with open(p['cleaned_path'],'rb') as f:
            r=requests.post(url,data={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':p['case_id'],'scenario':p['scenario']})},files={'files':f},timeout=120)
            s=r.json().get('structured_result',{})
            g=s.get('gate_result',{}) if isinstance(s.get('gate_result'),dict) else {}
        print(p['case_id'], 'status', r.status_code, 'v',s.get('validation_status'),'bank', (s.get('bank_verdict') or {}).get('verdict'), 'gstat',g.get('status'),'critcomp',g.get('critical_completeness'),'compl',g.get('completeness'),'warns',g.get('warning_issue_count'),'blocks',g.get('blocking_issue_count'),'missing',len(g.get('missing_required') or []))
        time.sleep(1)
