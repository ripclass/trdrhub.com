import csv, json, time, requests
from pathlib import Path
fail_path=Path('Data/day3/results/phase4_full90_stable_failed_cases.csv')
rows=list(csv.DictReader(fail_path.open(encoding='utf-8')))
print('fails',len(rows))
# load manifest path mapping
man=dict((r['case_id'],r) for r in csv.DictReader(open('data/day3/manifest/final_manifest.csv',encoding='utf-8')))
url='http://localhost:8000/api/validate/'
for r in rows:
    cid=r['case_id']; manr=man[cid]
    path=manr['cleaned_path']
    files={'files':open(path,'rb')}
    payload={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':cid,'scenario':manr['scenario']})}
    # simple retry loop for 429
    for attempt in range(1,6):
        try:
            resp=requests.post(url,data=payload,files=files,timeout=90)
        except Exception as e:
            print(cid,'ERR',e)
            break
        if resp.status_code!=429:
            break
        wait=min(2.0*(2**(attempt-1)),20)
        time.sleep(wait)
    d=resp.json() if resp.ok else {'error':resp.text}
    s=d.get('structured_result',{}) if isinstance(d.get('structured_result'),dict) else {}
    g=s.get('gate_result',{}) if isinstance(s.get('gate_result'),dict) else {}
    print(f"{cid},{manr['scenario']},{manr['expected_verdict']},{resp.status_code},v_status={s.get('validation_status')},bank={s.get('bank_verdict',{}).get('verdict') if isinstance(s.get('bank_verdict'),dict) else None},warnings={s.get('processing_summary',{}).get('warnings')},errors={s.get('processing_summary',{}).get('errors')},gate={g.get('status')},can={g.get('can_proceed')},warns={g.get('warning_issue_count')},blocks={g.get('blocking_issue_count')},comp={g.get('critical_completeness')}")
    files['files'].close()
    time.sleep(1.1)
