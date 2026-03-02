import json
import pathlib
import requests
url='http://localhost:8000/api/validate/'
files={'files':open('data/day3/generated/stubs/s_LCSETD04_0335a9d2e5.pdf','rb')}
data={
    'document_type':'letter_of_credit',
    'user_type':'exporter',
    'workflow_type':'export-lc-upload',
    'metadata':'{"case_id":"forge_x_warn_001","scenario":"warn"}',
}
r=requests.post(url,data=data,files=files,timeout=120)
print(r.status_code)
print(r.text[:5000])
open('temp_sample_response.json','w',encoding='utf-8').write(r.text)
print('saved')
