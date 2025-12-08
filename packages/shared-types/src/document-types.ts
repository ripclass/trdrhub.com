/**
 * Shared Document Types - Single Source of Truth
 * 
 * This file defines ALL document types used across the TRDR Hub platform.
 * Both frontend and backend import from here to ensure consistency.
 * 
 * RULES:
 * 1. NEVER change existing values (breaks backward compatibility)
 * 2. Always add new types to the appropriate category
 * 3. Keep labels user-friendly for dropdown display
 * 4. Keep values snake_case for API consistency
 */

// =============================================================================
// DOCUMENT TYPE DEFINITIONS
// =============================================================================

/**
 * Document Type Categories for grouping in UI
 */
export const DOCUMENT_CATEGORIES = {
  CORE: 'core',
  TRANSPORT: 'transport',
  INSPECTION: 'inspection',
  HEALTH: 'health',
  FINANCIAL: 'financial',
  CUSTOMS: 'customs',
  OTHER: 'other',
} as const;

export type DocumentCategory = typeof DOCUMENT_CATEGORIES[keyof typeof DOCUMENT_CATEGORIES];

/**
 * Core document type values - used in API payloads
 * These are the canonical values used everywhere in the system.
 */
export const DOCUMENT_TYPE_VALUES = {
  // =========================================================================
  // CORE DOCUMENTS (Required for most LCs)
  // =========================================================================
  LETTER_OF_CREDIT: 'letter_of_credit',
  SWIFT_MESSAGE: 'swift_message',
  LC_APPLICATION: 'lc_application',
  COMMERCIAL_INVOICE: 'commercial_invoice',
  PROFORMA_INVOICE: 'proforma_invoice',
  BILL_OF_LADING: 'bill_of_lading',
  PACKING_LIST: 'packing_list',
  CERTIFICATE_OF_ORIGIN: 'certificate_of_origin',
  INSURANCE_CERTIFICATE: 'insurance_certificate',
  INSURANCE_POLICY: 'insurance_policy',

  // =========================================================================
  // TRANSPORT DOCUMENTS
  // =========================================================================
  OCEAN_BILL_OF_LADING: 'ocean_bill_of_lading',
  SEA_WAYBILL: 'sea_waybill',
  AIR_WAYBILL: 'air_waybill',
  MULTIMODAL_TRANSPORT_DOCUMENT: 'multimodal_transport_document',
  RAILWAY_CONSIGNMENT_NOTE: 'railway_consignment_note',
  ROAD_TRANSPORT_DOCUMENT: 'road_transport_document',
  FORWARDER_CERTIFICATE_OF_RECEIPT: 'forwarder_certificate_of_receipt',
  HOUSE_BILL_OF_LADING: 'house_bill_of_lading',
  MASTER_BILL_OF_LADING: 'master_bill_of_lading',
  SHIPPING_COMPANY_CERTIFICATE: 'shipping_company_certificate',
  MATES_RECEIPT: 'mates_receipt',
  DELIVERY_ORDER: 'delivery_order',

  // =========================================================================
  // INSPECTION & QUALITY CERTIFICATES
  // =========================================================================
  INSPECTION_CERTIFICATE: 'inspection_certificate',
  PRE_SHIPMENT_INSPECTION: 'pre_shipment_inspection',
  QUALITY_CERTIFICATE: 'quality_certificate',
  WEIGHT_CERTIFICATE: 'weight_certificate',
  MEASUREMENT_CERTIFICATE: 'measurement_certificate',
  ANALYSIS_CERTIFICATE: 'analysis_certificate',
  LAB_TEST_REPORT: 'lab_test_report',
  SGS_CERTIFICATE: 'sgs_certificate',
  BUREAU_VERITAS_CERTIFICATE: 'bureau_veritas_certificate',
  INTERTEK_CERTIFICATE: 'intertek_certificate',

  // =========================================================================
  // HEALTH & AGRICULTURAL CERTIFICATES
  // =========================================================================
  PHYTOSANITARY_CERTIFICATE: 'phytosanitary_certificate',
  FUMIGATION_CERTIFICATE: 'fumigation_certificate',
  HEALTH_CERTIFICATE: 'health_certificate',
  VETERINARY_CERTIFICATE: 'veterinary_certificate',
  SANITARY_CERTIFICATE: 'sanitary_certificate',
  CITES_PERMIT: 'cites_permit',
  RADIATION_CERTIFICATE: 'radiation_certificate',
  HALAL_CERTIFICATE: 'halal_certificate',
  KOSHER_CERTIFICATE: 'kosher_certificate',
  ORGANIC_CERTIFICATE: 'organic_certificate',

  // =========================================================================
  // FINANCIAL DOCUMENTS
  // =========================================================================
  DRAFT_BILL_OF_EXCHANGE: 'draft_bill_of_exchange',
  PROMISSORY_NOTE: 'promissory_note',
  BANK_GUARANTEE: 'bank_guarantee',
  STANDBY_LC: 'standby_lc',
  PAYMENT_RECEIPT: 'payment_receipt',
  DEBIT_NOTE: 'debit_note',
  CREDIT_NOTE: 'credit_note',

  // =========================================================================
  // BENEFICIARY & ATTESTATION DOCUMENTS
  // =========================================================================
  BENEFICIARY_CERTIFICATE: 'beneficiary_certificate',
  MANUFACTURER_CERTIFICATE: 'manufacturer_certificate',
  CONFORMITY_CERTIFICATE: 'conformity_certificate',
  NON_MANIPULATION_CERTIFICATE: 'non_manipulation_certificate',

  // =========================================================================
  // CUSTOMS & TRADE COMPLIANCE
  // =========================================================================
  CUSTOMS_DECLARATION: 'customs_declaration',
  EXPORT_LICENSE: 'export_license',
  IMPORT_LICENSE: 'import_license',
  GSP_FORM_A: 'gsp_form_a',
  EUR1_MOVEMENT_CERTIFICATE: 'eur1_movement_certificate',
  WAREHOUSE_RECEIPT: 'warehouse_receipt',
  CARGO_MANIFEST: 'cargo_manifest',

  // =========================================================================
  // OTHER / SUPPORTING
  // =========================================================================
  SUPPORTING_DOCUMENT: 'supporting_document',
  OTHER: 'other',
  UNKNOWN: 'unknown',
} as const;

