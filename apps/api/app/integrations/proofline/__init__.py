"""Proofline adapters for existing and external source modules."""

from .base import AdapterResult, ProoflineAdapter
from .registry import build_adapter_registry

__all__ = ["AdapterResult", "ProoflineAdapter", "build_adapter_registry"]
