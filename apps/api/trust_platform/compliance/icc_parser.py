#!/usr/bin/env python3
"""
ICC Document Parser
Extracts and structures text from ICC publications (UCP600, ISBP, etc.) for AI rule generation.

IMPORTANT: ICC documents contain copyrighted material. This parser is designed to:
- Extract structured text for internal AI processing only
- Never store or redistribute full ICC text
- Output only paraphrased rules with article references
- Maintain strict confidentiality of source material
"""

import logging
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# PDF processing libraries (install with: pip install PyPDF2 pdfminer.six)
try:
    import PyPDF2
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False
    logging.warning("PDF libraries not installed. Install with: pip install PyPDF2 pdfminer.six")

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    UCP600 = "ucp600"
    ISBP = "isbp"
    ISP98 = "isp98"
    INCOTERMS = "incoterms"
    UNKNOWN = "unknown"


@dataclass
class ArticleSection:
    """Represents a parsed article or section from ICC document"""
    article_id: str  # e.g., "UCP600-14", "ISBP-A6"
    title: str
    content: str
    subsections: List[str]
    page_number: Optional[int] = None
    confidence: float = 0.8  # Parser confidence in extraction


@dataclass
class ParsedDocument:
    """Complete parsed ICC document"""
    document_type: DocumentType
    document_version: str
    title: str
    total_pages: int
    articles: List[ArticleSection]
    metadata: Dict[str, Any]
    parsing_timestamp: datetime
    confidentiality_note: str = "CONFIDENTIAL: ICC copyrighted material - internal use only"


