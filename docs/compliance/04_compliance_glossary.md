# Compliance Glossary

**Document Version:** 1.0
**Last Updated:** September 17, 2025
**Target Audience:** SMEs, Banks, Financial Institutions
**LCopilot Version:** Sprint 8.2

## Introduction

This glossary provides definitions for key terms used in international trade finance, letters of credit, and compliance standards. Terms are explained in plain language with specific context for how they apply to banking operations and the LCopilot platform.

---

#### Acceptance
**Definition:** A time draft that has been accepted by the drawee bank or party, creating an obligation to pay at maturity
**Bank/Legal Context:** Banks use acceptance to extend credit terms while maintaining document control
**LCopilot Relevance:** Draft examination workflow validates acceptance signatures and maturity dates
**Related Rules/Docs:** UCP 600 Art. 6, 7

---

#### Advising Bank
**Definition:** A bank that notifies the beneficiary of a letter of credit on behalf of the issuing bank
**Bank/Legal Context:** Acts as intermediary but doesn't guarantee payment unless also confirming
**LCopilot Relevance:** Party identification in LC workflows, notification management
**Related Rules/Docs:** UCP 600 Art. 9

---

#### Air Waybill (AWB)
**Definition:** Transport document for air cargo shipments, not negotiable
**Bank/Legal Context:** Evidence of air transport but cannot be used as title document
**LCopilot Relevance:** AWB validation engine checks flight details, routing, consignee information
**Related Rules/Docs:** UCP 600 Art. 23, ISBP 745 G1-G10

---

#### Amendment
**Definition:** A change or modification to the terms and conditions of a letter of credit
**Bank/Legal Context:** Must be agreed by all parties; partial acceptance not permitted
**LCopilot Relevance:** Amendment tracking and approval workflows
**Related Rules/Docs:** UCP 600 Art. 10

---

#### Applicant
**Definition:** The party (usually buyer/importer) who requests the issuance of a letter of credit
**Bank/Legal Context:** Primary obligor to the issuing bank for reimbursement
**LCopilot Relevance:** Entity management, invoice validation, waiver processes
**Related Rules/Docs:** UCP 600 Art. 2

---

#### Beneficiary
**Definition:** The party (usually seller/exporter) in whose favor a letter of credit is issued
**Bank/Legal Context:** Has right to present documents and receive payment upon compliance
**LCopilot Relevance:** Document presentation tracking, compliance verification
**Related Rules/Docs:** UCP 600 Art. 2

---

#### Bill of Exchange
**Definition:** Unconditional written order for payment of a specific amount at a specified time
**Bank/Legal Context:** Negotiable instrument that creates payment obligations
**LCopilot Relevance:** Draft examination engine validates signatures, amounts, maturity terms
**Related Rules/Docs:** UCP 600 Art. 6, ISBP 745 C1-C5

---

#### Bill of Lading (B/L)
**Definition:** Transport document evidencing receipt of goods for shipment and serving as title document
**Bank/Legal Context:** Negotiable document representing ownership of goods
**LCopilot Relevance:** B/L examination engine validates on-board notations, shipping dates, ports
**Related Rules/Docs:** UCP 600 Art. 20, ISBP 745 E1-E12

---

#### Certificate of Origin
**Definition:** Document certifying the country where goods were manufactured or produced
**Bank/Legal Context:** Required for customs clearance and preferential trade treatment
**LCopilot Relevance:** Origin validation with trade agreement verification
**Related Rules/Docs:** ISBP 745 L1-L4

---

#### Charter Party
**Definition:** Contract between shipowner and charterer for use of vessel
**Bank/Legal Context:** Charter party bills of lading are generally not acceptable unless specifically allowed
**LCopilot Relevance:** Charter party B/L identification and validation warnings
**Related Rules/Docs:** UCP 600 Art. 22, ISBP 745 F1-F7

---

#### CIF (Cost, Insurance, Freight)
**Definition:** Incoterm where seller pays costs, insurance, and freight to named destination
**Bank/Legal Context:** Commonly used in LC terms, affects insurance requirements
**LCopilot Relevance:** Insurance coverage calculations, amount validation
**Related Rules/Docs:** ISBP 745 K2

---

#### CIP (Carriage and Insurance Paid)
**Definition:** Incoterm where seller pays carriage and insurance to named destination
**Bank/Legal Context:** Similar to CIF but for any mode of transport
**LCopilot Relevance:** Insurance coverage validation, multimodal transport support
**Related Rules/Docs:** ISBP 745 K2

