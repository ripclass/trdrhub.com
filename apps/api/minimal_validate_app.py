from fastapi import FastAPI
from types import SimpleNamespace
from uuid import UUID
import importlib.util
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

validate_path = BASE / 'app' / 'routers' / 'validate.py'
spec = importlib.util.spec_from_file_location('standalone_validate_router', validate_path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

app = FastAPI()
app.dependency_overrides[module.get_user_optional] = lambda: SimpleNamespace(
    id=UUID('00000000-0000-0000-0000-000000000001'),
    email='demo@trdrhub.com',
    role='exporter',
    company_id=None,
)
app.include_router(module.router)

@app.get('/health')
def health():
    return {'ok': True}
