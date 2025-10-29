#!/usr/bin/env python3
"""
Compliance Documentation Index Generator

This script generates an index/README for the compliance documentation,
including cross-references, term counts, and navigation aids.

Usage:
    python generate_index.py [--output README.md] [--format html|md]
"""

import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ComplianceIndexGenerator:
    """Generates index documentation for compliance docs."""

    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)

    def extract_document_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from document headers."""
        if not file_path.exists():
            return {}

        content = file_path.read_text(encoding='utf-8')
        metadata = {}

        # Extract document version
        version_match = re.search(r'\*\*Document Version:\*\* (.+)', content)
        if version_match:
            metadata['version'] = version_match.group(1)

        # Extract last updated date
        updated_match = re.search(r'\*\*Last Updated:\*\* (.+)', content)
        if updated_match:
            metadata['last_updated'] = updated_match.group(1)

        # Extract document title (first h1)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1)

        # Extract status information
        status_match = re.search(r'\*\*Status:\*\* (.+)', content)
        if status_match:
            metadata['status'] = status_match.group(1)

        return metadata

    def extract_coverage_statistics(self, file_path: Path) -> Dict[str, int]:
        """Extract implementation coverage statistics."""
        if not file_path.exists():
            return {}

        content = file_path.read_text(encoding='utf-8')
        stats = {}

        # Extract total mapped items
        total_match = re.search(r'\*\*Total (?:Articles|Sections) Mapped:\*\* (\d+)', content)
        if total_match:
            stats['total'] = int(total_match.group(1))

        # Extract implemented count
        impl_match = re.search(r'\*\*Fully Implemented \(✅\):\*\* (\d+)', content)
        if impl_match:
            stats['implemented'] = int(impl_match.group(1))

        # Extract partial count
        partial_match = re.search(r'\*\*Partially Implemented \(🟡\):\*\* (\d+)', content)
        if partial_match:
            stats['partial'] = int(partial_match.group(1))

        # Calculate percentage
        if stats.get('total', 0) > 0:
            stats['completion_percent'] = round((stats.get('implemented', 0) / stats['total']) * 100, 1)

        return stats

    def count_glossary_terms(self, glossary_file: Path) -> int:
        """Count the number of terms in the glossary."""
        if not glossary_file.exists():
            return 0

        content = glossary_file.read_text(encoding='utf-8')
        terms = re.findall(r'^#### ([A-Za-z0-9\s\(\)/\-]+)$', content, re.MULTILINE)
        return len(terms)

    def generate_toc(self) -> List[Dict[str, str]]:
        """Generate table of contents with file information."""
        toc_items = [
            {
                'file': '01_ucp600_mapping.md',
                'title': 'UCP 600 Compliance Mapping',
                'description': 'Mapping of LCopilot features to ICC Uniform Customs and Practice for Documentary Credits'
            },
            {
                'file': '02_isbp745_mapping.md',
                'title': 'ISBP 745 Compliance Mapping',
                'description': 'Mapping to International Standard Banking Practice for Document Examination'
            },
            {
                'file': '03_eucp_mapping.md',
                'title': 'eUCP Compliance Mapping',
                'description': 'Electronic UCP supplement for digital document presentation'
            },
            {
                'file': '04_compliance_glossary.md',
                'title': 'Compliance Glossary',
                'description': 'Comprehensive definitions of trade finance and compliance terms'
            },
            {
                'file': '05_annex_for_sla.md',
                'title': 'SLA Compliance Annex',
                'description': 'Contractual compliance framework for service level agreements'
            },
            {
                'file': '06_version_history.md',
                'title': 'Version History',
                'description': 'Change log and version tracking for compliance documentation'
            }
        ]

        # Add metadata to each item
        for item in toc_items:
            file_path = self.docs_path / item['file']
            if file_path.exists():
                metadata = self.extract_document_metadata(file_path)
                item.update(metadata)

                # Add coverage stats for mapping documents
                if 'mapping' in item['file']:
                    stats = self.extract_coverage_statistics(file_path)
                    item['coverage'] = stats

        return toc_items

    def generate_markdown_index(self) -> str:
        """Generate Markdown format index."""
        toc_items = self.generate_toc()
        glossary_count = self.count_glossary_terms(self.docs_path / '04_compliance_glossary.md')

        md_content = f"""# LCopilot Compliance Documentation

**Generated:** {datetime.now().strftime('%B %d, %Y')}
**LCopilot Version:** Sprint 8.2
**Documentation Status:** Complete

## Overview

This directory contains comprehensive compliance documentation for the LCopilot platform, covering regulatory standards, implementation mappings, and operational procedures for international trade finance.

## Document Structure

| Document | Status | Coverage | Description |
|----------|--------|----------|-------------|
"""

        for item in toc_items:
            file_name = item['file']
            title = item.get('title', 'Unknown')
            description = item.get('description', '')
            version = item.get('version', '1.0')

            # Format coverage information
            coverage_text = "N/A"
            if 'coverage' in item and item['coverage']:
                stats = item['coverage']
                if 'completion_percent' in stats:
                    coverage_text = f"{stats['completion_percent']}% ({stats.get('implemented', 0)}/{stats.get('total', 0)})"

            # Status badge
            status_text = "✅ Complete"
            if not (self.docs_path / file_name).exists():
                status_text = "❌ Missing"
            elif item.get('status') == 'Draft':
                status_text = "🟡 Draft"

            md_content += f"| [{title}]({file_name}) | {status_text} | {coverage_text} | {description} |\n"

        md_content += f"""
## Quick Navigation

