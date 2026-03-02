import csv, json
import requests
from pathlib import Path
rows=list(csv.DictReader(open('data/day3/manifest/final_manifest.csv')))
want=set(['forge_x_warn_001', 'forge_x_reject_002','forge_x_reject_004','forge_x_reject_001','forge_x_sanctions_tbml_shell_002'])
url='http://localhost:8000/api/validate/'
for r in rows:
    cid=r['case_id']
    if cid not in want: continue
    path=r['cleaned_path']
    files={'files':open(path,'rb')}
    data={
        'document_type':'letter_of_credit',
        'user_type':'exporter',
        'workflow_type':'export-lc-upload',
        'metadata':json.dumps({'case_id':cid,'scenario':r['scenario']}),
    }
    resp=requests.post(url,data=data,files=files,timeout=120)
    d=resp.json()
    s=d.get('structured_result',{})
    print(cid, r['scenario'], r['expected_verdict'], 'status', d.get('status'), 'final', s.get('validation_status'), 'gate', s.get('gate_result',{}).get('status'), 'pass', s.get('final_verdict'), 'bank', (s.get('bank_verdict') or {}).get('verdict'), 'issues', len(s.get('issues') or []), 'warnings', s.get('processing_summary',{}).get('warnings'))
    files['files'].close()
