"""Compatibility guards for the FastAPI/Pydantic versions used in production."""

import ast
from pathlib import Path


PROOFLINE_SCHEMAS = Path("apps/api/app/schemas/proofline.py")
PROOFLINE_ROUTER = Path("apps/api/app/routers/proofline.py")


def test_nested_document_schema_is_defined_before_trade_case_detail():
    """Pydantic 2.5 must see nested response types before route registration."""

    source = PROOFLINE_SCHEMAS.read_text(encoding="utf-8")

    assert source.index("class TradeCaseDocumentResponse") < source.index(
        "class TradeCaseDetailResponse"
    )


def test_no_content_route_has_no_inferred_return_model():
    """FastAPI 0.104 rejects a 204 route with an inferred return annotation."""

    tree = ast.parse(PROOFLINE_ROUTER.read_text(encoding="utf-8"))
    delete_party = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "delete_trade_case_party"
    )

    assert delete_party.returns is None
