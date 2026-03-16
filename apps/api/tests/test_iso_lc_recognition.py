from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
ISO_EXTRACTOR_PATH = ROOT / "app" / "services" / "extraction" / "iso20022_lc_extractor.py"
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
SMART_EXTRACTOR_PATH = ROOT / "app" / "services" / "extraction" / "smart_lc_extractor.py"
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"


TSRV_XML = """
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:tsrv.001.001.01">
  <UndtkgIssnc>
    <Undtkg>
      <Id>SBLC-001</Id>
      <Amt Ccy="USD">100000</Amt>
    </Undtkg>
  </UndtkgIssnc>
</Document>
""".strip()

TSIN_XML = """
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:tsin.001.001.01">
  <DocCdtIssnc>
    <DocCdtDtls>
      <DocCdtId>DOC-123</DocCdtId>
      <LcAmt Ccy="USD">250000</LcAmt>
      <DocCdtFrm>
        <Cd>IRVC</Cd>
      </DocCdtFrm>
      <Bnfcry>
        <Nm>Exporter Co</Nm>
      </Bnfcry>
    </DocCdtDtls>
  </DocCdtIssnc>
</Document>
""".strip()

GENERIC_ISO_XML = """
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:foo.001.001.01">
  <AnyMessage>
    <BIC>ABCDUS33</BIC>
    <Amt Ccy="USD">1000</Amt>
    <PstlAdr>
      <Ctry>US</Ctry>
    </PstlAdr>
  </AnyMessage>
</Document>
""".strip()

NON_ISO_XML = "<Document><foo>bar</foo></Document>"
MT700_TEXT = ":27:1/1\n:40A:IRREVOCABLE\n:20:LC12345\n:31C:240101\n:32B:USD1000\n"


def _load_iso_module():
    spec = importlib.util.spec_from_file_location("iso20022_lc_extractor_test", ISO_EXTRACTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ISO extractor module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_function(path: Path, function_name: str, namespace: Dict[str, Any]) -> Any:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, filename=str(path), mode="exec"), namespace)
    return namespace[function_name]


def test_iso_schema_detection_covers_supported_variants() -> None:
    iso_module = _load_iso_module()

    assert iso_module.detect_iso20022_schema(TSRV_XML) == ("tsrv.001", 0.95)
    assert iso_module.detect_iso20022_schema(TSIN_XML) == ("tsin.001", 0.95)
    assert iso_module.detect_iso20022_schema(GENERIC_ISO_XML) == ("unknown_iso20022", 0.7)


def test_enhanced_iso_extractor_sets_truthful_lc_type() -> None:
    iso_module = _load_iso_module()

    standby = iso_module.extract_iso20022_lc_enhanced(TSRV_XML)
    assert standby["format"] == "iso20022"
    assert standby["schema"] == "tsrv.001"
    assert standby["lc_type"] == "standby"
    assert standby["lc_type_source"] == "iso20022_schema"

    documentary = iso_module.extract_iso20022_lc_enhanced(TSIN_XML)
    assert documentary["format"] == "iso20022"
    assert documentary["schema"] == "tsin.001"
    assert documentary["lc_type"] == "irrevocable"
    assert documentary["lc_type_source"] == "iso20022_schema"


def test_launch_and_validate_recognize_iso_formats_without_breaking_mt_detection() -> None:
    iso_module = _load_iso_module()
    namespace = {"Optional": Optional, "detect_iso20022_schema": iso_module.detect_iso20022_schema}

    launch_detect = _load_function(LAUNCH_PIPELINE_PATH, "detect_lc_format", dict(namespace))
    validate_detect = _load_function(VALIDATE_PATH, "detect_lc_format", dict(namespace))

    assert launch_detect(TSRV_XML) == "iso20022"
    assert launch_detect(TSIN_XML) == "iso20022"
    assert launch_detect(GENERIC_ISO_XML) == "iso20022"
    assert launch_detect(MT700_TEXT) == "mt700"

    assert validate_detect(TSRV_XML) == "iso20022"
    assert validate_detect(TSIN_XML) == "iso20022"
    assert validate_detect(GENERIC_ISO_XML) == "iso20022"
    assert validate_detect(MT700_TEXT) == "mt700"


def test_smart_detector_catches_iso_variants_but_keeps_non_iso_xml_out() -> None:
    iso_module = _load_iso_module()
    smart_detect = _load_function(
        SMART_EXTRACTOR_PATH,
        "detect_lc_format",
        {"Optional": Optional, "detect_iso20022_schema": iso_module.detect_iso20022_schema},
    )

    assert smart_detect(TSRV_XML, filename="credit.xml") == "iso20022"
    assert smart_detect(TSIN_XML, filename="credit.xml") == "iso20022"
    assert smart_detect(GENERIC_ISO_XML, filename="credit.xml") == "iso20022"
    assert smart_detect(NON_ISO_XML, filename="credit.xml") == "xml_other"
    assert smart_detect(MT700_TEXT, filename="credit.txt") == "mt700"
