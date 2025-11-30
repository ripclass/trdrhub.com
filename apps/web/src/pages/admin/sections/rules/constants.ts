export type RulebookType = "base" | "supplement" | "general";

export interface RulebookOption {
  value: string;
  label: string;
  type: RulebookType;
  domain: string;
}

export const PRIMARY_DOMAIN_OPTIONS: { value: string; label: string }[] = [
  // Core Standards
  { value: "icc", label: "ICC (International Chamber of Commerce)" },
  { value: "swift", label: "SWIFT (Messaging Standards)" },
  { value: "iso20022", label: "ISO 20022 (Financial Messaging)" },
  
  // Trade Agreements
  { value: "fta", label: "FTA (Free Trade Agreements)" },
  
  // Compliance & Screening
  { value: "sanctions", label: "Sanctions" },
  { value: "export_control", label: "Export Control" },
  
  // Commodities
  { value: "commodity", label: "Commodity (Sector-Specific Rules)" },
  
  // Bank Profiles
  { value: "bank", label: "Bank (Bank Profiles & Preferences)" },
  
  // Country Regulations
  { value: "regulations", label: "Regulations (Country-Specific)" },
  
  // Legal Frameworks
  { value: "law", label: "Law (Legal Frameworks)" },
  { value: "mode", label: "Mode (Jurisdiction Modes)" },
];