class ICCDocumentParser:
    """Parses ICC documents while maintaining IP compliance"""

    def __init__(self):
        self.supported_formats = ['.pdf']
        self.temp_dir = Path(tempfile.gettempdir()) / "icc_parser"
        self.temp_dir.mkdir(exist_ok=True)

        # Article patterns for different ICC publications
        self.article_patterns = {
            DocumentType.UCP600: {
                'article_regex': r'Article\s+(\d+[a-z]?)\s*[-–]\s*(.*?)(?=\n|$)',
                'subarticle_regex': r'^([a-z]\)\s*.*?)(?=\n[a-z]\)|$)',
                'numbering_regex': r'(\d+)\.?\s*([a-z]\))?',
                'expected_articles': 39
            },
            DocumentType.ISBP: {
                'article_regex': r'([A-Z]\d+)\s*[-–]\s*(.*?)(?=\n|$)',
                'subarticle_regex': r'^([ivx]+\)\s*.*?)(?=\n[ivx]+\)|$)',
                'numbering_regex': r'([A-Z])(\d+)',
                'expected_articles': 200
            }
        }

    def parse_document(self, file_path: Path, document_type: Optional[DocumentType] = None) -> ParsedDocument:
        """
        Parse ICC document from PDF file

        Args:
            file_path: Path to ICC PDF file
            document_type: Type of ICC document (auto-detected if None)

        Returns:
            ParsedDocument with structured content
        """
        if not HAS_PDF_LIBS:
            raise ImportError("PDF parsing libraries not installed. Run: pip install PyPDF2 pdfminer.six")

        if not file_path.exists():
            raise FileNotFoundError(f"ICC document not found: {file_path}")

        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {file_path.suffix}")

        logger.info(f"Parsing ICC document: {file_path.name}")

        # Extract text from PDF
        text_content = self._extract_text_from_pdf(file_path)

        # Detect document type if not specified
        if document_type is None:
            document_type = self._detect_document_type(text_content)

        # Parse document structure
        articles = self._parse_articles(text_content, document_type)

        # Extract metadata
        metadata = self._extract_metadata(text_content, document_type)

        # Create parsed document
        parsed_doc = ParsedDocument(
            document_type=document_type,
            document_version=metadata.get('version', 'unknown'),
            title=metadata.get('title', file_path.stem),
            total_pages=self._count_pages(file_path),
            articles=articles,
            metadata=metadata,
            parsing_timestamp=datetime.now()
        )

        logger.info(f"Parsed {len(articles)} articles from {document_type.value}")
        return parsed_doc

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text content from PDF using multiple methods"""
        text_content = ""

        # Method 1: pdfminer (better for complex layouts)
        try:
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                boxes_flow=0.5,
                all_texts=False
            )
            text_content = extract_text(str(file_path), laparams=laparams)
            logger.debug(f"Extracted {len(text_content)} characters using pdfminer")

        except Exception as e:
            logger.warning(f"pdfminer extraction failed: {e}")

            # Method 2: PyPDF2 fallback
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pages_text = []

                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            pages_text.append(f"[PAGE {page_num + 1}]\n{page_text}")
                        except Exception as page_error:
                            logger.warning(f"Failed to extract page {page_num + 1}: {page_error}")

                    text_content = "\n\n".join(pages_text)
                    logger.debug(f"Extracted {len(text_content)} characters using PyPDF2")

            except Exception as e2:
                logger.error(f"Both PDF extraction methods failed: {e2}")
                raise RuntimeError(f"Could not extract text from PDF: {e2}")

        if not text_content.strip():
            raise ValueError("No text content extracted from PDF")

        return text_content

    def _detect_document_type(self, text_content: str) -> DocumentType:
        """Auto-detect ICC document type from content"""
        text_lower = text_content.lower()

        # Check for document type indicators
        if 'uniform customs and practice' in text_lower and '600' in text_lower:
            return DocumentType.UCP600
        elif 'international standard banking practice' in text_lower:
            return DocumentType.ISBP
        elif 'international standby practices' in text_lower and '98' in text_lower:
            return DocumentType.ISP98
        elif 'incoterms' in text_lower:
            return DocumentType.INCOTERMS
        else:
            logger.warning("Could not detect ICC document type")
            return DocumentType.UNKNOWN

    def _parse_articles(self, text_content: str, document_type: DocumentType) -> List[ArticleSection]:
        """Parse articles and sections from document text"""
        articles = []

        if document_type not in self.article_patterns:
            logger.warning(f"No parsing patterns for {document_type.value}")
            return articles

        patterns = self.article_patterns[document_type]

        # Split text into potential articles
        article_matches = re.finditer(patterns['article_regex'], text_content, re.MULTILINE | re.IGNORECASE)

        for match in article_matches:
            article_num = match.group(1)
            article_title = match.group(2).strip() if len(match.groups()) > 1 else ""

            # Extract article content (text between this article and next)
            start_pos = match.end()
            next_match = None

            # Find next article
            remaining_text = text_content[start_pos:]
            next_article = re.search(patterns['article_regex'], remaining_text, re.MULTILINE | re.IGNORECASE)

            if next_article:
                article_content = remaining_text[:next_article.start()].strip()
            else:
                article_content = remaining_text[:1000].strip()  # Limit to avoid huge sections

            # Parse subsections within article
            subsections = self._parse_subsections(article_content, patterns.get('subarticle_regex'))

            # Create article ID
            if document_type == DocumentType.UCP600:
                article_id = f"UCP600-{article_num}"
            elif document_type == DocumentType.ISBP:
                article_id = f"ISBP-{article_num}"
            else:
                article_id = f"{document_type.value.upper()}-{article_num}"

            # Calculate confidence based on content quality
            confidence = self._calculate_parsing_confidence(article_content, article_title)

            article = ArticleSection(
                article_id=article_id,
                title=article_title,
                content=article_content,
                subsections=subsections,
                confidence=confidence
            )

            articles.append(article)

        logger.info(f"Parsed {len(articles)} articles for {document_type.value}")
        return articles

    def _parse_subsections(self, article_content: str, subarticle_pattern: Optional[str]) -> List[str]:
        """Parse subsections within an article"""
        if not subarticle_pattern:
            return []

        subsections = []
        matches = re.finditer(subarticle_pattern, article_content, re.MULTILINE)

        for match in matches:
            subsection_text = match.group(1).strip()
            if len(subsection_text) > 10:  # Filter out very short matches
                subsections.append(subsection_text)

        return subsections

    def _calculate_parsing_confidence(self, content: str, title: str) -> float:
        """Calculate confidence score for parsed article"""
        confidence = 0.5  # Base confidence

        # Boost confidence for well-structured content
        if len(content) > 50:
            confidence += 0.1
        if len(title) > 5:
            confidence += 0.1
        if re.search(r'\b(shall|must|will|may)\b', content, re.IGNORECASE):
            confidence += 0.2  # Contains modal verbs typical of ICC rules
        if re.search(r'\b(document|credit|bank|beneficiary|applicant)\b', content, re.IGNORECASE):
            confidence += 0.1  # Contains LC terminology

        # Penalize for parsing issues
        if content.count('PAGE') > 2:
            confidence -= 0.2  # Likely contains page break artifacts
        if len(content.split()) < 10:
            confidence -= 0.3  # Too short to be meaningful

        return max(0.1, min(1.0, confidence))

    def _extract_metadata(self, text_content: str, document_type: DocumentType) -> Dict[str, Any]:
        """Extract document metadata"""
        metadata = {
            'document_type': document_type.value,
            'extracted_at': datetime.now().isoformat()
        }

        # Extract version information
        version_patterns = [
            r'Version\s+(\d+\.?\d*)',
            r'Publication\s+(\d+)',
            r'UCP\s*(\d+)',
            r'ISBP\s*(\d+)'
        ]

        for pattern in version_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                metadata['version'] = match.group(1)
                break

        # Extract title
        title_match = re.search(r'^(.+?)(?:\n|\r)', text_content)
        if title_match:
            potential_title = title_match.group(1).strip()
            if len(potential_title) < 100:  # Reasonable title length
                metadata['title'] = potential_title

        return metadata

    def _count_pages(self, file_path: Path) -> int:
        """Count total pages in PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception:
            return 0

    def export_parsed_data(self, parsed_doc: ParsedDocument, output_dir: Path) -> Path:
        """
        Export parsed data to JSON for AI processing

        NOTE: This exports structured references only, not full ICC text
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create export data with article references only
        export_data = {
            'document_info': {
                'type': parsed_doc.document_type.value,
                'version': parsed_doc.document_version,
                'total_articles': len(parsed_doc.articles),
                'parsing_timestamp': parsed_doc.parsing_timestamp.isoformat(),
                'confidentiality_notice': 'This contains only article references, not full ICC text'
            },
            'article_references': []
        }

        # Export only article structure, not content
        for article in parsed_doc.articles:
            reference_data = {
                'article_id': article.article_id,
                'title': article.title,
                'has_subsections': len(article.subsections) > 0,
                'subsection_count': len(article.subsections),
                'confidence': article.confidence,
                'content_length': len(article.content),  # Length only, not content
                'contains_keywords': self._extract_keywords_only(article.content)
            }
            export_data['article_references'].append(reference_data)

        # Save to file
        import json
        output_file = output_dir / f"{parsed_doc.document_type.value}_references.json"
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported article references to {output_file}")
        return output_file

    def _extract_keywords_only(self, content: str) -> List[str]:
        """Extract keywords for AI context without exposing full content"""
        # Common LC/trade finance keywords
        keywords = []
        keyword_patterns = [
            r'\b(document|documents)\b',
            r'\b(credit|credits)\b',
            r'\b(bank|banking)\b',
            r'\b(beneficiary|beneficiaries)\b',
            r'\b(applicant|applicants)\b',
            r'\b(presentation|present)\b',
            r'\b(examination|examine)\b',
            r'\b(compliance|complying)\b',
            r'\b(discrepancy|discrepancies)\b'
        ]

        for pattern in keyword_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                keywords.append(pattern.replace(r'\b', '').replace(r'|.*?\b', '').strip('()'))

        return list(set(keywords))  # Remove duplicates

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary parser files")
        except Exception as e:
            logger.warning(f"Could not clean temp files: {e}")


def main():
    """Demo ICC document parser"""
    parser = ICCDocumentParser()

    print("=== ICC Document Parser Demo ===")
    print("NOTE: This parser is designed for internal rule generation only.")
    print("ICC documents contain copyrighted material and must not be redistributed.\n")

    # Example usage (would require actual ICC PDF files)
    sample_files = [
        "ucp600.pdf",
        "isbp.pdf"
    ]

    for filename in sample_files:
        file_path = Path(filename)
        if file_path.exists():
            try:
                print(f"Parsing {filename}...")
                parsed_doc = parser.parse_document(file_path)

                print(f"  Document Type: {parsed_doc.document_type.value}")
                print(f"  Articles Found: {len(parsed_doc.articles)}")
                print(f"  Average Confidence: {sum(a.confidence for a in parsed_doc.articles) / len(parsed_doc.articles):.2f}")

                # Export references only
                output_dir = Path("parsed_output")
                exported_file = parser.export_parsed_data(parsed_doc, output_dir)
                print(f"  Exported to: {exported_file}")

            except Exception as e:
                print(f"  Error parsing {filename}: {e}")
        else:
            print(f"  {filename} not found (demo only)")

    parser.cleanup_temp_files()
    print("\nParser demo complete.")


if __name__ == "__main__":
    main()