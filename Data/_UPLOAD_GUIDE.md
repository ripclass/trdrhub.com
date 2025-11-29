# TRDR Hub Ruleset Upload Guide

## Quick Reference

**Total Files:** 109
**Total Rules:** ~3,200+
**Upload Order:** Start with ICC Core → Cross-Doc → Then by priority

---

## 📁 FOLDER STRUCTURE

```
Data/
├── 📚 ICC CORE PUBLICATIONS (12 files)
│   ├── icc.ucp600-2007-v1.0.0.json      ← Main LC rules
│   ├── ucp600.json                       ← Alternative format
│   ├── isbp745_v2.json                   ← Banking practice (LARGE!)
│   ├── isbp745.json                      ← Original version
│   ├── eucp_v2.1_fixed.json              ← Electronic supplement
│   ├── isp98.json                        ← Standby LCs
│   ├── urdg758.json                      ← Demand guarantees
│   ├── urc522.json                       ← Collections
│   ├── eurc_v1.1.json                    ← Electronic collections
│   ├── urr725.json                       ← Reimbursements
│   ├── urf800.json                       ← Forfaiting
│   ├── urbpo750.json                     ← Bank Payment Obligation
│   ├── urdtt.json                        ← Digital trade
│   └── incoterms2020.json                ← Trade terms
│
├── 📨 MESSAGING STANDARDS (5 files)
│   ├── swift_mt700.json                  ← Documentary credits
│   ├── swift_mt400_collections.json      ← Collections
│   ├── swift_mt760_guarantees.json       ← Guarantees
│   ├── iso20022_trade.json               ← ISO 20022 LC
│   └── iso20022_guarantees_standby.json  ← ISO 20022 guarantees
│
├── 🔗 CROSS-DOCUMENT (2 files)
│   ├── lcopilot_crossdoc_v2.json         ← Main cross-doc rules
│   └── lcopilot_crossdoc.json            ← Legacy
│
├── ⚖️ ICC OPINIONS & DOCDEX (4 files)
│   ├── icc_opinions_key.json             ← 50 key opinions
│   ├── icc_opinions_additional.json      ← 12 more opinions
│   ├── docdex_cases_key.json             ← 30 key cases
│   └── docdex_cases_additional.json      ← 12 more cases
│
├── 🏦 BANK PROFILES (10 files)
│   ├── bank_profiles.json                ← Main profiles
│   ├── additional_bank_profiles.json     ← Extended profiles
│   ├── bank_profiles_china.json
│   ├── bank_profiles_india.json
│   ├── bank_profiles_canada.json
│   ├── bank_profiles_europe.json
│   ├── bank_profiles_asean.json
│   ├── bank_profiles_latam.json
│   ├── bank_profiles_mena.json
│   └── bank_profiles_islamic.json
│
├── 🌍 COUNTRY RULES (48 files)
│   ├── [See detailed list below]
│
├── 🚢 FTA/ORIGIN RULES (10 files)
│   ├── fta_rcep_origin.json
│   ├── fta_cptpp_origin.json
│   ├── fta_usmca_origin.json
│   ├── fta_afcfta_origin.json
│   ├── fta_eu_uk_tca.json
│   ├── fta_asean_china.json
│   ├── fta_mercosur.json
│   ├── fta_eu_partnerships.json
│   ├── fta_us_bilateral.json
│   └── fta_regional_blocs.json
│
├── 🚨 SANCTIONS (5 files)
│   ├── sanctions_screening.json
│   ├── sanctions_ofac_detailed.json
│   ├── sanctions_eu_detailed.json
│   ├── sanctions_un_uk.json
│   └── sanctions_vessel_shipping.json
│
├── 📦 COMMODITIES (13 files)
│   ├── commodity_agriculture.json
│   ├── commodity_textiles.json
│   ├── commodity_chemicals.json
│   ├── commodity_electronics.json
│   ├── commodity_energy.json
│   ├── commodity_mining.json
│   ├── commodity_automotive.json
│   ├── commodity_pharma.json
│   ├── commodity_food_beverage.json
│   ├── commodity_machinery.json
│   ├── commodity_precious_metals.json
│   ├── commodity_timber_wood.json
│   └── commodity_seafood.json
│
└── 🇺🇸 JURISDICTION MODES (1 file)
    └── us_mode_isp98.json
```