export const RULEBOOK_OPTIONS_BY_DOMAIN: Record<string, RulebookOption[]> = {
  // ═══════════════════════════════════════════════════════════════════
  // ICC - International Chamber of Commerce
  // ═══════════════════════════════════════════════════════════════════
  icc: [
    // Documentary Credits (LC)
    { value: "icc.ucp600", label: "UCP 600 (Commercial Documentary Credits)", type: "base", domain: "icc" },
    { value: "icc.isbp745", label: "ISBP 745 (Standard Banking Practice)", type: "supplement", domain: "icc" },
    { value: "icc.eucp", label: "eUCP v2.1 (Electronic Supplement to UCP)", type: "supplement", domain: "icc" },
    
    // Standby & Guarantees
    { value: "icc.isp98", label: "ISP98 (International Standby Practices)", type: "base", domain: "icc" },
    { value: "icc.urdg758", label: "URDG 758 (Demand Guarantees)", type: "base", domain: "icc" },
    
    // Collections
    { value: "icc.urc522", label: "URC 522 (Collections)", type: "base", domain: "icc" },
    { value: "icc.eurc", label: "eURC v1.1 (Electronic Supplement to URC)", type: "supplement", domain: "icc" },
    
    // Bank-to-Bank
    { value: "icc.urr725", label: "URR 725 (Bank-to-Bank Reimbursements)", type: "supplement", domain: "icc" },
    { value: "icc.urbpo750", label: "URBPO 750 (Bank Payment Obligation)", type: "base", domain: "icc" },
    
    // Forfaiting
    { value: "icc.urf800", label: "URF 800 (Forfaiting)", type: "base", domain: "icc" },
    
    // Digital Trade
    { value: "icc.urdtt", label: "URDTT (Digital Trade Transactions)", type: "base", domain: "icc" },
    
    // Incoterms
    { value: "icc.incoterms2020", label: "Incoterms 2020", type: "base", domain: "icc" },
    { value: "icc.incoterms", label: "Incoterms (General)", type: "base", domain: "icc" },
    
    // Opinions & DOCDEX
    { value: "icc.opinions", label: "ICC Banking Commission Opinions", type: "general", domain: "icc" },
    { value: "icc.docdex", label: "ICC DOCDEX Decisions", type: "general", domain: "icc" },
    
    // Cross-Document Rules
    { value: "icc.lcopilot.crossdoc", label: "LCopilot Cross-Document Rules", type: "general", domain: "icc" },
    
    // Legacy
    { value: "icc", label: "ICC (General / Legacy)", type: "general", domain: "icc" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // SWIFT - Messaging Standards
  // ═══════════════════════════════════════════════════════════════════
  swift: [
    // Documentary Credits
    { value: "swift.mt700", label: "MT700 (Issue of Documentary Credit)", type: "base", domain: "swift" },
    { value: "swift.mt707", label: "MT707 (Amendment to Documentary Credit)", type: "base", domain: "swift" },
    
    // Guarantees
    { value: "swift.mt760", label: "MT760 (Guarantee/Standby LC)", type: "base", domain: "swift" },
    { value: "swift.mt767", label: "MT767 (Guarantee Amendment)", type: "base", domain: "swift" },
    { value: "swift.mt768", label: "MT768 (Guarantee Acknowledgement)", type: "base", domain: "swift" },
    
    // Collections
    { value: "swift.mt400", label: "MT400 (Advice of Payment)", type: "base", domain: "swift" },
    { value: "swift.mt410", label: "MT410 (Acknowledgement)", type: "base", domain: "swift" },
    { value: "swift.mt412", label: "MT412 (Advice of Acceptance)", type: "base", domain: "swift" },
    { value: "swift.mt416", label: "MT416 (Advice of Non-Payment)", type: "base", domain: "swift" },
    { value: "swift.mt420", label: "MT420 (Tracer)", type: "base", domain: "swift" },
    { value: "swift.mt422", label: "MT422 (Advice of Fate)", type: "base", domain: "swift" },
    { value: "swift.mt430", label: "MT430 (Amendment of Instructions)", type: "base", domain: "swift" },
    
    // General
    { value: "swift", label: "SWIFT (General)", type: "general", domain: "swift" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // ISO 20022 - Financial Messaging
  // ═══════════════════════════════════════════════════════════════════
  iso20022: [
    { value: "iso20022.trade", label: "ISO 20022 Trade (trad.001/002/003)", type: "base", domain: "iso20022" },
    { value: "iso20022.tsrv", label: "ISO 20022 Trade Services (Undertakings)", type: "base", domain: "iso20022" },
    { value: "iso20022.tsmt", label: "ISO 20022 TSMT (BPO)", type: "base", domain: "iso20022" },
    { value: "iso20022", label: "ISO 20022 (General)", type: "general", domain: "iso20022" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // FTA - Free Trade Agreements
  // ═══════════════════════════════════════════════════════════════════
  fta: [
    // Major Regional Agreements
    { value: "fta.rcep", label: "RCEP (Regional Comprehensive Economic Partnership)", type: "base", domain: "fta" },
    { value: "fta.cptpp", label: "CPTPP (Trans-Pacific Partnership)", type: "base", domain: "fta" },
    { value: "fta.usmca", label: "USMCA (US-Mexico-Canada)", type: "base", domain: "fta" },
    { value: "fta.afcfta", label: "AfCFTA (African Continental FTA)", type: "base", domain: "fta" },
    
    // EU Agreements
    { value: "fta.eu_uk", label: "EU-UK TCA (Trade and Cooperation)", type: "base", domain: "fta" },
    { value: "fta.eu_japan", label: "EU-Japan EPA", type: "base", domain: "fta" },
    { value: "fta.eu_korea", label: "EU-Korea FTA", type: "base", domain: "fta" },
    { value: "fta.ceta", label: "CETA (EU-Canada)", type: "base", domain: "fta" },
    { value: "fta.eusfta", label: "EU-Singapore FTA", type: "base", domain: "fta" },
    { value: "fta.evfta", label: "EU-Vietnam FTA", type: "base", domain: "fta" },
    { value: "fta.eu_mexico", label: "EU-Mexico FTA", type: "base", domain: "fta" },
    { value: "fta.pem", label: "PEM Convention (Pan-Euro-Med)", type: "base", domain: "fta" },
    
    // US Bilateral
    { value: "fta.korus", label: "KORUS (US-Korea FTA)", type: "base", domain: "fta" },
    { value: "fta.us_israel", label: "US-Israel FTA", type: "base", domain: "fta" },
    { value: "fta.uschile", label: "US-Chile FTA", type: "base", domain: "fta" },
    { value: "fta.uspanama", label: "US-Panama TPA", type: "base", domain: "fta" },
    { value: "fta.ussfta", label: "US-Singapore FTA", type: "base", domain: "fta" },
    { value: "fta.ausfta", label: "Australia-US FTA", type: "base", domain: "fta" },
    { value: "fta.ctpa", label: "US-Colombia TPA", type: "base", domain: "fta" },
    { value: "fta.ptpa", label: "US-Peru TPA", type: "base", domain: "fta" },
    
    // Asian Agreements
    { value: "fta.acfta", label: "ACFTA (ASEAN-China FTA)", type: "base", domain: "fta" },
    { value: "fta.asean", label: "ASEAN FTA", type: "base", domain: "fta" },
    
    // Regional Blocs
    { value: "fta.mercosur", label: "Mercosur (South America)", type: "base", domain: "fta" },
    { value: "fta.efta", label: "EFTA (European Free Trade)", type: "base", domain: "fta" },
    { value: "fta.gcc", label: "GCC (Gulf Cooperation Council)", type: "base", domain: "fta" },
    { value: "fta.sadc", label: "SADC (Southern African)", type: "base", domain: "fta" },
    { value: "fta.comesa", label: "COMESA (Eastern/Southern Africa)", type: "base", domain: "fta" },
    { value: "fta.ecowas", label: "ECOWAS (West Africa)", type: "base", domain: "fta" },
    { value: "fta.eaeu", label: "EAEU (Eurasian Economic Union)", type: "base", domain: "fta" },
    { value: "fta.pacific_alliance", label: "Pacific Alliance", type: "base", domain: "fta" },
    
    // Collection Rulebooks (multiple FTAs in one file)
    { value: "fta.eu_bilateral", label: "EU Bilateral FTAs (Collection)", type: "general", domain: "fta" },
    { value: "fta.us_bilateral", label: "US Bilateral FTAs (Collection)", type: "general", domain: "fta" },
    { value: "fta.regional", label: "Regional Blocs (Collection)", type: "general", domain: "fta" },
    
    // General
    { value: "fta", label: "FTA (General)", type: "general", domain: "fta" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // SANCTIONS - Sanctions Screening
  // ═══════════════════════════════════════════════════════════════════
  sanctions: [
    // Primary Lists
    { value: "sanctions.ofac", label: "OFAC (US Treasury)", type: "base", domain: "sanctions" },
    { value: "sanctions.ofac.us", label: "OFAC US-Specific", type: "base", domain: "sanctions" },
    { value: "sanctions.eu", label: "EU Consolidated Sanctions", type: "base", domain: "sanctions" },
    { value: "sanctions.un", label: "UN Security Council Sanctions", type: "base", domain: "sanctions" },
    { value: "sanctions.uk", label: "UK OFSI Sanctions", type: "base", domain: "sanctions" },
    
    // Maritime & Vessels
    { value: "sanctions.vessel", label: "Vessel/Maritime Sanctions", type: "base", domain: "sanctions" },
    { value: "sanctions.port", label: "Port Restrictions", type: "base", domain: "sanctions" },
    
    // Country-Specific
    { value: "sanctions.cn", label: "China Sanctions/Unreliable Entity", type: "base", domain: "sanctions" },
    { value: "sanctions.ae", label: "UAE Sanctions", type: "base", domain: "sanctions" },
    { value: "sanctions.swiss", label: "Swiss SECO Sanctions", type: "base", domain: "sanctions" },
    
    // General
    { value: "sanctions.global", label: "Global Sanctions (Combined)", type: "general", domain: "sanctions" },
    { value: "sanctions.checklist", label: "Sanctions Checklist", type: "general", domain: "sanctions" },
    { value: "sanctions", label: "Sanctions (General)", type: "general", domain: "sanctions" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // EXPORT CONTROL - Export Controls & Dual-Use
  // ═══════════════════════════════════════════════════════════════════
  export_control: [
    { value: "export_control.us", label: "US EAR (Export Administration)", type: "base", domain: "export_control" },
    { value: "export_control.eu", label: "EU Dual-Use Regulation", type: "base", domain: "export_control" },
    { value: "export_control", label: "Export Control (General)", type: "general", domain: "export_control" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // COMMODITY - Sector-Specific Rules
  // ═══════════════════════════════════════════════════════════════════
  commodity: [
    { value: "commodity.agriculture", label: "Agriculture & Food Products", type: "base", domain: "commodity" },
    { value: "commodity.textiles", label: "Textiles & Garments", type: "base", domain: "commodity" },
    { value: "commodity.chemicals", label: "Chemicals & Hazmat", type: "base", domain: "commodity" },
    { value: "commodity.electronics", label: "Electronics & Technology", type: "base", domain: "commodity" },
    { value: "commodity.energy", label: "Energy & Fuels", type: "base", domain: "commodity" },
    { value: "commodity.mining", label: "Mining & Minerals", type: "base", domain: "commodity" },
    { value: "commodity.automotive", label: "Automotive & Vehicles", type: "base", domain: "commodity" },
    { value: "commodity.pharma", label: "Pharmaceuticals & Medical", type: "base", domain: "commodity" },
    { value: "commodity.food", label: "Food & Beverages", type: "base", domain: "commodity" },
    { value: "commodity.beverage", label: "Beverages (Alcohol/Non-Alcohol)", type: "base", domain: "commodity" },
    { value: "commodity.machinery", label: "Machinery & Equipment", type: "base", domain: "commodity" },
    { value: "commodity.precious_metals", label: "Precious Metals & Gems", type: "base", domain: "commodity" },
    { value: "commodity.timber", label: "Timber & Wood Products", type: "base", domain: "commodity" },
    { value: "commodity.seafood", label: "Seafood & Marine", type: "base", domain: "commodity" },
    { value: "commodity", label: "Commodity (General)", type: "general", domain: "commodity" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // BANK - Bank Profiles & Preferences
  // ═══════════════════════════════════════════════════════════════════
  bank: [
    // Global Banks
    { value: "bank.hsbc", label: "HSBC", type: "base", domain: "bank" },
    { value: "bank.citi", label: "Citibank", type: "base", domain: "bank" },
    { value: "bank.citi.us", label: "Citibank US", type: "base", domain: "bank" },
    { value: "bank.jpmorgan", label: "JP Morgan", type: "base", domain: "bank" },
    { value: "bank.jpmorgan.us", label: "JP Morgan US", type: "base", domain: "bank" },
    { value: "bank.scb", label: "Standard Chartered", type: "base", domain: "bank" },
    { value: "bank.deutsche", label: "Deutsche Bank", type: "base", domain: "bank" },
    { value: "bank.bnp", label: "BNP Paribas", type: "base", domain: "bank" },
    { value: "bank.socgen", label: "Société Générale", type: "base", domain: "bank" },
    { value: "bank.bofa", label: "Bank of America", type: "base", domain: "bank" },
    { value: "bank.bofa.us", label: "Bank of America US", type: "base", domain: "bank" },
    { value: "bank.wellsfargo", label: "Wells Fargo", type: "base", domain: "bank" },
    { value: "bank.wellsfargo.us", label: "Wells Fargo US", type: "base", domain: "bank" },
    
    // Asian Banks
    { value: "bank.icbc", label: "ICBC (China)", type: "base", domain: "bank" },
    { value: "bank.boc", label: "Bank of China", type: "base", domain: "bank" },
    { value: "bank.mufg", label: "MUFG (Japan)", type: "base", domain: "bank" },
    { value: "bank.smbc", label: "SMBC (Japan)", type: "base", domain: "bank" },
    { value: "bank.mizuho", label: "Mizuho (Japan)", type: "base", domain: "bank" },
    { value: "bank.dbs", label: "DBS (Singapore)", type: "base", domain: "bank" },
    { value: "bank.uob", label: "UOB (Singapore)", type: "base", domain: "bank" },
    { value: "bank.kookmin", label: "Kookmin (Korea)", type: "base", domain: "bank" },
    { value: "bank.shinhan", label: "Shinhan (Korea)", type: "base", domain: "bank" },
    
    // European Banks
    { value: "bank.ing", label: "ING", type: "base", domain: "bank" },
    { value: "bank.rabobank", label: "Rabobank", type: "base", domain: "bank" },
    { value: "bank.commerzbank", label: "Commerzbank", type: "base", domain: "bank" },
    { value: "bank.unicredit", label: "UniCredit", type: "base", domain: "bank" },
    { value: "bank.de", label: "German Banks (General)", type: "base", domain: "bank" },
    
    // Australian Banks
    { value: "bank.nab", label: "NAB (Australia)", type: "base", domain: "bank" },
    { value: "bank.anz", label: "ANZ (Australia)", type: "base", domain: "bank" },
    
    // Middle East Banks
    { value: "bank.emiratesnbd", label: "Emirates NBD", type: "base", domain: "bank" },
    { value: "bank.mashreq", label: "Mashreq Bank", type: "base", domain: "bank" },
    { value: "bank.nbk", label: "National Bank of Kuwait", type: "base", domain: "bank" },
    { value: "bank.qnb", label: "Qatar National Bank", type: "base", domain: "bank" },
    { value: "bank.snb", label: "Saudi National Bank", type: "base", domain: "bank" },
    
    // Africa/LatAm Banks
    { value: "bank.standardbank", label: "Standard Bank (Africa)", type: "base", domain: "bank" },
    { value: "bank.itau", label: "Itaú (Brazil)", type: "base", domain: "bank" },
    
    // Regional Profiles
    { value: "bank.china", label: "China Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.india", label: "India Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.canada", label: "Canada Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.europe", label: "Europe Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.asean", label: "ASEAN Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.latam", label: "Latin America Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.mena", label: "MENA Banks (Regional)", type: "general", domain: "bank" },
    { value: "bank.islamic", label: "Islamic Finance Banks", type: "general", domain: "bank" },
    
    // General
    { value: "bank", label: "Bank (General)", type: "general", domain: "bank" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // REGULATIONS - Country-Specific Regulations
  // ═══════════════════════════════════════════════════════════════════
  regulations: [
    // Asia-Pacific
    { value: "regulations.cn", label: "China (SAFE, GACC, PBOC)", type: "base", domain: "regulations" },
    { value: "regulations.in", label: "India (RBI, FEMA)", type: "base", domain: "regulations" },
    { value: "regulations.bd", label: "Bangladesh (BB, LCAF)", type: "base", domain: "regulations" },
    { value: "regulations.sg", label: "Singapore (MAS, ETA)", type: "base", domain: "regulations" },
    { value: "regulations.jp", label: "Japan (METI, NACCS)", type: "base", domain: "regulations" },
    { value: "regulations.kr", label: "South Korea (KITA)", type: "base", domain: "regulations" },
    { value: "regulations.vn", label: "Vietnam (SBV)", type: "base", domain: "regulations" },
    { value: "regulations.th", label: "Thailand (BOT)", type: "base", domain: "regulations" },
    { value: "regulations.my", label: "Malaysia (BNM)", type: "base", domain: "regulations" },
    { value: "regulations.ph", label: "Philippines (BSP)", type: "base", domain: "regulations" },
    { value: "regulations.id", label: "Indonesia (BI)", type: "base", domain: "regulations" },
    { value: "regulations.tw", label: "Taiwan (CBC)", type: "base", domain: "regulations" },
    { value: "regulations.hk", label: "Hong Kong (HKMA)", type: "base", domain: "regulations" },
    { value: "regulations.au", label: "Australia (ABF)", type: "base", domain: "regulations" },
    { value: "regulations.nz", label: "New Zealand (RBNZ)", type: "base", domain: "regulations" },
    { value: "regulations.kh", label: "Cambodia (NBC)", type: "base", domain: "regulations" },
    { value: "regulations.pk", label: "Pakistan (SBP)", type: "base", domain: "regulations" },
    
    // Europe
    { value: "regulations.eu", label: "European Union (UCC)", type: "base", domain: "regulations" },
    { value: "regulations.uk", label: "United Kingdom (ETDA)", type: "base", domain: "regulations" },
    { value: "regulations.de", label: "Germany (BAFA)", type: "base", domain: "regulations" },
    { value: "regulations.nl", label: "Netherlands", type: "base", domain: "regulations" },
    
    // Middle East & Africa
    { value: "regulations.ae", label: "UAE (CBUAE)", type: "base", domain: "regulations" },
    { value: "regulations.sa", label: "Saudi Arabia (ZATCA)", type: "base", domain: "regulations" },
    { value: "regulations.eg", label: "Egypt (CBE)", type: "base", domain: "regulations" },
    { value: "regulations.qa", label: "Qatar (QCB)", type: "base", domain: "regulations" },
    { value: "regulations.kw", label: "Kuwait (CBK)", type: "base", domain: "regulations" },
    { value: "regulations.bh", label: "Bahrain (CBB)", type: "base", domain: "regulations" },
    { value: "regulations.om", label: "Oman (CBO)", type: "base", domain: "regulations" },
    { value: "regulations.jo", label: "Jordan (CBJ)", type: "base", domain: "regulations" },
    { value: "regulations.ma", label: "Morocco (BAM)", type: "base", domain: "regulations" },
    { value: "regulations.za", label: "South Africa (SARB)", type: "base", domain: "regulations" },
    { value: "regulations.ng", label: "Nigeria (CBN)", type: "base", domain: "regulations" },
    { value: "regulations.ke", label: "Kenya (CBK)", type: "base", domain: "regulations" },
    { value: "regulations.gh", label: "Ghana (BOG)", type: "base", domain: "regulations" },
    { value: "regulations.kz", label: "Kazakhstan (NBK)", type: "base", domain: "regulations" },
    
    // Americas
    { value: "regulations.us", label: "United States", type: "base", domain: "regulations" },
    { value: "regulations.mx", label: "Mexico (SAT)", type: "base", domain: "regulations" },
    { value: "regulations.br", label: "Brazil (BCB)", type: "base", domain: "regulations" },
    { value: "regulations.ar", label: "Argentina (BCRA)", type: "base", domain: "regulations" },
    { value: "regulations.cl", label: "Chile", type: "base", domain: "regulations" },
    { value: "regulations.co", label: "Colombia (BanRep)", type: "base", domain: "regulations" },
    { value: "regulations.pe", label: "Peru (BCRP)", type: "base", domain: "regulations" },
    { value: "regulations.pa", label: "Panama", type: "base", domain: "regulations" },
    { value: "regulations.lk", label: "Sri Lanka (CBSL)", type: "base", domain: "regulations" },
    
    // Turkey
    { value: "regulations.tr", label: "Turkey (CBRT)", type: "base", domain: "regulations" },
    
    // General
    { value: "regulations", label: "Regulations (General)", type: "general", domain: "regulations" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // LAW - Legal Frameworks
  // ═══════════════════════════════════════════════════════════════════
  law: [
    { value: "law.ucc.us", label: "US Uniform Commercial Code (UCC)", type: "base", domain: "law" },
    { value: "law", label: "Law (General)", type: "general", domain: "law" },
  ],

  // ═══════════════════════════════════════════════════════════════════
  // MODE - Jurisdiction Modes
  // ═══════════════════════════════════════════════════════════════════
  mode: [
    { value: "mode.us", label: "US Mode (ISP98 + UCC)", type: "base", domain: "mode" },
    { value: "mode", label: "Mode (General)", type: "general", domain: "mode" },
  ],
};

export const ALL_RULEBOOK_OPTIONS: RulebookOption[] = Object.values(RULEBOOK_OPTIONS_BY_DOMAIN).flat();
