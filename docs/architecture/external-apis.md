# External APIs

The MVP's core functionality relies on a dual-engine OCR strategy using an Adapter Pattern to abstract the vendors. The OCRManager will orchestrate calls to concrete OCREngine implementations, normalizing their results.

- **Google Cloud Vision (Document AI)**: Primary OCR engine.
- **AWS Textract**: Secondary OCR engine for fallback and comparison.