---

#### Clean Transport Document
**Definition:** Transport document without clauses or notations indicating defective goods or packaging
**Bank/Legal Context:** Banks only accept clean transport documents unless credit specifically allows claused documents
**LCopilot Relevance:** Document quality assessment, clause detection algorithms
**Related Rules/Docs:** UCP 600 Art. 27

---

#### Commercial Invoice
**Definition:** Document listing goods sold, quantities, prices, and commercial terms
**Bank/Legal Context:** Key document for customs valuation and LC compliance
**LCopilot Relevance:** Invoice validation engine, amount verification, goods description matching
**Related Rules/Docs:** UCP 600 Art. 18, ISBP 745 B1-B8

---

#### Complying Presentation
**Definition:** Document presentation that conforms to all credit terms and conditions
**Bank/Legal Context:** Triggers bank's obligation to honor payment under UCP rules
**LCopilot Relevance:** Compliance scoring engine, discrepancy detection
**Related Rules/Docs:** UCP 600 Art. 14

---

#### Confirmed Letter of Credit
**Definition:** LC where a second bank (confirming bank) adds its payment undertaking
**Bank/Legal Context:** Provides additional security as beneficiary has recourse to two banks
**LCopilot Relevance:** Confirmation tracking, multiple bank workflow management
**Related Rules/Docs:** UCP 600 Art. 8

---

#### Confirming Bank
**Definition:** Bank that adds its confirmation to a letter of credit
**Bank/Legal Context:** Assumes same obligations as issuing bank for complying presentations
**LCopilot Relevance:** Multi-bank authorization workflows, payment routing
**Related Rules/Docs:** UCP 600 Art. 8

---

#### Consignee
**Definition:** Party to whom goods are shipped and delivered
**Bank/Legal Context:** Must match credit terms; may differ from applicant in specific cases
**LCopilot Relevance:** Transport document validation, party verification
**Related Rules/Docs:** ISBP 745 E1, G1

---

#### Container Load Plan
**Definition:** Document showing arrangement of goods within shipping containers
**Bank/Legal Context:** Sometimes required for containerized shipments
**LCopilot Relevance:** Specialized document validation for container shipments
**Related Rules/Docs:** ISBP interpretation notes

---

#### Correspondent Bank
**Definition:** Bank that provides services to another bank in a different location
**Bank/Legal Context:** Facilitates international payments and LC operations
**LCopilot Relevance:** Payment routing, SWIFT message handling
**Related Rules/Docs:** UCP 600 general provisions

---

#### Credit
**Definition:** Short form for "documentary credit" or letter of credit
**Bank/Legal Context:** Standardized term used throughout UCP rules
**LCopilot Relevance:** System terminology, API endpoint naming
**Related Rules/Docs:** UCP 600 Art. 2

---

#### Data Residency
**Definition:** Legal requirement for data to be stored within specific geographic boundaries
**Bank/Legal Context:** Critical for regulatory compliance, especially in banking
**LCopilot Relevance:** Tenant data residency policies enforce geographic storage controls
**Related Rules/Docs:** GDPR, Bangladesh Bank regulations

---

#### Deferred Payment
**Definition:** Payment method where bank undertakes to pay at a determinable future date
**Bank/Legal Context:** Provides financing without creating negotiable instruments
**LCopilot Relevance:** Payment method tracking, maturity date calculations
**Related Rules/Docs:** UCP 600 Art. 7, 12

---

#### Discrepancy
**Definition:** Inconsistency between presented documents and credit terms
**Bank/Legal Context:** Grounds for refusing documents unless waived by applicant
**LCopilot Relevance:** Automated discrepancy detection, severity assessment
**Related Rules/Docs:** UCP 600 Art. 16

---

#### Document Against Acceptance (D/A)
**Definition:** Collection method where documents released upon acceptance of draft
**Bank/Legal Context:** Provides financing through time drafts
**LCopilot Relevance:** Collection workflow management, draft tracking
**Related Rules/Docs:** URC 522

---

#### Document Against Payment (D/P)
**Definition:** Collection method where documents released only upon payment
**Bank/Legal Context:** Sight payment collections with immediate settlement
**LCopilot Relevance:** Collection workflow automation, payment verification
**Related Rules/Docs:** URC 522

---