---

## 📋 COMPLETE UPLOAD TABLE

### 🔴 PRIORITY 1: ICC CORE (Upload First!)

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `icc.ucp600-2007-v1.0.0.json` | icc | icc.ucp600 | global | UCP600-2007 | 1.0.0 | Main LC rules - 39 articles |
| `isbp745_v2.json` | icc | icc.isbp745 | global | ISBP745-2013 | 2.0.0 | Banking practice - 247 rules (LARGE ~431KB!) |
| `eucp_v2.1_fixed.json` | icc | icc.eucp | global | eUCP2.1-2019 | 1.0.0 | Electronic presentation - 14 rules |
| `isp98.json` | icc | icc.isp98 | global | ISP98-1998 | 1.0.0 | Standby LCs - 178 rules |
| `urdg758.json` | icc | icc.urdg758 | global | URDG758-2010 | 1.0.0 | Demand guarantees - 35 rules |
| `urc522.json` | icc | icc.urc522 | global | URC522-1995 | 1.0.0 | Collections - 79 rules |
| `eurc_v1.1.json` | icc | icc.eurc | global | eURC1.1-2019 | 1.0.0 | Electronic collections - 44 rules |
| `urr725.json` | icc | icc.urr725 | global | URR725-2008 | 1.0.0 | Reimbursements - 47 rules |
| `urf800.json` | icc | icc.urf800 | global | URF800-2013 | 1.0.0 | Forfaiting - 37 rules |
| `urbpo750.json` | icc | icc.urbpo750 | global | URBPO750-2013 | 1.0.0 | Bank Payment Obligation - 35 rules |
| `urdtt.json` | icc | icc.urdtt | global | URDTT-2021 | 1.0.0 | Digital trade - 35 rules |
| `incoterms2020.json` | icc | icc.incoterms | global | Incoterms-2020 | 1.0.0 | Trade terms - 20 rules |

### 🟠 PRIORITY 2: MESSAGING STANDARDS

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `swift_mt700.json` | swift | swift.mt700 | global | MT700-2023 | 1.0.0 | Documentary credits - 37 rules |
| `swift_mt400_collections.json` | swift | swift.mt400 | global | MT400-2023 | 1.0.0 | Collections - 9 rules |
| `swift_mt760_guarantees.json` | swift | swift.mt760 | global | MT760-2023 | 1.0.0 | Guarantees - 11 rules |
| `iso20022_trade.json` | iso20022 | iso20022.trade | global | ISO20022-2023 | 1.0.0 | LC issuance/amendment - 32 rules |
| `iso20022_guarantees_standby.json` | iso20022 | iso20022.tsrv | global | ISO20022-2023 | 1.0.0 | Undertakings - 10 rules |

### 🟡 PRIORITY 3: CROSS-DOCUMENT RULES

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `lcopilot_crossdoc_v2.json` | icc | icc.lcopilot.crossdoc | global | CrossDoc-2025 | 2.0.0 | 72 cross-doc validation rules |

### 🟢 PRIORITY 4: ICC OPINIONS & DOCDEX

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `icc_opinions_key.json` | icc | icc.opinions | global | Opinions-2024 | 1.0.0 | 50 key Banking Commission opinions |
| `icc_opinions_additional.json` | icc | icc.opinions | global | Opinions-2024 | 1.1.0 | 12 additional opinions |
| `docdex_cases_key.json` | icc | icc.docdex | global | DOCDEX-2024 | 1.0.0 | 30 key DOCDEX decisions |
| `docdex_cases_additional.json` | icc | icc.docdex | global | DOCDEX-2024 | 1.1.0 | 12 additional decisions |