export type DocumentTypeValue = typeof DOCUMENT_TYPE_VALUES[keyof typeof DOCUMENT_TYPE_VALUES];

// =============================================================================
// DOCUMENT TYPE METADATA
// =============================================================================

export interface DocumentTypeInfo {
  value: DocumentTypeValue;
  label: string;
  shortLabel?: string;  // For compact UI displays
  category: DocumentCategory;
  emoji?: string;       // For visual identification
  aliases: string[];    // For pattern matching and backward compatibility
  description?: string; // Help text
  avgPages?: number;    // Average page count for this document type
  required?: boolean;   // Is this typically required for LC?
}

/**
 * Complete document type registry with metadata
 */
export const DOCUMENT_TYPES: Record<DocumentTypeValue, DocumentTypeInfo> = {
  // =========================================================================
  // CORE DOCUMENTS
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT]: {
    value: DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT,
    label: 'Letter of Credit',
    shortLabel: 'LC',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '📄',
    aliases: ['lc', 'l/c', 'mt700', 'mt760', 'documentary_credit'],
    description: 'MT700/MT760 Letter of Credit document',
    avgPages: 6,
    required: true,
  },
  [DOCUMENT_TYPE_VALUES.SWIFT_MESSAGE]: {
    value: DOCUMENT_TYPE_VALUES.SWIFT_MESSAGE,
    label: 'SWIFT Message',
    shortLabel: 'SWIFT',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '💬',
    aliases: ['swift', 'mt', 'message'],
    description: 'SWIFT banking message (MT series)',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.LC_APPLICATION]: {
    value: DOCUMENT_TYPE_VALUES.LC_APPLICATION,
    label: 'LC Application',
    shortLabel: 'LC App',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '📝',
    aliases: ['lc_app', 'application', 'lc_request'],
    description: 'Application for opening Letter of Credit',
    avgPages: 4,
  },
  [DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE]: {
    value: DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE,
    label: 'Commercial Invoice',
    shortLabel: 'Invoice',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '🧾',
    aliases: ['invoice', 'inv', 'commercial_inv', 'sales_invoice'],
    description: 'Seller\'s invoice for goods shipped',
    avgPages: 2,
    required: true,
  },
  [DOCUMENT_TYPE_VALUES.PROFORMA_INVOICE]: {
    value: DOCUMENT_TYPE_VALUES.PROFORMA_INVOICE,
    label: 'Proforma Invoice',
    shortLabel: 'Proforma',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '📋',
    aliases: ['proforma', 'pro_forma', 'pi'],
    description: 'Preliminary invoice before shipment',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.BILL_OF_LADING]: {
    value: DOCUMENT_TYPE_VALUES.BILL_OF_LADING,
    label: 'Bill of Lading',
    shortLabel: 'B/L',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🚢',
    aliases: ['bl', 'b/l', 'bol', 'lading'],
    description: 'Transport document for ocean shipment',
    avgPages: 3,
    required: true,
  },
  [DOCUMENT_TYPE_VALUES.PACKING_LIST]: {
    value: DOCUMENT_TYPE_VALUES.PACKING_LIST,
    label: 'Packing List',
    shortLabel: 'PL',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '📦',
    aliases: ['packing', 'pack_list', 'plist', 'pl'],
    description: 'Detailed list of packed goods',
    avgPages: 3,
    required: true,
  },
  [DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN]: {
    value: DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN,
    label: 'Certificate of Origin',
    shortLabel: 'COO',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '🌍',
    aliases: ['coo', 'origin', 'origin_cert', 'co'],
    description: 'Certifies country of origin of goods',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE,
    label: 'Insurance Certificate',
    shortLabel: 'Ins. Cert',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '🛡️',
    aliases: ['insurance', 'ins_cert', 'insurance_cert', 'cargo_insurance', 'marine_insurance'],
    description: 'Proof of cargo insurance coverage',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.INSURANCE_POLICY]: {
    value: DOCUMENT_TYPE_VALUES.INSURANCE_POLICY,
    label: 'Insurance Policy',
    shortLabel: 'Policy',
    category: DOCUMENT_CATEGORIES.CORE,
    emoji: '📜',
    aliases: ['policy', 'ins_policy'],
    description: 'Full insurance policy document',
    avgPages: 8,
  },

  // =========================================================================
  // TRANSPORT DOCUMENTS
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.OCEAN_BILL_OF_LADING]: {
    value: DOCUMENT_TYPE_VALUES.OCEAN_BILL_OF_LADING,
    label: 'Ocean Bill of Lading',
    shortLabel: 'Ocean B/L',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🚢',
    aliases: ['ocean_bl', 'marine_bl', 'obl'],
    description: 'Bill of lading for ocean freight',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.SEA_WAYBILL]: {
    value: DOCUMENT_TYPE_VALUES.SEA_WAYBILL,
    label: 'Sea Waybill',
    shortLabel: 'SWB',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🌊',
    aliases: ['sea_waybill', 'swb', 'seawaybill'],
    description: 'Non-negotiable sea transport document',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.AIR_WAYBILL]: {
    value: DOCUMENT_TYPE_VALUES.AIR_WAYBILL,
    label: 'Air Waybill',
    shortLabel: 'AWB',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '✈️',
    aliases: ['awb', 'airwaybill', 'air_waybill', 'hawb', 'mawb'],
    description: 'Transport document for air freight',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.MULTIMODAL_TRANSPORT_DOCUMENT]: {
    value: DOCUMENT_TYPE_VALUES.MULTIMODAL_TRANSPORT_DOCUMENT,
    label: 'Multimodal Transport Document',
    shortLabel: 'MTD',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🚚',
    aliases: ['multimodal', 'mtd', 'combined_transport'],
    description: 'Document for multiple transport modes',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.RAILWAY_CONSIGNMENT_NOTE]: {
    value: DOCUMENT_TYPE_VALUES.RAILWAY_CONSIGNMENT_NOTE,
    label: 'Railway Consignment Note',
    shortLabel: 'Rail CN',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🚂',
    aliases: ['rail', 'railway', 'cim', 'smgs'],
    description: 'Transport document for rail freight',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.ROAD_TRANSPORT_DOCUMENT]: {
    value: DOCUMENT_TYPE_VALUES.ROAD_TRANSPORT_DOCUMENT,
    label: 'Road Transport Document',
    shortLabel: 'CMR',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🚛',
    aliases: ['cmr', 'road', 'trucking'],
    description: 'Transport document for road freight (CMR)',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.FORWARDER_CERTIFICATE_OF_RECEIPT]: {
    value: DOCUMENT_TYPE_VALUES.FORWARDER_CERTIFICATE_OF_RECEIPT,
    label: "Forwarder's Certificate of Receipt",
    shortLabel: 'FCR',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '📋',
    aliases: ['fcr', 'forwarder', 'freight_receipt'],
    description: 'Freight forwarder receipt document',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.HOUSE_BILL_OF_LADING]: {
    value: DOCUMENT_TYPE_VALUES.HOUSE_BILL_OF_LADING,
    label: 'House Bill of Lading',
    shortLabel: 'HBL',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🏠',
    aliases: ['hbl', 'house_bl'],
    description: 'B/L issued by freight forwarder',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.MASTER_BILL_OF_LADING]: {
    value: DOCUMENT_TYPE_VALUES.MASTER_BILL_OF_LADING,
    label: 'Master Bill of Lading',
    shortLabel: 'MBL',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '👑',
    aliases: ['mbl', 'master_bl'],
    description: 'B/L issued by shipping line',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.SHIPPING_COMPANY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.SHIPPING_COMPANY_CERTIFICATE,
    label: 'Shipping Company Certificate',
    shortLabel: 'Ship Cert',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '⚓',
    aliases: ['shipping_cert', 'carrier_cert'],
    description: 'Certificate from shipping company',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.MATES_RECEIPT]: {
    value: DOCUMENT_TYPE_VALUES.MATES_RECEIPT,
    label: "Mate's Receipt",
    shortLabel: 'MR',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '🧾',
    aliases: ['mates_receipt', 'mr', 'mate_receipt'],
    description: 'Receipt from ship\'s officer for cargo',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.DELIVERY_ORDER]: {
    value: DOCUMENT_TYPE_VALUES.DELIVERY_ORDER,
    label: 'Delivery Order',
    shortLabel: 'DO',
    category: DOCUMENT_CATEGORIES.TRANSPORT,
    emoji: '📬',
    aliases: ['do', 'delivery', 'release_order'],
    description: 'Order to release cargo',
    avgPages: 1,
  },

  // =========================================================================
  // INSPECTION & QUALITY CERTIFICATES
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.INSPECTION_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.INSPECTION_CERTIFICATE,
    label: 'Inspection Certificate',
    shortLabel: 'Insp Cert',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🔍',
    aliases: ['inspection', 'insp_cert', 'survey'],
    description: 'Third-party inspection certificate',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.PRE_SHIPMENT_INSPECTION]: {
    value: DOCUMENT_TYPE_VALUES.PRE_SHIPMENT_INSPECTION,
    label: 'Pre-Shipment Inspection',
    shortLabel: 'PSI',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '✅',
    aliases: ['psi', 'pre_shipment'],
    description: 'Inspection before shipment',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.QUALITY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.QUALITY_CERTIFICATE,
    label: 'Quality Certificate',
    shortLabel: 'QC',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '⭐',
    aliases: ['quality', 'qc', 'quality_cert'],
    description: 'Certificate of quality',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE,
    label: 'Weight Certificate',
    shortLabel: 'Wt Cert',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '⚖️',
    aliases: ['weight', 'weighment', 'weight_cert'],
    description: 'Certificate of weight',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.MEASUREMENT_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.MEASUREMENT_CERTIFICATE,
    label: 'Measurement Certificate',
    shortLabel: 'Meas Cert',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '📐',
    aliases: ['measurement', 'dimension'],
    description: 'Certificate of measurements/dimensions',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.ANALYSIS_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.ANALYSIS_CERTIFICATE,
    label: 'Analysis Certificate',
    shortLabel: 'Analysis',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🧪',
    aliases: ['analysis', 'chemical_analysis'],
    description: 'Chemical/composition analysis',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.LAB_TEST_REPORT]: {
    value: DOCUMENT_TYPE_VALUES.LAB_TEST_REPORT,
    label: 'Lab Test Report',
    shortLabel: 'Lab Test',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🔬',
    aliases: ['lab_test', 'lab_report', 'test_report'],
    description: 'Laboratory test results',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.SGS_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.SGS_CERTIFICATE,
    label: 'SGS Certificate',
    shortLabel: 'SGS',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🏅',
    aliases: ['sgs'],
    description: 'Certificate from SGS inspection',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.BUREAU_VERITAS_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.BUREAU_VERITAS_CERTIFICATE,
    label: 'Bureau Veritas Certificate',
    shortLabel: 'BV',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🏅',
    aliases: ['bureau_veritas', 'bv'],
    description: 'Certificate from Bureau Veritas',
    avgPages: 3,
  },
  [DOCUMENT_TYPE_VALUES.INTERTEK_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.INTERTEK_CERTIFICATE,
    label: 'Intertek Certificate',
    shortLabel: 'Intertek',
    category: DOCUMENT_CATEGORIES.INSPECTION,
    emoji: '🏅',
    aliases: ['intertek'],
    description: 'Certificate from Intertek',
    avgPages: 3,
  },

  // =========================================================================
  // HEALTH & AGRICULTURAL CERTIFICATES
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.PHYTOSANITARY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.PHYTOSANITARY_CERTIFICATE,
    label: 'Phytosanitary Certificate',
    shortLabel: 'Phyto',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '🌿',
    aliases: ['phyto', 'phytosanitary', 'plant_health'],
    description: 'Plant health certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.FUMIGATION_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.FUMIGATION_CERTIFICATE,
    label: 'Fumigation Certificate',
    shortLabel: 'Fumi',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '💨',
    aliases: ['fumigation', 'fumi', 'pest_control'],
    description: 'Proof of fumigation treatment',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.HEALTH_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.HEALTH_CERTIFICATE,
    label: 'Health Certificate',
    shortLabel: 'Health',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '❤️',
    aliases: ['health', 'health_cert'],
    description: 'General health certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.VETERINARY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.VETERINARY_CERTIFICATE,
    label: 'Veterinary Certificate',
    shortLabel: 'Vet',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '🐄',
    aliases: ['vet', 'veterinary', 'animal_health'],
    description: 'Animal health certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.SANITARY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.SANITARY_CERTIFICATE,
    label: 'Sanitary Certificate',
    shortLabel: 'Sanitary',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '🧼',
    aliases: ['sanitary', 'sanit'],
    description: 'Sanitary/hygiene certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.CITES_PERMIT]: {
    value: DOCUMENT_TYPE_VALUES.CITES_PERMIT,
    label: 'CITES Permit',
    shortLabel: 'CITES',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '🦁',
    aliases: ['cites'],
    description: 'Permit for endangered species trade',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.RADIATION_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.RADIATION_CERTIFICATE,
    label: 'Radiation Certificate',
    shortLabel: 'Radiation',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '☢️',
    aliases: ['radiation', 'non_radiation'],
    description: 'Radiation testing certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.HALAL_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.HALAL_CERTIFICATE,
    label: 'Halal Certificate',
    shortLabel: 'Halal',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '☪️',
    aliases: ['halal'],
    description: 'Halal certification',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.KOSHER_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.KOSHER_CERTIFICATE,
    label: 'Kosher Certificate',
    shortLabel: 'Kosher',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '✡️',
    aliases: ['kosher'],
    description: 'Kosher certification',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.ORGANIC_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.ORGANIC_CERTIFICATE,
    label: 'Organic Certificate',
    shortLabel: 'Organic',
    category: DOCUMENT_CATEGORIES.HEALTH,
    emoji: '🌱',
    aliases: ['organic'],
    description: 'Organic certification',
    avgPages: 2,
  },

  // =========================================================================
  // FINANCIAL DOCUMENTS
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.DRAFT_BILL_OF_EXCHANGE]: {
    value: DOCUMENT_TYPE_VALUES.DRAFT_BILL_OF_EXCHANGE,
    label: 'Draft/Bill of Exchange',
    shortLabel: 'Draft',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '💵',
    aliases: ['draft', 'boe', 'bill_of_exchange'],
    description: 'Payment draft or bill of exchange',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.PROMISSORY_NOTE]: {
    value: DOCUMENT_TYPE_VALUES.PROMISSORY_NOTE,
    label: 'Promissory Note',
    shortLabel: 'P/N',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '📝',
    aliases: ['promissory', 'pn'],
    description: 'Promise to pay document',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.BANK_GUARANTEE]: {
    value: DOCUMENT_TYPE_VALUES.BANK_GUARANTEE,
    label: 'Bank Guarantee',
    shortLabel: 'BG',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '🏦',
    aliases: ['bg', 'guarantee'],
    description: 'Bank guarantee document',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.STANDBY_LC]: {
    value: DOCUMENT_TYPE_VALUES.STANDBY_LC,
    label: 'Standby Letter of Credit',
    shortLabel: 'SBLC',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '🔒',
    aliases: ['sblc', 'standby'],
    description: 'Standby LC document',
    avgPages: 4,
  },
  [DOCUMENT_TYPE_VALUES.PAYMENT_RECEIPT]: {
    value: DOCUMENT_TYPE_VALUES.PAYMENT_RECEIPT,
    label: 'Payment Receipt',
    shortLabel: 'Receipt',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '🧾',
    aliases: ['receipt', 'payment'],
    description: 'Proof of payment',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.DEBIT_NOTE]: {
    value: DOCUMENT_TYPE_VALUES.DEBIT_NOTE,
    label: 'Debit Note',
    shortLabel: 'DN',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '➖',
    aliases: ['debit', 'dn'],
    description: 'Debit note document',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.CREDIT_NOTE]: {
    value: DOCUMENT_TYPE_VALUES.CREDIT_NOTE,
    label: 'Credit Note',
    shortLabel: 'CN',
    category: DOCUMENT_CATEGORIES.FINANCIAL,
    emoji: '➕',
    aliases: ['credit', 'cn'],
    description: 'Credit note document',
    avgPages: 1,
  },

  // =========================================================================
  // BENEFICIARY & ATTESTATION
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE,
    label: 'Beneficiary Certificate',
    shortLabel: 'Benef Cert',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '✍️',
    aliases: ['beneficiary', 'benef_cert', 'attestation'],
    description: 'Certificate signed by beneficiary',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.MANUFACTURER_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.MANUFACTURER_CERTIFICATE,
    label: "Manufacturer's Certificate",
    shortLabel: 'Mfr Cert',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '🏭',
    aliases: ['manufacturer', 'mfr_cert'],
    description: 'Certificate from manufacturer',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.CONFORMITY_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.CONFORMITY_CERTIFICATE,
    label: 'Certificate of Conformity',
    shortLabel: 'COC',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '✓',
    aliases: ['conformity', 'coc', 'compliance'],
    description: 'Certificate of compliance/conformity',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.NON_MANIPULATION_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.NON_MANIPULATION_CERTIFICATE,
    label: 'Non-Manipulation Certificate',
    shortLabel: 'Non-Manip',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '🔐',
    aliases: ['non_manipulation', 'transhipment'],
    description: 'Certificate of non-manipulation',
    avgPages: 1,
  },

  // =========================================================================
  // CUSTOMS & TRADE COMPLIANCE
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.CUSTOMS_DECLARATION]: {
    value: DOCUMENT_TYPE_VALUES.CUSTOMS_DECLARATION,
    label: 'Customs Declaration',
    shortLabel: 'Customs',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '🛃',
    aliases: ['customs', 'declaration', 'customs_form'],
    description: 'Customs clearance document',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.EXPORT_LICENSE]: {
    value: DOCUMENT_TYPE_VALUES.EXPORT_LICENSE,
    label: 'Export License',
    shortLabel: 'Exp Lic',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '📤',
    aliases: ['export_license', 'export_permit'],
    description: 'License to export goods',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.IMPORT_LICENSE]: {
    value: DOCUMENT_TYPE_VALUES.IMPORT_LICENSE,
    label: 'Import License',
    shortLabel: 'Imp Lic',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '📥',
    aliases: ['import_license', 'import_permit'],
    description: 'License to import goods',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.GSP_FORM_A]: {
    value: DOCUMENT_TYPE_VALUES.GSP_FORM_A,
    label: 'GSP Form A',
    shortLabel: 'Form A',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '📃',
    aliases: ['gsp', 'form_a', 'preference'],
    description: 'Generalized System of Preferences form',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.EUR1_MOVEMENT_CERTIFICATE]: {
    value: DOCUMENT_TYPE_VALUES.EUR1_MOVEMENT_CERTIFICATE,
    label: 'EUR.1 Movement Certificate',
    shortLabel: 'EUR.1',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '🇪🇺',
    aliases: ['eur1', 'eur.1', 'movement_cert'],
    description: 'EU preferential origin certificate',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.WAREHOUSE_RECEIPT]: {
    value: DOCUMENT_TYPE_VALUES.WAREHOUSE_RECEIPT,
    label: 'Warehouse Receipt',
    shortLabel: 'WR',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '🏢',
    aliases: ['warehouse', 'wr', 'storage'],
    description: 'Receipt for goods in warehouse',
    avgPages: 1,
  },
  [DOCUMENT_TYPE_VALUES.CARGO_MANIFEST]: {
    value: DOCUMENT_TYPE_VALUES.CARGO_MANIFEST,
    label: 'Cargo Manifest',
    shortLabel: 'Manifest',
    category: DOCUMENT_CATEGORIES.CUSTOMS,
    emoji: '📋',
    aliases: ['manifest', 'cargo_list'],
    description: 'List of all cargo on vessel',
    avgPages: 3,
  },

  // =========================================================================
  // OTHER / SUPPORTING
  // =========================================================================
  [DOCUMENT_TYPE_VALUES.SUPPORTING_DOCUMENT]: {
    value: DOCUMENT_TYPE_VALUES.SUPPORTING_DOCUMENT,
    label: 'Supporting Document',
    shortLabel: 'Support',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '📎',
    aliases: ['supporting', 'supplementary', 'attachment'],
    description: 'Additional supporting document',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.OTHER]: {
    value: DOCUMENT_TYPE_VALUES.OTHER,
    label: 'Other Document',
    shortLabel: 'Other',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '📄',
    aliases: ['other', 'misc', 'miscellaneous'],
    description: 'Other document type',
    avgPages: 2,
  },
  [DOCUMENT_TYPE_VALUES.UNKNOWN]: {
    value: DOCUMENT_TYPE_VALUES.UNKNOWN,
    label: 'Unknown',
    shortLabel: '?',
    category: DOCUMENT_CATEGORIES.OTHER,
    emoji: '❓',
    aliases: ['unknown'],
    description: 'Document type not identified',
    avgPages: 2,
  },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Normalize any document type value to the canonical form
 * Handles aliases, legacy values, and case variations
 */
