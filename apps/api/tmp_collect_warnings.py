import warnings

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    import app.services.validator  # noqa: F401
    import app.routers.validate  # noqa: F401

print(len(w))
for ww in w:
    print(f"{ww.filename}:{ww.lineno}:{type(ww.message).__name__}:{ww.message}")
