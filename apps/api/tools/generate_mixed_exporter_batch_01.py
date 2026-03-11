from pathlib import Path
import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

OUT_BASE = Path(r'H:\.openclaw\workspace\synthetic_exporter_mixed_batch_01')
OUT_BASE.mkdir(parents=True, exist_ok=True)

CORE_MT = '''DOCUMENTARY CREDIT NO: {lc_no}
FORM OF DOCUMENTARY CREDIT: IRREVOCABLE
DATE OF ISSUE: 11 MARCH 2026
APPLICANT: {applicant}
BENEFICIARY: {beneficiary}
AMOUNT: USD {amount}
AVAILABLE WITH ANY BANK BY NEGOTIATION
PARTIAL SHIPMENTS: ALLOWED
TRANSSHIPMENT: ALLOWED
LATEST DATE OF SHIPMENT: 25 APRIL 2026
PORT OF LOADING: CHITTAGONG / CHATTOGRAM / CTG PORT
PORT OF DISCHARGE: JEBEL ALI, UAE
GOODS: 100% COTTON KNIT T-SHIRTS, MEN'S BASIC ROUND NECK, 180 GSM
DOCUMENTS REQUIRED: SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS, FULL SET CLEAN ON BOARD BILL OF LADING, PACKING LIST, CERTIFICATE OF ORIGIN, INSURANCE CERTIFICATE, BENEFICIARY CERTIFICATE.
ADDITIONAL CONDITIONS: ALL DOCUMENTS MUST QUOTE THIS CREDIT NUMBER. SPELLING VARIANTS OF PORT NAMES MAY APPEAR IN SUPPORTING DOCUMENTS.
'''

CORE_ISO = '''<Document><BkToCstmrDoc><Tx><DocumentaryCredit><CreditNumber>{lc_no}</CreditNumber><IssueDate>2026-03-11</IssueDate><Applicant>{applicant}</Applicant><Beneficiary>{beneficiary}</Beneficiary><Amount currency="USD">{amount}</Amount><PortOfLoading>Chattogram</PortOfLoading><PortOfDischarge>Jebel Ali</PortOfDischarge><GoodsDescription>100 percent cotton knit t shirts, men's round neck, assorted sizes, export packing.</GoodsDescription><RequiredDocuments>Commercial Invoice; Bill of Lading; Packing List; Certificate of Origin; Insurance Certificate; Beneficiary Certificate.</RequiredDocuments></DocumentaryCredit></Tx></BkToCstmrDoc></Document>'''

INVOICE = '''COMMERCIAL INVOICE
Invoice No: INV-{n}
Invoice Date: 2026-03-11
Seller: {beneficiary}
Buyer: {applicant}
Port of Loading: Chattogram
Port of Discharge: Jebel Ali
Description: Cotton knit t-shirts packed in export cartons.
Amount: USD {amount}
Gross Weight: 525.68 KG
Net Weight: 492.78 KG
'''

BL = '''BILL OF LADING
B/L No: BL-{n}
Shipper: {beneficiary}
Consignee: {applicant}
Port of Loading: CTG / Chittagong / Chattogram
Port of Discharge: Jebel Ali
Vessel: OCEAN UNITY
Voyage: V-{n}
Gross Weight: 525.68 KG
'''

PACKING = '''PACKING LIST
Packing List No: PL-{n}
Exporter: {beneficiary}
Importer: {applicant}
Cartons: 250
Gross Weight: 525.68 KG
Net Weight: 492.78 KG
Dimensions: 120 x 80 x 60 CM
'''

