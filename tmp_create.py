from app.database import Base, engine
from sqlalchemy import Table, Column, String, MetaData
# inject organizations table to satisfy FK refs if missing
if 'organizations' not in Base.metadata.tables:
    Table('organizations', Base.metadata, Column('id', String), extend_existing=True)
try:
    Base.metadata.create_all(bind=engine)
    print('create_all_ok')
except Exception as e:
    print(type(e).__name__, e)
    import traceback; traceback.print_exc()