### 🔵 PRIORITY 5: BANK PROFILES

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `bank_profiles.json` | banks | banks.profiles | global | Profiles-2025 | 1.0.0 | HSBC, Citi, ICBC, StanChart, etc. - 27 rules |
| `additional_bank_profiles.json` | banks | banks.profiles | global | Profiles-2025 | 1.1.0 | MUFG, SMBC, BNP, etc. - 26 rules |
| `bank_profiles_china.json` | banks | banks.profiles.cn | cn | Profiles-2025 | 1.0.0 | CCB, ABC, BOCOM, CMB - 7 rules |
| `bank_profiles_india.json` | banks | banks.profiles.in | in | Profiles-2025 | 1.0.0 | SBI, ICICI, HDFC, Axis - 7 rules |
| `bank_profiles_canada.json` | banks | banks.profiles.ca | ca | Profiles-2025 | 1.0.0 | RBC, TD, Scotiabank - 6 rules |
| `bank_profiles_europe.json` | banks | banks.profiles.eu | eu | Profiles-2025 | 1.0.0 | UBS, Barclays, Crédit Agricole - 8 rules |
| `bank_profiles_asean.json` | banks | banks.profiles.asean | asean | Profiles-2025 | 1.0.0 | Maybank, CIMB, BCA - 8 rules |
| `bank_profiles_latam.json` | banks | banks.profiles.latam | latam | Profiles-2025 | 1.0.0 | Bradesco, Banorte, BCP - 8 rules |
| `bank_profiles_mena.json` | banks | banks.profiles.mena | mena | Profiles-2025 | 1.0.0 | FAB, ADCB, CIB Egypt - 8 rules |
| `bank_profiles_islamic.json` | banks | banks.profiles.islamic | global | Profiles-2025 | 1.0.0 | Al Rajhi, Dubai Islamic, QIB - 8 rules |

### 🟣 PRIORITY 6: FTA/ORIGIN RULES

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `fta_rcep_origin.json` | fta | fta.rcep | rcep | RCEP-2022 | 1.0.0 | 15 Asia-Pacific members - 15 rules |
| `fta_cptpp_origin.json` | fta | fta.cptpp | cptpp | CPTPP-2018 | 1.0.0 | 11 Pacific Rim members - 11 rules |
| `fta_usmca_origin.json` | fta | fta.usmca | usmca | USMCA-2020 | 1.0.0 | US, Mexico, Canada - 12 rules |
| `fta_afcfta_origin.json` | fta | fta.afcfta | africa | AfCFTA-2021 | 1.0.0 | 54 African countries - 10 rules |
| `fta_eu_uk_tca.json` | fta | fta.eu_uk | eu_gb | TCA-2021 | 1.0.0 | Brexit deal - 10 rules |
| `fta_asean_china.json` | fta | fta.acfta | acfta | ACFTA-2010 | 1.0.0 | ASEAN-China - 10 rules |
| `fta_mercosur.json` | fta | fta.mercosur | mercosur | Mercosur-1991 | 1.0.0 | South America - 10 rules |
| `fta_eu_partnerships.json` | fta | fta.eu_bilateral | eu | EU-FTAs-2024 | 1.0.0 | EU-Japan, EU-Korea, CETA, etc. - 10 rules |
| `fta_us_bilateral.json` | fta | fta.us_bilateral | us | US-FTAs-2024 | 1.0.0 | US-Israel, KORUS, etc. - 10 rules |
| `fta_regional_blocs.json` | fta | fta.regional | global | Regional-2024 | 1.0.0 | EFTA, GCC, ASEAN, SADC - 10 rules |

### ⚫ PRIORITY 7: SANCTIONS

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `sanctions_screening.json` | sanctions | sanctions.screening | global | Sanctions-2025 | 1.0.0 | General screening rules - 15 rules |
| `sanctions_ofac_detailed.json` | sanctions | sanctions.ofac | us | OFAC-2025 | 1.0.0 | US sanctions - 12 rules |
| `sanctions_eu_detailed.json` | sanctions | sanctions.eu | eu | EU-Sanctions-2025 | 1.0.0 | EU sanctions - 10 rules |
| `sanctions_un_uk.json` | sanctions | sanctions.un_uk | global | UN-UK-2025 | 1.0.0 | UN & UK sanctions - 10 rules |
| `sanctions_vessel_shipping.json` | sanctions | sanctions.vessel | global | Vessel-2025 | 1.0.0 | Maritime sanctions - 9 rules |

