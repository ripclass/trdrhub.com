from pathlib import Path


def test_template_prefill_route_is_registered_before_template_id_route() -> None:
    router_source = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "sme_templates.py"
    ).read_text(encoding="utf-8")
    prefill_index = router_source.index('@router.post("/prefill"')
    get_index = router_source.index('@router.get("/{template_id}"')

    assert prefill_index < get_index
