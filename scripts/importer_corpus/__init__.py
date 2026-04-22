"""
Importer corpus — synthetic trade-document bundles for testing the
importer flows (Draft LC Review + Supplier Document Review).

Avoids any jurisdiction hardcoding: every party name, tax ID, bank,
port, currency, and clause phrasing is driven by per-corridor config.
The MT700 shape mirrors real Import LCs captured from production
flows (see F:/New Download/LC Copies/2024-2025/), but the corpus
generator itself is corridor-agnostic.
"""