### ⬜ PRIORITY 8: COMMODITIES

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `commodity_agriculture.json` | commodity | commodity.agriculture | global | Agri-2025 | 1.0.0 | Phyto, health, organic - 15 rules |
| `commodity_textiles.json` | commodity | commodity.textiles | global | Textiles-2025 | 1.0.0 | Origin, GSP, labeling - 10 rules |
| `commodity_chemicals.json` | commodity | commodity.chemicals | global | Chemicals-2025 | 1.0.0 | GHS, REACH, IMDG - 12 rules |
| `commodity_electronics.json` | commodity | commodity.electronics | global | Electronics-2025 | 1.0.0 | CE, RoHS, FCC - 12 rules |
| `commodity_energy.json` | commodity | commodity.energy | global | Energy-2025 | 1.0.0 | Crude, LNG, coal - 10 rules |
| `commodity_mining.json` | commodity | commodity.mining | global | Mining-2025 | 1.0.0 | Copper, iron, gold - 10 rules |
| `commodity_automotive.json` | commodity | commodity.automotive | global | Auto-2025 | 1.0.0 | VIN, CoC, EPA - 10 rules |
| `commodity_pharma.json` | commodity | commodity.pharma | global | Pharma-2025 | 1.0.0 | GMP, CoA, cold chain - 10 rules |
| `commodity_food_beverage.json` | commodity | commodity.food | global | Food-2025 | 1.0.0 | HACCP, FDA, Halal - 10 rules |
| `commodity_machinery.json` | commodity | commodity.machinery | global | Machinery-2025 | 1.0.0 | CE, dual-use - 8 rules |
| `commodity_precious_metals.json` | commodity | commodity.precious | global | Precious-2025 | 1.0.0 | LBMA, assay - 8 rules |
| `commodity_timber_wood.json` | commodity | commodity.timber | global | Timber-2025 | 1.0.0 | EUDR, Lacey, FSC - 8 rules |
| `commodity_seafood.json` | commodity | commodity.seafood | global | Seafood-2025 | 1.0.0 | IUU, SIMP, MSC - 9 rules |

### 🌐 PRIORITY 9: COUNTRY RULES (48 files)

#### Asia-Pacific (17 countries)

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `cn_safe_china.json` | country | country.cn | cn | CN-2025 | 1.0.0 | SAFE, GACC, PBOC - 25 rules |
| `in_rbi_rules.json` | country | country.in | in | IN-2025 | 1.0.0 | RBI, FEMA, AD banks - 25 rules |
| `bd_bangladesh_bank.json` | country | country.bd | bd | BD-2025 | 1.0.0 | BB, LCAF, RMG - 25 rules |
| `sg_eta_2021.json` | country | country.sg | sg | SG-2025 | 1.0.0 | ETA, TradeTrust - 17 rules |
| `jp_japan_rules.json` | country | country.jp | jp | JP-2025 | 1.0.0 | METI, NACCS - 10 rules |
| `kr_korea_rules.json` | country | country.kr | kr | KR-2025 | 1.0.0 | KITA, UNI-PASS - 11 rules |
| `vn_vietnam_rules.json` | country | country.vn | vn | VN-2025 | 1.0.0 | SBV, VNACCS - 11 rules |
| `th_thailand_rules.json` | country | country.th | th | TH-2025 | 1.0.0 | BOT, NSW - 12 rules |
| `my_malaysia_rules.json` | country | country.my | my | MY-2025 | 1.0.0 | BNM, JAKIM - 12 rules |
| `ph_philippines_rules.json` | country | country.ph | ph | PH-2025 | 1.0.0 | BSP, BOC - 12 rules |
| `id_indonesia_rules.json` | country | country.id | id | ID-2025 | 1.0.0 | BI, CEISA - 12 rules |
| `tw_taiwan_rules.json` | country | country.tw | tw | TW-2025 | 1.0.0 | CBC, BOFT - 12 rules |
| `hk_hongkong_rules.json` | country | country.hk | hk | HK-2025 | 1.0.0 | TID, CEPA - 12 rules |
| `au_australia_rules.json` | country | country.au | au | AU-2025 | 1.0.0 | ABF, BICON - 12 rules |
| `nz_newzealand_rules.json` | country | country.nz | nz | NZ-2025 | 1.0.0 | RBNZ, MPI - 10 rules |
| `kh_cambodia_rules.json` | country | country.kh | kh | KH-2025 | 1.0.0 | NBC, EBA - 10 rules |
| `pk_pakistan_rules.json` | country | country.pk | pk | PK-2025 | 1.0.0 | SBP, WeBOC - 12 rules |

