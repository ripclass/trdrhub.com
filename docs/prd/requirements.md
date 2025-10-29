# Requirements

## Functional Requirements (FR)

- **FR1**: The system must allow a user to upload a Letter of Credit, a Commercial Invoice, and a Bill of Lading in PDF and common image formats.
- **FR2**: The system must use Optical Character Recognition (OCR) to extract key data fields from the uploaded documents.
- **FR3**: The system must validate the extracted data against a core set of deterministic rules based on UCP 600, focusing on Dates, Amounts, Parties, and Ports.
- **FR4**: The system must perform cross-document consistency checks for key fields (e.g., amounts, ports) between the uploaded documents.
- **FR5**: The system must generate a downloadable PDF report summarizing all findings.
- **FR6**: The PDF report must clearly list all identified discrepancies.
- **FR7**: The report must include a checklist of all documents required by the LC and their validation status.
- **FR8**: The report must display a summary of key deadlines.
- **FR9**: The system must provide a simple, linear workflow from document upload → issue review → report download.
- **FR10**: The system must provide a user-facing visual matrix (Cross-Check Matrix) showing side-by-side field comparisons across documents.

## Non-Functional Requirements (NFR)

- **NFR1**: The user interface must be available in both English and Bangla.
- **NFR2**: The web application must be fully responsive and usable on both desktop and mobile browsers.
- **NFR3**: The end-to-end validation process, from document upload to report availability, should feel near-instantaneous to the user (target < 30 seconds).
- **NFR4**: All user-uploaded documents and extracted data must be encrypted both in transit (TLS 1.3) and at rest (AES-256).
- **NFR5**: User-uploaded documents must be automatically and permanently deleted from the system after a defined retention period (e.g., 7 days).
- **NFR6**: The system must maintain an immutable audit log for each validation check.
