import csv,json,requests
r=next(x for x in csv.DictReader(open('data/day3/manifest/final_manifest.csv')) if x['case_id']=='forge_x_reject_002')
url='http://localhost:8000/api/validate/'
with open(r['cleaned_path'],'rb') as f:
    resp=requests.post(url,data={'document_type':'letter_of_credit','user_type':'exporter','workflow_type':'export-lc-upload','metadata':json.dumps({'case_id':r['case_id'],'scenario':r['scenario']})},files={'files':f},timeout=120)
print('status',resp.status_code)
text=resp.text
print(text[:400])
print('len',len(text))
obj=resp.json()
print('top keys',obj.keys())
print('structured type',type(obj.get('structured_result')))
print('structured keys', list((obj.get('structured_result') or {}).keys())[:20])
print('has issues', 'issues' in obj, 'issues len', len(obj.get('issues',[]) or []))