#### Europe (4 regions/countries)

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `eu_customs_general.json` | country | country.eu | eu | EU-2025 | 1.0.0 | UCC, TARIC - 20 rules |
| `uk_etda_ebl.json` | country | country.gb | gb | UK-2025 | 1.0.0 | ETDA, ECJU - 15 rules |
| `de_germany_rules.json` | country | country.de | de | DE-2025 | 1.0.0 | BAFA, ATLAS - 14 rules |
| `nl_netherlands_rules.json` | country | country.nl | nl | NL-2025 | 1.0.0 | Rotterdam, VAT - 11 rules |

#### Middle East & Africa (14 countries)

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `ae_uae_compliance.json` | country | country.ae | ae | UAE-2025 | 1.0.0 | CBUAE, ETTSL - 20 rules |
| `sa_saudi_rules.json` | country | country.sa | sa | SA-2025 | 1.0.0 | ZATCA, SABER - 12 rules |
| `eg_egypt_rules.json` | country | country.eg | eg | EG-2025 | 1.0.0 | CBE, NAFEZA - 12 rules |
| `qa_qatar_rules.json` | country | country.qa | qa | QA-2025 | 1.0.0 | QCB, LNG - 11 rules |
| `kw_kuwait_rules.json` | country | country.kw | kw | KW-2025 | 1.0.0 | CBK, GCC - 9 rules |
| `bh_bahrain_rules.json` | country | country.bh | bh | BH-2025 | 1.0.0 | CBB, Alba - 9 rules |
| `om_oman_rules.json` | country | country.om | om | OM-2025 | 1.0.0 | CBO, Salalah - 10 rules |
| `jo_jordan_rules.json` | country | country.jo | jo | JO-2025 | 1.0.0 | CBJ, QIZ - 10 rules |
| `ma_morocco_rules.json` | country | country.ma | ma | MA-2025 | 1.0.0 | BAM, Tanger Med - 11 rules |
| `za_southafrica_rules.json` | country | country.za | za | ZA-2025 | 1.0.0 | SARB, SACU - 12 rules |
| `ng_nigeria_rules.json` | country | country.ng | ng | NG-2025 | 1.0.0 | CBN, Form M - 12 rules |
| `ke_kenya_rules.json` | country | country.ke | ke | KE-2025 | 1.0.0 | CBK, EAC - 12 rules |
| `gh_ghana_rules.json` | country | country.gh | gh | GH-2025 | 1.0.0 | BOG, COCOBOD - 11 rules |
| `kz_kazakhstan_rules.json` | country | country.kz | kz | KZ-2025 | 1.0.0 | NBK, EAEU - 11 rules |

#### Americas (9 countries)

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `us_mode_isp98.json` | country | country.us | us | US-2025 | 1.0.0 | OFAC, EAR, UCC - 24 rules |
| `mx_mexico_rules.json` | country | country.mx | mx | MX-2025 | 1.0.0 | SAT, IMMEX - 12 rules |
| `br_brazil_rules.json` | country | country.br | br | BR-2025 | 1.0.0 | BCB, SISCOMEX - 12 rules |
| `ar_argentina_rules.json` | country | country.ar | ar | AR-2025 | 1.0.0 | BCRA, SIRA - 12 rules |
| `cl_chile_rules.json` | country | country.cl | cl | CL-2025 | 1.0.0 | Banco Central - 11 rules |
| `co_colombia_rules.json` | country | country.co | co | CO-2025 | 1.0.0 | BanRep, MUISCA - 12 rules |
| `pe_peru_rules.json` | country | country.pe | pe | PE-2025 | 1.0.0 | BCRP, SUNAT - 12 rules |
| `pa_panama_rules.json` | country | country.pa | pa | PA-2025 | 1.0.0 | Canal, Colón FZ - 10 rules |
| `lk_srilanka_rules.json` | country | country.lk | lk | LK-2025 | 1.0.0 | CBSL, BOI - 10 rules |

#### Turkey

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `tr_turkey_rules.json` | country | country.tr | tr | TR-2025 | 1.0.0 | CBRT, BİLGE - 12 rules |

---

## 📝 UPLOAD CHECKLIST