DOCS = {
 'Air_Waybill.pdf': 'AIR WAYBILL\nAWB No: AWB-{n}\nAirport of Departure: DAC\nAirport of Destination: DXB\nShipper: {beneficiary}\nConsignee: {applicant}\nGross Weight: 525.68 KG\n',
 'Sea_Waybill.pdf': 'SEA WAYBILL\nB/L No: SWB-{n}\nPort of Loading: Chattogram\nPort of Discharge: Jebel Ali\nVessel: SEA BRIGHT\nVoyage: SW-{n}\nShipper: {beneficiary}\nConsignee: {applicant}\n',
 'FCR.pdf': "FORWARDER'S CERTIFICATE OF RECEIPT\nFCR No: FCR-{n}\nShipper: {beneficiary}\nConsignee: {applicant}\nIssued By: Forwarder One\n",
 'Weight_Certificate.pdf': 'WEIGHT CERTIFICATE\nGROSS: 525.68 KG\nNET: 492.78 KG\nIssued By: Independent Surveyor\n',
 'Measurement_Certificate.pdf': 'MEASUREMENT CERTIFICATE\nDimensions: 120 x 80 x 60 CM\nIssued By: Independent Surveyor\n',
 'Lab_Test_Report.pdf': 'LAB TEST REPORT\nLaboratory: Intertek\nTest Result: PASS\nAnalysis Result: Fiber composition 100 percent cotton.\n',
 'SGS_Certificate.pdf': 'SGS CERTIFICATE\nInspection Agency: SGS\nInspection Result: PASSED\n',
 'Certificate_of_Conformity.pdf': 'CERTIFICATE OF CONFORMITY\nCertificate Number: COC-{n}\nIssued By: Testing Authority\n',
 'Beneficiary_Certificate.pdf': 'BENEFICIARY CERTIFICATE\nCertificate No: BEN-{n}\nIssued By: {beneficiary}\n',
 'Insurance_Policy.pdf': 'INSURANCE POLICY\nPolicy No: POL-{n}\nInsured Amount: USD {amount}\nInsurer: Global Insurance Co\n',
 'Phytosanitary_Certificate.pdf': 'PHYTOSANITARY CERTIFICATE\nCertificate Number: PHY-{n}\nIssuing Authority: Plant Quarantine Authority\n',
 'Fumigation_Certificate.pdf': 'FUMIGATION CERTIFICATE\nCertificate Number: FUM-{n}\nIssuing Authority: Fumigation Services Ltd\n',
 'Export_License.pdf': 'EXPORT LICENSE\nLicense No: EXP-{n}\nIssued By: Export Promotion Bureau\n',
 'Import_License.pdf': 'IMPORT LICENSE\nLicense No: IMP-{n}\nIssued By: Trade Authority\n',
 'Customs_Declaration.pdf': 'CUSTOMS DECLARATION\nDeclaration No: CUS-{n}\nIssued By: Customs Authority\n',
 'Bank_Guarantee.pdf': 'BANK GUARANTEE\nGuarantee No: BG-{n}\nApplicant: {applicant}\nBeneficiary: {beneficiary}\nGuarantee Amount: USD {amount}\n',
 'SBLC.pdf': 'STANDBY LETTER OF CREDIT\nLC Number: SBLC-{n}\nApplicant: {applicant}\nBeneficiary: {beneficiary}\nAmount: USD {amount}\n',
 'Bill_of_Exchange.pdf': 'BILL OF EXCHANGE\nDraft No: BOE-{n}\nAmount: USD {amount}\nDrawer: {beneficiary}\nDrawee: {applicant}\n',
 'Promissory_Note.pdf': 'PROMISSORY NOTE\nNote No: PN-{n}\nAmount: USD {amount}\nMaker: {applicant}\nPayee: {beneficiary}\n',
 'Payment_Receipt.pdf': 'PAYMENT RECEIPT\nReceipt No: RC-{n}\nReceipt Amount: USD {amount}\nReceived From: {applicant}\n',
 'Debit_Note.pdf': 'DEBIT NOTE\nDebit Note No: DN-{n}\nAmount: USD 1000\n',
 'Credit_Note.pdf': 'CREDIT NOTE\nCredit Note No: CN-{n}\nAmount: USD 800\n',
 'Health_Certificate.pdf': 'HEALTH CERTIFICATE\nCertificate Number: HC-{n}\nIssuing Authority: Health Authority\n',
 'Veterinary_Certificate.pdf': 'VETERINARY CERTIFICATE\nCertificate Number: VET-{n}\nIssuing Authority: Veterinary Authority\n',
 'Sanitary_Certificate.pdf': 'SANITARY CERTIFICATE\nCertificate Number: SAN-{n}\nIssuing Authority: Sanitary Authority\n',
 'CITES_Permit.pdf': 'CITES PERMIT\nPermit Number: CIT-{n}\nIssued By: Wildlife Authority\n',
 'Radiation_Certificate.pdf': 'RADIATION CERTIFICATE\nCertificate Number: RAD-{n}\nIssued By: Radiation Authority\n',
 'Organic_Certificate.pdf': 'ORGANIC CERTIFICATE\nCertificate No: ORG-{n}\nIssued By: Organic Board\n',
 'Non_Manipulation_Certificate.pdf': 'NON-MANIPULATION CERTIFICATE\nCertificate Number: NMC-{n}\nIssued By: Port Authority\n',
 'Other_Document.pdf': 'SPECIAL TRADE SUPPORTING MEMO\nPermit issued for export support. Shipment reference and internal notes included for manual review.\n'
}