### Standards Compliance
- **[UCP 600 Mapping](01_ucp600_mapping.md)** - Core documentary credit rules
- **[ISBP 745 Mapping](02_isbp745_mapping.md)** - Document examination standards
- **[eUCP Mapping](03_eucp_mapping.md)** - Electronic document handling

### Reference Materials
- **[Compliance Glossary](04_compliance_glossary.md)** - {glossary_count} trade finance terms
- **[SLA Annex](05_annex_for_sla.md)** - Contractual compliance framework
- **[Version History](06_version_history.md)** - Documentation change log

### Tools and Validation
- **[Documentation Validator](tools/validate_docs.py)** - Automated compliance checking
- **[Index Generator](tools/generate_index.py)** - Documentation index creation

## Compliance Summary

### Implementation Coverage
"""

        # Add coverage summary for each mapping document
        for item in toc_items:
            if 'mapping' in item['file'] and 'coverage' in item:
                stats = item['coverage']
                file_title = item.get('title', item['file'])
                if stats:
                    total = stats.get('total', 0)
                    implemented = stats.get('implemented', 0)
                    partial = stats.get('partial', 0)
                    completion = stats.get('completion_percent', 0)

                    md_content += f"""
**{file_title}**
- Total Mapped: {total}
- Fully Implemented: {implemented} ({completion}%)
- Partially Implemented: {partial}
"""

        md_content += f"""
### Glossary Statistics
- **Total Terms:** {glossary_count}
- **Target:** ≥60 terms ({"✅ Met" if glossary_count >= 60 else "❌ Not Met"})
- **Categories:** Banking/LC Terms, Document Types, Technical/Compliance, Trade Terms

## Regulatory Alignment

This documentation suite ensures LCopilot compliance with:

- **ICC Standards:** UCP 600, ISBP 745, eUCP Version 2.0
- **Data Protection:** GDPR compliance posture with geographic data residency
- **Banking Regulations:** Bangladesh Bank requirements and international banking practices
- **Audit Requirements:** Comprehensive audit trail and evidence management

## Usage Instructions

### For Banking Operations
1. Review [UCP 600 Mapping](01_ucp600_mapping.md) for core LC compliance
2. Consult [ISBP 745 Mapping](02_isbp745_mapping.md) for document examination procedures
3. Reference [Compliance Glossary](04_compliance_glossary.md) for terminology clarification

### For Technical Implementation
1. Use [Documentation Validator](tools/validate_docs.py) for automated compliance checking
2. Review [SLA Annex](05_annex_for_sla.md) for service level requirements
3. Monitor [Version History](06_version_history.md) for change management

### For Regulatory Review
1. Start with [SLA Annex](05_annex_for_sla.md) for contractual compliance framework
2. Review specific standards mappings as needed
3. Use glossary for term clarification and cross-referencing

## Validation and Quality Assurance

This documentation is validated using automated tools to ensure:

- **Structural Integrity:** All required documents present and properly formatted
- **Cross-Reference Accuracy:** Valid links between standards and implementation
- **Content Completeness:** Minimum term counts and coverage requirements met
- **Markdown Syntax:** Proper formatting and table structure

To validate documentation:

```bash
# Run full validation suite
python tools/validate_docs.py --verbose

# Generate fresh index
python tools/generate_index.py --output README.md

# Check specific document
python tools/validate_docs.py --docs-path . 04_compliance_glossary.md
```

## Maintenance and Updates

This documentation is maintained alongside LCopilot platform releases:

- **Version Control:** All changes tracked with version history
- **Regular Reviews:** Quarterly review for regulatory alignment
- **Automated Validation:** CI/CD integration for quality assurance
- **Stakeholder Communication:** Updates communicated to relevant parties

---

**Document Authority:** LCopilot Compliance Team
**Next Review:** December 17, 2025
**Contact:** compliance@lcopilot.com

*This index is automatically generated and should not be manually edited. Use `python tools/generate_index.py` to regenerate.*"""

        return md_content

    def generate_html_index(self) -> str:
        """Generate HTML format index."""
        # Convert markdown to basic HTML structure
        md_content = self.generate_markdown_index()

        # Basic HTML wrapper
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LCopilot Compliance Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .status-complete {{ color: #28a745; }}
        .status-missing {{ color: #dc3545; }}
        .status-draft {{ color: #ffc107; }}
        code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
"""

        # Convert key markdown elements to HTML
        md_content = md_content.replace('# ', '<h1>').replace('\n## ', '</p>\n<h2>').replace('\n### ', '</p>\n<h3>')
        md_content = md_content.replace('**', '<strong>').replace('**', '</strong>')
        md_content = md_content.replace('`', '<code>').replace('`', '</code>')

        html_content += f"    {md_content}\n</body>\n</html>"

        return html_content


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="Generate compliance documentation index")
    parser.add_argument("--docs-path", default="docs/compliance",
                       help="Path to compliance documentation directory")
    parser.add_argument("--output", default="README.md",
                       help="Output file name")
    parser.add_argument("--format", choices=["md", "html"], default="md",
                       help="Output format")

    args = parser.parse_args()

    # Initialize generator
    generator = ComplianceIndexGenerator(args.docs_path)

    # Generate index
    if args.format == "html":
        content = generator.generate_html_index()
    else:
        content = generator.generate_markdown_index()

    # Write output
    if args.docs_path == "docs/compliance":
        # Handle relative path from project root
        output_path = Path(args.output)
    else:
        output_path = Path(args.docs_path) / args.output

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')

    print(f"✅ Generated compliance index: {output_path}")
    print(f"   Format: {args.format.upper()}")
    print(f"   Size: {len(content)} characters")


if __name__ == "__main__":
    main()