export function normalizeDocumentType(input: string): DocumentTypeValue {
  if (!input) return DOCUMENT_TYPE_VALUES.UNKNOWN;
  
  const normalized = input.toLowerCase().trim();
  
  // Direct match
  if (normalized in DOCUMENT_TYPES) {
    return normalized as DocumentTypeValue;
  }
  
  // Check aliases
  for (const [key, info] of Object.entries(DOCUMENT_TYPES)) {
    if (info.aliases.includes(normalized)) {
      return key as DocumentTypeValue;
    }
  }
  
  // Fuzzy match on common patterns
  if (normalized.includes('lc') || normalized.includes('credit')) {
    return DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT;
  }
  if (normalized.includes('invoice') || normalized.includes('inv')) {
    return DOCUMENT_TYPE_VALUES.COMMERCIAL_INVOICE;
  }
  if (normalized.includes('lading') || normalized === 'bl' || normalized === 'bol') {
    return DOCUMENT_TYPE_VALUES.BILL_OF_LADING;
  }
  if (normalized.includes('packing')) {
    return DOCUMENT_TYPE_VALUES.PACKING_LIST;
  }
  if (normalized.includes('origin') || normalized === 'coo') {
    return DOCUMENT_TYPE_VALUES.CERTIFICATE_OF_ORIGIN;
  }
  if (normalized.includes('insurance')) {
    return DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE;
  }
  
  return DOCUMENT_TYPE_VALUES.UNKNOWN;
}

