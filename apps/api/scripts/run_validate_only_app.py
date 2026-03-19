from fastapi import FastAPI
from app.routers.validate import router as validate_router

app = FastAPI()
app.include_router(validate_router)

@app.get('/health')
def health():
    return {'ok': True, 'mode': 'validate-only'}

@app.get('/api/auth/csrf-token')
def csrf_token_api():
    return {'csrf_token': 'local-dev-csrf'}

@app.get('/auth/csrf-token')
def csrf_token_auth():
    return {'csrf_token': 'local-dev-csrf'}