MATRIX = [
 {'set':'mix_001_mt_transport_quality','lc':'mt','extras':['Air_Waybill.pdf','Weight_Certificate.pdf','Beneficiary_Certificate.pdf']},
 {'set':'mix_002_mt_finreg','lc':'mt','extras':['Bank_Guarantee.pdf','Payment_Receipt.pdf','Phytosanitary_Certificate.pdf']},
 {'set':'mix_003_mt_transport_lab','lc':'mt','extras':['FCR.pdf','Lab_Test_Report.pdf','Certificate_of_Conformity.pdf']},
 {'set':'mix_004_mt_sblc_cites','lc':'mt','extras':['SBLC.pdf','Debit_Note.pdf','CITES_Permit.pdf']},
 {'set':'mix_005_iso_transport_health','lc':'iso','extras':['Sea_Waybill.pdf','Health_Certificate.pdf','Import_License.pdf']},
 {'set':'mix_006_iso_invoice_notes','lc':'iso','extras':['Credit_Note.pdf','Promissory_Note.pdf','Export_License.pdf']},
 {'set':'mix_007_iso_specials','lc':'iso','extras':['Organic_Certificate.pdf','Non_Manipulation_Certificate.pdf','Customs_Declaration.pdf']},
 {'set':'mix_008_mt_measurement','lc':'mt','extras':['Measurement_Certificate.pdf','Insurance_Policy.pdf','Fumigation_Certificate.pdf']},
 {'set':'mix_009_iso_veterinary','lc':'iso','extras':['Veterinary_Certificate.pdf','Payment_Receipt.pdf','Air_Waybill.pdf']},
 {'set':'mix_010_mt_sgs','lc':'mt','extras':['SGS_Certificate.pdf','Bill_of_Exchange.pdf','Sanitary_Certificate.pdf']},
 {'set':'mix_011_iso_radiation','lc':'iso','extras':['Radiation_Certificate.pdf','Beneficiary_Certificate.pdf','Sea_Waybill.pdf']},
 {'set':'mix_012_mt_unknown','lc':'mt','extras':['Other_Document.pdf','Customs_Declaration.pdf','Promissory_Note.pdf']},
]

def pdf(path: Path, title: str, body: str):
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 20*mm
    c.setFont('Helvetica-Bold', 13)
    c.drawString(20*mm, y, title)
    y -= 10*mm
    c.setFont('Helvetica', 10)
    for para in body.split('\n'):
        line = para.strip()
        if not line:
            y -= 4*mm
            continue
        chunks = [line[i:i+95] for i in range(0, len(line), 95)]
        for ch in chunks:
            if y < 20*mm:
                c.showPage(); y = height - 20*mm; c.setFont('Helvetica',10)
            c.drawString(15*mm, y, ch)
            y -= 5*mm
    c.save()

manifest = []
for idx, spec in enumerate(MATRIX, start=1):
    n = f'{idx:03d}'
    folder = OUT_BASE / spec['set']
    folder.mkdir(parents=True, exist_ok=True)
    applicant = f'Applicant Co {n}'
    beneficiary = f'Beneficiary Co {n}'
    amount = str(25000 + idx*1375)
    lc_no = f'MX{20260311}{idx:03d}'
    lc_text = (CORE_MT if spec['lc']=='mt' else CORE_ISO).format(lc_no=lc_no, applicant=applicant, beneficiary=beneficiary, amount=amount)
    pdf(folder / 'LC.pdf', 'Letter of Credit', lc_text)
    pdf(folder / 'Invoice.pdf', 'Commercial Invoice', INVOICE.format(n=n, applicant=applicant, beneficiary=beneficiary, amount=amount))
    pdf(folder / 'Bill_of_Lading.pdf', 'Bill of Lading', BL.format(n=n, applicant=applicant, beneficiary=beneficiary))
    pdf(folder / 'Packing_List.pdf', 'Packing List', PACKING.format(n=n, applicant=applicant, beneficiary=beneficiary))
    docs = ['LC.pdf','Invoice.pdf','Bill_of_Lading.pdf','Packing_List.pdf']
    for extra in spec['extras']:
        body = DOCS[extra].format(n=n, applicant=applicant, beneficiary=beneficiary, amount=amount)
        pdf(folder / extra, extra.replace('_',' ').replace('.pdf',''), body)
        docs.append(extra)
    manifest.append({'set': spec['set'], 'lc_format': spec['lc'], 'docs': docs})

(OUT_BASE / '_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(OUT_BASE / '_README.txt').write_text('Mixed-family exporter synthetic batch 01 with dense MT + ISO LC texts and cross-family extras.', encoding='utf-8')
print(OUT_BASE)