#### Documentary Collection
**Definition:** Bank service for handling documents against payment or acceptance
**Bank/Legal Context:** Less secure than LC but lower cost alternative
**LCopilot Relevance:** Collection module in broader trade finance platform
**Related Rules/Docs:** URC 522

---

#### Documentary Credit
**Definition:** Letter of credit - bank's conditional payment undertaking based on documents
**Bank/Legal Context:** Primary instrument for international trade finance
**LCopilot Relevance:** Core platform functionality, full LC lifecycle management
**Related Rules/Docs:** UCP 600 Art. 2

---

#### Drawee
**Definition:** Party on whom a bill of exchange is drawn (who must pay)
**Bank/Legal Context:** Usually the issuing bank or applicant in LC transactions
**LCopilot Relevance:** Draft validation, payment obligation tracking
**Related Rules/Docs:** UCP 600 Art. 6

---

#### Drawer
**Definition:** Party who draws/creates a bill of exchange
**Bank/Legal Context:** Usually the beneficiary demanding payment
**LCopilot Relevance:** Draft examination, signature validation
**Related Rules/Docs:** UCP 600 Art. 6

---

#### Electronic Presentation
**Definition:** Submission of electronic documents instead of paper documents
**Bank/Legal Context:** Governed by eUCP rules as supplement to UCP 600
**LCopilot Relevance:** Digital document handling, electronic signature validation
**Related Rules/Docs:** eUCP Version 2.0

---

#### Encryption at Rest
**Definition:** Cryptographic protection of data when stored in databases or file systems
**Bank/Legal Context:** Required for financial data protection and regulatory compliance
**LCopilot Relevance:** KMS integration encrypts all stored documents and database records
**Related Rules/Docs:** PCI DSS, GDPR data protection

---

#### eUCP (Electronic UCP)
**Definition:** ICC rules supplement to UCP 600 for electronic document presentation
**Bank/Legal Context:** Enables paperless LC transactions with digital documents
**LCopilot Relevance:** Electronic document workflows, digital signature validation
**Related Rules/Docs:** eUCP Version 2.0

---

#### Expiry Date
**Definition:** Latest date for document presentation under a letter of credit
**Bank/Legal Context:** After expiry, documents cannot be presented even if otherwise complying
**LCopilot Relevance:** Timeline validation, expiry warnings and enforcement
**Related Rules/Docs:** UCP 600 Art. 6

---

#### FOB (Free on Board)
**Definition:** Incoterm where seller's responsibility ends when goods pass ship's rail
**Bank/Legal Context:** Affects insurance requirements and risk transfer point
**LCopilot Relevance:** Transport document validation, insurance coverage assessment
**Related Rules/Docs:** Incoterms 2020

---

#### Force Majeure
**Definition:** Unforeseeable circumstances preventing contract performance
**Bank/Legal Context:** Banks disclaim liability for delays due to force majeure events
**LCopilot Relevance:** Force majeure event logging, business continuity procedures
**Related Rules/Docs:** UCP 600 Art. 35, 38

---

#### Freight Collect
**Definition:** Shipping arrangement where freight charges paid by consignee at destination
**Bank/Legal Context:** Affects CIF/CFR term compliance and document requirements
**LCopilot Relevance:** Transport document validation, freight term verification
**Related Rules/Docs:** ISBP 745 transport document sections

---

#### Freight Prepaid
**Definition:** Shipping arrangement where freight charges paid by shipper in advance
**Bank/Legal Context:** Required for CIF/CFR terms, evidenced on transport documents
**LCopilot Relevance:** Freight payment verification, Incoterm compliance
**Related Rules/Docs:** ISBP 745 transport document sections

---

#### Goods Description
**Definition:** Written specification of merchandise covered by the letter of credit
**Bank/Legal Context:** Documents must show goods consistent with credit description
**LCopilot Relevance:** AI-powered semantic matching for description consistency
**Related Rules/Docs:** UCP 600 Art. 14, ISBP 745 B2

---

#### Honor
**Definition:** Bank's payment under a letter of credit for complying presentation
**Bank/Legal Context:** Bank's irrevocable obligation upon document compliance
**LCopilot Relevance:** Payment workflow automation, compliance verification
**Related Rules/Docs:** UCP 600 Art. 7

---

#### ICC (International Chamber of Commerce)
**Definition:** Global business organization that publishes trade finance rules
**Bank/Legal Context:** Authoritative source for UCP, ISBP, URC, and other trade rules
**LCopilot Relevance:** Compliance framework based on ICC standards
**Related Rules/Docs:** UCP 600, ISBP 745, eUCP, URC 522

