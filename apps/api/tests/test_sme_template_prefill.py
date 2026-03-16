import ast
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional


def _load_substitute_template_variables():
    source = Path("app/routers/sme_templates.py").read_text(encoding="utf-8")
    module = ast.parse(source, filename="app/routers/sme_templates.py")
    function_node = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "_substitute_template_variables"
    )
    extracted_module = ast.Module(body=[function_node], type_ignores=[])
    namespace = {
        "Optional": Optional,
        "List": List,
        "Company": object,
        "CompanyComplianceInfo": object,
        "CompanyAddress": object,
        "DefaultConsigneeShipper": object,
    }
    exec(compile(extracted_module, "app/routers/sme_templates.py", "exec"), namespace)
    return namespace["_substitute_template_variables"]


_substitute_template_variables = _load_substitute_template_variables()


def test_prefill_uses_company_contact_fields_without_missing_attribute_errors():
    company = SimpleNamespace(
        name="Acme Export",
        contact_email="ops@acme.test",
    )

    result = _substitute_template_variables(
        {
            "beneficiary": "{{company_name}}",
            "notes": "Reach us at {{company_email}}. Phone: {{company_phone}}",
        },
        company,
    )

    assert result["beneficiary"] == "Acme Export"
    assert result["notes"] == "Reach us at ops@acme.test. Phone: "
