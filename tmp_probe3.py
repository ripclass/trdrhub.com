import csv, json, requests
rows={}
for r in csv.DictReader(open('data/day3/manifest/final_manifest.csv')):
    rows[r['case_id']]=r
want=['forge_x_warn_001','forge_x_reject_001','forge_x_reject_002','forge_x_reject_004','forge_x_sanctions_tbml_shell_002','forge_x_reject_003','forge_x_sanctions_tbml_shell_001']
url='http://localhost:8000/api/validate/'
for cid in want:
    r=rows[cid]; path=r['cleaned_path']
    with open(path,'rb') as f:
      resp=requests.post(url, data={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':cid,'scenario':r['scenario']})}, files={'files':f}, timeout=120).json()
    s=resp.get('structured_result',{})
    g=s.get('gate_result',{}) if isinstance(s.get('gate_result'),dict) else {}
    print('\n==',cid,r['scenario'],'expected',r['expected_verdict'])
    print('validation_status',s.get('validation_status'),'bank', (s.get('bank_verdict') or {}).get('verdict'))
    print('lc_type',s.get('lc_type'), 'confidence',s.get('lc_type_confidence'))
    print('gate_status',g.get('status'),'can_proceed',g.get('can_proceed'),'warnings',g.get('warning_issue_count'),'blocker',g.get('blocking_issue_count'))
    print('critical_completeness',g.get('critical_completeness'),'completeness',g.get('completeness'))
    print('missing_required',g.get('missing_required'))
    print('processing_summary warnings',s.get('processing_summary',{}).get('warnings'),'errors',s.get('processing_summary',{}).get('errors'))
    print('issues',len(s.get('issues',[]) or []),'keys', list((s.get('issues') or [])[:1]))