### Batch 1: ICC Core (12 files)
- [ ] `icc.ucp600-2007-v1.0.0.json` - Domain: `icc`, Rulebook: `icc.ucp600`
- [ ] `isbp745_v2.json` - Domain: `icc`, Rulebook: `icc.isbp745` ⚠️ LARGE FILE - May timeout
- [ ] `eucp_v2.1_fixed.json` - Domain: `icc`, Rulebook: `icc.eucp`
- [ ] `isp98.json` - Domain: `icc`, Rulebook: `icc.isp98`
- [ ] `urdg758.json` - Domain: `icc`, Rulebook: `icc.urdg758`
- [ ] `urc522.json` - Domain: `icc`, Rulebook: `icc.urc522`
- [ ] `eurc_v1.1.json` - Domain: `icc`, Rulebook: `icc.eurc`
- [ ] `urr725.json` - Domain: `icc`, Rulebook: `icc.urr725`
- [ ] `urf800.json` - Domain: `icc`, Rulebook: `icc.urf800`
- [ ] `urbpo750.json` - Domain: `icc`, Rulebook: `icc.urbpo750`
- [ ] `urdtt.json` - Domain: `icc`, Rulebook: `icc.urdtt`
- [ ] `incoterms2020.json` - Domain: `icc`, Rulebook: `icc.incoterms`

### Batch 2: Messaging (5 files)
- [ ] `swift_mt700.json` - Domain: `swift`, Rulebook: `swift.mt700`
- [ ] `swift_mt400_collections.json` - Domain: `swift`, Rulebook: `swift.mt400`
- [ ] `swift_mt760_guarantees.json` - Domain: `swift`, Rulebook: `swift.mt760`
- [ ] `iso20022_trade.json` - Domain: `iso20022`, Rulebook: `iso20022.trade`
- [ ] `iso20022_guarantees_standby.json` - Domain: `iso20022`, Rulebook: `iso20022.tsrv`

### Batch 3: Cross-Document (1 file)
- [ ] `lcopilot_crossdoc_v2.json` - Domain: `icc`, Rulebook: `icc.lcopilot.crossdoc`

### Batch 4: Opinions/DOCDEX (4 files)
- [ ] `icc_opinions_key.json` - Domain: `icc`, Rulebook: `icc.opinions`
- [ ] `icc_opinions_additional.json` - Domain: `icc`, Rulebook: `icc.opinions`
- [ ] `docdex_cases_key.json` - Domain: `icc`, Rulebook: `icc.docdex`
- [ ] `docdex_cases_additional.json` - Domain: `icc`, Rulebook: `icc.docdex`

### Batch 5: Bank Profiles (10 files)
- [ ] `bank_profiles.json` - Domain: `banks`, Rulebook: `banks.profiles`
- [ ] All regional bank profiles...

### Batch 6+: FTAs, Sanctions, Commodities, Countries...

---

## ⚠️ TIPS

1. **Large files may timeout** - `isbp745_v2.json` is 431KB. If it fails, try during low-traffic times.

2. **Use the right domain** - The dropdown must match:
   - `icc` for ICC publications
   - `swift` for MT messages
   - `iso20022` for ISO 20022
   - `fta` for trade agreements
   - `sanctions` for sanctions
   - `commodity` for commodities
   - `banks` for bank profiles
   - `country` for country rules

3. **Version format** - Use semantic versioning: `1.0.0`, `2.0.0`, etc.

4. **Notes are optional** - But helpful for tracking what's in each file.

5. **Don't duplicate** - Check if already uploaded before re-uploading.

---

## 🎯 QUICK COPY-PASTE REFERENCE

### For UCP600:
```
Domain: icc
Rulebook: icc.ucp600
Jurisdiction: global
Rulebook Version: UCP600-2007
Ruleset Version: 1.0.0
```

### For ISBP745:
```
Domain: icc
Rulebook: icc.isbp745
Jurisdiction: global
Rulebook Version: ISBP745-2013
Ruleset Version: 2.0.0
```

### For Cross-Document:
```
Domain: icc
Rulebook: icc.lcopilot.crossdoc
Jurisdiction: global
Rulebook Version: CrossDoc-2025
Ruleset Version: 2.0.0
```

---

*Generated for TRDR Hub LCopilot - 109 files, ~3,200 rules*