---

#### Incoterms
**Definition:** ICC rules for interpretation of trade terms (FOB, CIF, etc.)
**Bank/Legal Context:** Define seller/buyer responsibilities, affect document requirements
**LCopilot Relevance:** Trade term validation, insurance and transport requirements
**Related Rules/Docs:** Incoterms 2020

---

#### Inspection Certificate
**Definition:** Document certifying goods meet specified quality or quantity standards
**Bank/Legal Context:** Often required for commodity trades or specific regulations
**LCopilot Relevance:** Certificate validation, issuing authority verification
**Related Rules/Docs:** ISBP 745 O1-O2

---

#### Insurance Certificate
**Definition:** Evidence of insurance coverage for goods in transit
**Bank/Legal Context:** Must cover at least 110% of CIF value unless stated otherwise
**LCopilot Relevance:** Coverage amount validation, risk assessment, currency matching
**Related Rules/Docs:** UCP 600 Art. 28, ISBP 745 K1-K13

---

#### ISBP (International Standard Banking Practice)
**Definition:** ICC guidance for examining documents under documentary credits
**Bank/Legal Context:** Authoritative interpretation of UCP 600 requirements
**LCopilot Relevance:** Document examination engine implements ISBP standards
**Related Rules/Docs:** ISBP 745 (current version)

---

#### Issuing Bank
**Definition:** Bank that issues the letter of credit on behalf of the applicant
**Bank/Legal Context:** Primary obligor with irrevocable payment undertaking
**LCopilot Relevance:** Bank entity management, authorization workflows
**Related Rules/Docs:** UCP 600 Art. 7

---

#### Latest Shipment Date
**Definition:** Last permitted date for goods to be shipped under the credit
**Bank/Legal Context:** Transport documents must evidence shipment by this date
**LCopilot Relevance:** Timeline validation, shipment date verification algorithms
**Related Rules/Docs:** UCP 600 Art. 6

---

#### Letter of Credit (LC)
**Definition:** Conditional bank payment undertaking in favor of beneficiary
**Bank/Legal Context:** Primary instrument for reducing payment risk in international trade
**LCopilot Relevance:** Core platform product, full lifecycle management
**Related Rules/Docs:** UCP 600 Art. 2

---

#### Marine Insurance
**Definition:** Insurance coverage for goods transported by sea
**Bank/Legal Context:** Standard requirement for CIF/CIP terms
**LCopilot Relevance:** Insurance validation engine, coverage adequacy assessment
**Related Rules/Docs:** UCP 600 Art. 28, Institute Cargo Clauses

---

#### Multimodal Transport
**Definition:** Carriage of goods using more than one mode of transport
**Bank/Legal Context:** Requires multimodal transport documents covering entire journey
**LCopilot Relevance:** Complex routing validation, multi-leg transport verification
**Related Rules/Docs:** UCP 600 Art. 19, ISBP 745 J1-J6

---

#### Negotiation
**Definition:** Bank's examination and purchase of documents for value
**Bank/Legal Context:** Creates negotiable relationship between beneficiary and negotiating bank
**LCopilot Relevance:** Negotiation workflow management, value date calculations
**Related Rules/Docs:** UCP 600 Art. 6, 7

---

#### Nominated Bank
**Definition:** Bank specifically authorized to pay, accept, or negotiate under the credit
**Bank/Legal Context:** May or may not have obligation to act depending on credit terms
**LCopilot Relevance:** Bank routing, authorization level management
**Related Rules/Docs:** UCP 600 Art. 6, 12

---

#### On Board
**Definition:** Notation indicating goods have been loaded onto the carrying vessel
**Bank/Legal Context:** Required for ocean bills of lading unless credit allows other evidence
**LCopilot Relevance:** OCR detection of on-board notations, date extraction
**Related Rules/Docs:** UCP 600 Art. 20, ISBP 745 E2

---

#### Original Document
**Definition:** Document in its first and primary form, not a copy
**Bank/Legal Context:** UCP accepts reprographic copies if they appear original
**LCopilot Relevance:** Document authenticity assessment, electronic signature validation
**Related Rules/Docs:** UCP 600 Art. 17

---

#### Packing List
**Definition:** Detailed inventory of goods showing quantities, weights, and packaging
**Bank/Legal Context:** Supports customs clearance and cargo verification
**LCopilot Relevance:** Quantity reconciliation, weight validation, packaging verification
**Related Rules/Docs:** ISBP 745 M1-M2

