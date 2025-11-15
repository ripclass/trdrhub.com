export type RulebookType = "base" | "supplement" | "general";

export interface RulebookOption {
  value: string;
  label: string;
  type: RulebookType;
  domain: string;
}

export const PRIMARY_DOMAIN_OPTIONS: { value: string; label: string }[] = [
  { value: "icc", label: "ICC (International Chamber of Commerce)" },
  { value: "incoterms", label: "Incoterms" },
  { value: "vat", label: "VAT" },
  { value: "sanctions", label: "Sanctions" },
  { value: "aml", label: "AML (Anti-Money Laundering)" },
  { value: "customs", label: "Customs" },
  { value: "shipping", label: "Shipping" },
  { value: "regulations", label: "Regulations" },
];

export const RULEBOOK_OPTIONS_BY_DOMAIN: Record<string, RulebookOption[]> = {
  icc: [
    { value: "icc.ucp600", label: "UCP 600 (Commercial Documentary Credits)", type: "base", domain: "icc" },
    { value: "icc.eucp2.1", label: "eUCP v2.1 (Electronic Supplement to UCP)", type: "supplement", domain: "icc" },
    { value: "icc.isp98", label: "ISP98 (International Standby Practices)", type: "base", domain: "icc" },
    { value: "icc.urdg758", label: "URDG 758 (Demand Guarantees)", type: "base", domain: "icc" },
    { value: "icc.urc522", label: "URC 522 (Collections)", type: "base", domain: "icc" },
    { value: "icc.eurc1.0", label: "eURC 1.0 (Electronic Supplement to URC)", type: "supplement", domain: "icc" },
    { value: "icc.urr725", label: "URR 725 (Reimbursement Undertakings)", type: "supplement", domain: "icc" },
    { value: "icc.lcopilot.crossdoc", label: "LCOPILOT Cross-Document Rules", type: "general", domain: "icc" },
    { value: "icc", label: "ICC (General / Legacy)", type: "general", domain: "icc" },
  ],
  incoterms: [
    { value: "incoterms.2020", label: "Incoterms 2020", type: "base", domain: "incoterms" },
    { value: "incoterms.2010", label: "Incoterms 2010", type: "base", domain: "incoterms" },
  ],
  vat: [
    { value: "vat.eu", label: "EU VAT Directives", type: "base", domain: "vat" },
    { value: "vat.uk", label: "UK VAT Guidance", type: "base", domain: "vat" },
    { value: "vat.us", label: "US Sales Tax", type: "base", domain: "vat" },
  ],
  sanctions: [
    { value: "sanctions.ofac", label: "OFAC Sanctions", type: "base", domain: "sanctions" },
    { value: "sanctions.eu", label: "EU Consolidated Sanctions", type: "base", domain: "sanctions" },
  ],
  aml: [
    { value: "aml.fatf", label: "FATF Recommendations", type: "base", domain: "aml" },
    { value: "aml.local", label: "Local AML Policies", type: "base", domain: "aml" },
  ],
  customs: [
    { value: "customs.wco", label: "WCO Customs Guidelines", type: "base", domain: "customs" },
    { value: "customs.local", label: "Local Customs Regulations", type: "base", domain: "customs" },
  ],
  shipping: [
    { value: "shipping.imdg", label: "IMDG Code", type: "base", domain: "shipping" },
    { value: "shipping.solas", label: "SOLAS", type: "base", domain: "shipping" },
  ],
  regulations: [
    { value: "regulations.eu", label: "EU Trade Regulations", type: "base", domain: "regulations" },
    { value: "regulations.us", label: "US Trade Regulations", type: "base", domain: "regulations" },
    { value: "regulations.bd", label: "Bangladesh Central Bank", type: "base", domain: "regulations" },
  ],
};

export const ALL_RULEBOOK_OPTIONS: RulebookOption[] = Object.values(RULEBOOK_OPTIONS_BY_DOMAIN).flat();