/**
 * Get document type info by value or alias
 */
export function getDocumentTypeInfo(typeValue: string): DocumentTypeInfo | undefined {
  const normalized = normalizeDocumentType(typeValue);
  return DOCUMENT_TYPES[normalized];
}

/**
 * Get documents by category for grouped UI display
 */
export function getDocumentsByCategory(): Record<DocumentCategory, DocumentTypeInfo[]> {
  const grouped: Record<DocumentCategory, DocumentTypeInfo[]> = {
    [DOCUMENT_CATEGORIES.CORE]: [],
    [DOCUMENT_CATEGORIES.TRANSPORT]: [],
    [DOCUMENT_CATEGORIES.INSPECTION]: [],
    [DOCUMENT_CATEGORIES.HEALTH]: [],
    [DOCUMENT_CATEGORIES.FINANCIAL]: [],
    [DOCUMENT_CATEGORIES.CUSTOMS]: [],
    [DOCUMENT_CATEGORIES.OTHER]: [],
  };
  
  for (const info of Object.values(DOCUMENT_TYPES)) {
    grouped[info.category].push(info);
  }
  
  return grouped;
}

/**
 * Get dropdown options for UI (value + label pairs)
 */
export function getDocumentTypeOptions(): Array<{ value: DocumentTypeValue; label: string; category: DocumentCategory }> {
  return Object.values(DOCUMENT_TYPES)
    .filter(info => info.value !== DOCUMENT_TYPE_VALUES.UNKNOWN) // Don't show unknown in dropdown
    .map(info => ({
      value: info.value,
      label: info.label,
      category: info.category,
    }));
}

/**
 * Get required document types for typical export LC
 */
export function getRequiredDocumentTypes(): DocumentTypeValue[] {
  return Object.entries(DOCUMENT_TYPES)
    .filter(([_, info]) => info.required)
    .map(([key]) => key as DocumentTypeValue);
}

/**
 * Check if a document type is a transport document
 */
export function isTransportDocument(typeValue: string): boolean {
  const info = getDocumentTypeInfo(typeValue);
  return info?.category === DOCUMENT_CATEGORIES.TRANSPORT;
}

/**
 * Check if a document type is LC-related
 */
export function isLCDocument(typeValue: string): boolean {
  const normalized = normalizeDocumentType(typeValue);
  return [
    DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT,
    DOCUMENT_TYPE_VALUES.SWIFT_MESSAGE,
    DOCUMENT_TYPE_VALUES.LC_APPLICATION,
    DOCUMENT_TYPE_VALUES.STANDBY_LC,
  ].includes(normalized);
}