---

#### Partial Shipment
**Definition:** Shipment of goods in parts rather than as a single consignment
**Bank/Legal Context:** Prohibited unless specifically allowed by credit terms
**LCopilot Relevance:** Shipment analysis, quantity tracking across presentations
**Related Rules/Docs:** UCP 600 Art. 31

---

#### Presentation
**Definition:** Delivery of documents to the nominated or issuing bank
**Bank/Legal Context:** Triggers bank's examination period and payment obligations
**LCopilot Relevance:** Document receipt tracking, examination timeline management
**Related Rules/Docs:** UCP 600 Art. 14

---

#### Reimbursing Bank
**Definition:** Bank authorized to reimburse the nominated bank upon document compliance
**Bank/Legal Context:** Facilitates payment flows in multi-bank LC transactions
**LCopilot Relevance:** Payment routing, SWIFT reimbursement messaging
**Related Rules/Docs:** UCP 600 Art. 13

---

#### Sight Payment
**Definition:** Payment immediately upon presentation of complying documents
**Bank/Legal Context:** Most common LC availability method with immediate settlement
**LCopilot Relevance:** Payment processing, immediate settlement workflows
**Related Rules/Docs:** UCP 600 Art. 6, 7

---

#### SWIFT
**Definition:** Society for Worldwide Interbank Financial Telecommunication
**Bank/Legal Context:** Secure messaging network for international financial transactions
**LCopilot Relevance:** LC messaging, authentication, payment routing integration
**Related Rules/Docs:** SWIFT MT700, MT720 message formats

---

#### Tolerance
**Definition:** Permitted variation in credit amount, quantity, or unit price
**Bank/Legal Context:** UCP allows 10% tolerance unless credit states otherwise
**LCopilot Relevance:** Automatic tolerance calculations, variance analysis
**Related Rules/Docs:** UCP 600 Art. 30

---

#### Trade Finance
**Definition:** Banking products that facilitate international commerce
**Bank/Legal Context:** Includes letters of credit, guarantees, collections, and financing
**LCopilot Relevance:** Platform scope encompasses full trade finance product suite
**Related Rules/Docs:** Various ICC and banking regulations

---

#### Transferable Credit
**Definition:** Letter of credit that can be transferred to secondary beneficiaries
**Bank/Legal Context:** Enables intermediary trading with specific transfer conditions
**LCopilot Relevance:** Transfer workflow management, beneficiary substitution
**Related Rules/Docs:** UCP 600 Art. 38

---

#### Transport Document
**Definition:** Document evidencing carriage of goods (B/L, AWB, CMR, etc.)
**Bank/Legal Context:** Must evidence shipment and meet credit requirements
**LCopilot Relevance:** Multi-modal transport validation, route verification
**Related Rules/Docs:** UCP 600 Art. 19-26

---

#### UCP 600
**Definition:** Uniform Customs and Practice for Documentary Credits, 2007 revision
**Bank/Legal Context:** Global standard rules governing letter of credit operations
**LCopilot Relevance:** Compliance framework foundation, rule engine implementation
**Related Rules/Docs:** UCP 600 (complete text)

---

#### URC 522
**Definition:** Uniform Rules for Collections governing documentary collections
**Bank/Legal Context:** ICC rules for collection operations (D/P, D/A)
**LCopilot Relevance:** Collection module compliance framework
**Related Rules/Docs:** URC 522

---

#### Waiver
**Definition:** Applicant's authorization to accept discrepant documents
**Bank/Legal Context:** Allows payment despite document discrepancies
**LCopilot Relevance:** Waiver workflow, discrepancy resolution tracking
**Related Rules/Docs:** UCP 600 Art. 16

---

#### Weight Certificate
**Definition:** Document certifying the weight of shipped goods
**Bank/Legal Context:** Required for weight-based pricing or regulatory compliance
**LCopilot Relevance:** Weight validation, quantity reconciliation across documents
**Related Rules/Docs:** ISBP 745 N1-N4

---

## Term Count Summary

**Total Entries:** 68
**Categories:**
- Banking/LC Terms: 45
- Document Types: 12
- Technical/Compliance: 8
- Trade Terms: 3

---

*This glossary serves as a reference for LCopilot users and supports regulatory compliance documentation. Terms are updated with each platform release to maintain accuracy.*