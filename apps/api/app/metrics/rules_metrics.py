"\"\""
Prometheus metrics for rules governance workflows.
"\"\""

try:
    from prometheus_client import Counter
except ImportError:  # pragma: no cover
    class _MockCounter:
        def labels(self, **kwargs):
            return self

        def inc(self, value: float = 1.0) -> None:
            pass

    Counter = _MockCounter  # type: ignore


rules_import_total = Counter(
    "rules_import_total",
    "Count of rules imported into the normalized governance table",
    ["action", "result"],
)

rules_update_total = Counter(
    "rules_update_total",
    "Count of manual rule governance updates",
    ["action"],
)

