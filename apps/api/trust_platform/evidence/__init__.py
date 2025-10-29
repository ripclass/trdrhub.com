"""
Evidence Package Management for LCopilot Trust Platform
Provides tamper-proof bundling and verification of compliance validation results.
"""

from .evidence_packager import EvidencePackager, EvidenceManifest

__all__ = ["EvidencePackager", "EvidenceManifest"]