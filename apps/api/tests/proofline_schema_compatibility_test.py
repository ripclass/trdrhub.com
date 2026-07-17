"""Compatibility guards for the FastAPI/Pydantic versions used in production."""

from pathlib import Path


PROOFLINE_SCHEMAS = Path("apps/api/app/schemas/proofline.py")


def test_nested_document_schema_is_defined_before_trade_case_detail():
    """Pydantic 2.5 must see nested response types before route registration."""

    source = PROOFLINE_SCHEMAS.read_text(encoding="utf-8")

    assert source.index("class TradeCaseDocumentResponse") < source.index(
        "class TradeCaseDetailResponse"
    )
