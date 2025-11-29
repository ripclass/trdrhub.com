# TRDR Hub Ruleset Upload Guide

## Quick Reference

**Total Files:** 110
**Total Rules:** ~3,230+
**Upload Order:** Start with ICC Core → Cross-Doc → Then by priority

---

## 🎯 UPLOADER DOMAIN DROPDOWN

**IMPORTANT:** The domain you select in the uploader dropdown must match the `"domain"` value inside the JSON file!

| Upload Dropdown | Used For | Example Domains in JSON |
|-----------------|----------|-------------------------|
| `icc` | ICC Core publications | `icc`, `icc.ucp600`, `icc.isbp745`, `icc.opinions`, `icc.docdex` |
| `swift` | SWIFT MT messages | `swift.mt700`, `swift.mt760`, `swift.mt400` |
| `iso20022` | ISO 20022 standards | `iso20022.trade`, `iso20022.tsrv` |
| `fta` | Free Trade Agreements | `fta.rcep`, `fta.cptpp`, `fta.usmca`, `fta.afcfta` |
| `sanctions` | Sanctions screening | `sanctions.ofac`, `sanctions.eu`, `sanctions.un`, `sanctions.vessel` |
| `commodity` | Commodity-specific | `commodity.agriculture`, `commodity.textiles`, `commodity.chemicals` |
| `bank` | Bank profiles | `bank.hsbc`, `bank.china`, `bank.india`, `bank.islamic` |
| `regulations` | Country regulations | `regulations.cn`, `regulations.in`, `regulations.eu`, `regulations.us` |
| `export_control` | Export controls | `export_control.us`, `export_control.eu` |
| `law` | Legal frameworks | `law.ucc.us` |
| `mode` | Mode-specific rules | `mode.us` |

---

## 🗂️ ORGANIZE FILES INTO FOLDERS

Run this Python script to organize all JSON files into folders:

```bash
cd Data
python organize_rules.py
```

Or manually create these folders and move files:

---

## 📁 FOLDER STRUCTURE

```
Data/
├── 📚 icc_core/ (14 files)
│   ├── icc.ucp600-2007-v1.0.0.json      ← Main LC rules
│   ├── ucp600.json                       ← Alternative format
│   ├── isbp745_v2.json                   ← Banking practice (LARGE!)
│   ├── isbp745.json                      ← Original version
│   ├── eucp_v2.1_fixed.json              ← Electronic supplement
│   ├── eucp v2.1.json                    ← Original eUCP
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
├── 📨 messaging/ (5 files)
│   ├── swift_mt700.json                  ← Documentary credits
│   ├── swift_mt400_collections.json      ← Collections
│   ├── swift_mt760_guarantees.json       ← Guarantees
│   ├── iso20022_trade.json               ← ISO 20022 LC
│   └── iso20022_guarantees_standby.json  ← ISO 20022 guarantees
│
├── 🔗 crossdoc/ (3 files)
│   ├── lcopilot_crossdoc_v3.json         ← LATEST! Context-aware (100 rules)
│   ├── lcopilot_crossdoc_v2.json         ← Previous version (72 rules)
│   └── lcopilot_crossdoc.json            ← Legacy (6 rules)
│
├── ⚖️ opinions_docdex/ (2 merged files)
│   ├── icc_opinions_merged.json          ← 60 opinions (merged)
│   └── docdex_cases_merged.json          ← 42 DOCDEX cases (merged)
│
├── 🏦 bank_profiles/ (10 files)
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
├── 🌍 country_rules/ (48 files)
│   ├── [See detailed list below]
│
├── 🚢 fta_origin/ (10 files)
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
├── 🚨 sanctions/ (5 files)
│   ├── sanctions_screening.json
│   ├── sanctions_ofac_detailed.json
│   ├── sanctions_eu_detailed.json
│   ├── sanctions_un_uk.json
│   └── sanctions_vessel_shipping.json
│
├── 📦 commodities/ (13 files)
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
├── 🇺🇸 jurisdiction_modes/ (1 file)
│   └── us_mode_isp98.json
│
├── _UPLOAD_GUIDE.md                      ← This file
└── organize_rules.py                     ← Run to organize files
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
| `lcopilot_crossdoc_v3.json` | icc | icc.lcopilot.crossdoc | global | CrossDoc-2025 | 3.0.0 | **100 rules** - Bank/Country/Commodity/FTA/Sanctions aware |
| `lcopilot_crossdoc_v2.json` | icc | icc.lcopilot.crossdoc | global | CrossDoc-2025 | 2.0.0 | 72 cross-doc rules (superseded by v3) |

### 🟢 PRIORITY 4: ICC OPINIONS & DOCDEX

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `icc_opinions_merged.json` | icc | icc.opinions | global | Opinions-2024 | 1.0.0 | **60 merged Banking Commission opinions** |
| `docdex_cases_merged.json` | icc | icc.docdex | global | DOCDEX-2024 | 1.0.0 | **42 merged DOCDEX decisions** |

> ⚠️ **Note:** Key + Additional files have been merged. Upload only the merged files to avoid duplicates.

### 🔵 PRIORITY 5: BANK PROFILES

| File | Domain | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|--------|----------|--------------|--------------|-------------|-------|
| `bank_profiles.json` | bank | bank.profiles | global | Profiles-2025 | 1.0.0 | HSBC, Citi, ICBC, StanChart, etc. - 27 rules |
| `additional_bank_profiles.json` | bank | bank.profiles | global | Profiles-2025 | 1.1.0 | MUFG, SMBC, BNP, etc. - 26 rules |
| `bank_profiles_china.json` | bank | bank.china | cn | Profiles-2025 | 1.0.0 | CCB, ABC, BOCOM, CMB - 7 rules |
| `bank_profiles_india.json` | bank | bank.india | in | Profiles-2025 | 1.0.0 | SBI, ICICI, HDFC, Axis - 7 rules |
| `bank_profiles_canada.json` | bank | bank.canada | ca | Profiles-2025 | 1.0.0 | RBC, TD, Scotiabank - 6 rules |
| `bank_profiles_europe.json` | bank | bank.europe | eu | Profiles-2025 | 1.0.0 | UBS, Barclays, Crédit Agricole - 8 rules |
| `bank_profiles_asean.json` | bank | bank.asean | asean | Profiles-2025 | 1.0.0 | Maybank, CIMB, BCA - 8 rules |
| `bank_profiles_latam.json` | bank | bank.latam | latam | Profiles-2025 | 1.0.0 | Bradesco, Banorte, BCP - 8 rules |
| `bank_profiles_mena.json` | bank | bank.mena | mena | Profiles-2025 | 1.0.0 | FAB, ADCB, CIB Egypt - 8 rules |
| `bank_profiles_islamic.json` | bank | bank.islamic | global | Profiles-2025 | 1.0.0 | Al Rajhi, Dubai Islamic, QIB - 8 rules |

### 🟣 PRIORITY 6: FTA/ORIGIN RULES

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `fta_rcep_origin.json` | fta.rcep | fta.rcep | rcep | RCEP-2022 | 1.0.0 | 15 Asia-Pacific members - 15 rules |
| `fta_cptpp_origin.json` | fta.cptpp | fta.cptpp | cptpp | CPTPP-2018 | 1.0.0 | 11 Pacific Rim members - 11 rules |
| `fta_usmca_origin.json` | fta.usmca | fta.usmca | usmca | USMCA-2020 | 1.0.0 | US, Mexico, Canada - 12 rules |
| `fta_afcfta_origin.json` | fta.afcfta | fta.afcfta | africa | AfCFTA-2021 | 1.0.0 | 54 African countries - 10 rules |
| `fta_eu_uk_tca.json` | fta.eu_uk | fta.eu_uk | eu_gb | TCA-2021 | 1.0.0 | Brexit deal - 10 rules |
| `fta_asean_china.json` | fta.acfta | fta.acfta | acfta | ACFTA-2010 | 1.0.0 | ASEAN-China - 10 rules |
| `fta_mercosur.json` | fta.mercosur | fta.mercosur | mercosur | Mercosur-1991 | 1.0.0 | South America - 10 rules |
| `fta_eu_partnerships.json` | fta.* | fta.eu_bilateral | eu | EU-FTAs-2024 | 1.0.0 | EU-Japan, EU-Korea, CETA, etc. - 10 rules |
| `fta_us_bilateral.json` | fta.* | fta.us_bilateral | us | US-FTAs-2024 | 1.0.0 | US-Israel, KORUS, etc. - 10 rules |
| `fta_regional_blocs.json` | fta.* | fta.regional | global | Regional-2024 | 1.0.0 | EFTA, GCC, ASEAN, SADC - 10 rules |

### ⚫ PRIORITY 7: SANCTIONS

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `sanctions_screening.json` | sanctions.* | sanctions.screening | global | Sanctions-2025 | 1.0.0 | General screening rules - 15 rules |
| `sanctions_ofac_detailed.json` | sanctions.ofac | sanctions.ofac | us | OFAC-2025 | 1.0.0 | US sanctions - 12 rules |
| `sanctions_eu_detailed.json` | sanctions.eu | sanctions.eu | eu | EU-Sanctions-2025 | 1.0.0 | EU sanctions - 10 rules |
| `sanctions_un_uk.json` | sanctions.un, sanctions.uk | sanctions.un_uk | global | UN-UK-2025 | 1.0.0 | UN & UK sanctions - 10 rules |
| `sanctions_vessel_shipping.json` | sanctions.vessel | sanctions.vessel | global | Vessel-2025 | 1.0.0 | Maritime sanctions - 9 rules |

### ⬜ PRIORITY 8: COMMODITIES

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `commodity_agriculture.json` | commodity.agriculture | commodity.agriculture | global | Agri-2025 | 1.0.0 | Phyto, health, organic - 15 rules |
| `commodity_textiles.json` | commodity.textiles | commodity.textiles | global | Textiles-2025 | 1.0.0 | Origin, GSP, labeling - 10 rules |
| `commodity_chemicals.json` | commodity.chemicals | commodity.chemicals | global | Chemicals-2025 | 1.0.0 | GHS, REACH, IMDG - 12 rules |
| `commodity_electronics.json` | commodity.electronics | commodity.electronics | global | Electronics-2025 | 1.0.0 | CE, RoHS, FCC - 12 rules |
| `commodity_energy.json` | commodity.energy | commodity.energy | global | Energy-2025 | 1.0.0 | Crude, LNG, coal - 10 rules |
| `commodity_mining.json` | commodity.mining | commodity.mining | global | Mining-2025 | 1.0.0 | Copper, iron, gold - 10 rules |
| `commodity_automotive.json` | commodity.automotive | commodity.automotive | global | Auto-2025 | 1.0.0 | VIN, CoC, EPA - 10 rules |
| `commodity_pharma.json` | commodity.pharma | commodity.pharma | global | Pharma-2025 | 1.0.0 | GMP, CoA, cold chain - 10 rules |
| `commodity_food_beverage.json` | commodity.food | commodity.food | global | Food-2025 | 1.0.0 | HACCP, FDA, Halal - 10 rules |
| `commodity_machinery.json` | commodity.machinery | commodity.machinery | global | Machinery-2025 | 1.0.0 | CE, dual-use - 8 rules |
| `commodity_precious_metals.json` | commodity.precious_metals | commodity.precious | global | Precious-2025 | 1.0.0 | LBMA, assay - 8 rules |
| `commodity_timber_wood.json` | commodity.timber | commodity.timber | global | Timber-2025 | 1.0.0 | EUDR, Lacey, FSC - 8 rules |
| `commodity_seafood.json` | commodity.seafood | commodity.seafood | global | Seafood-2025 | 1.0.0 | IUU, SIMP, MSC - 9 rules |

### 🌐 PRIORITY 9: COUNTRY RULES (48 files)

#### Asia-Pacific (17 countries)

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `cn_safe_china.json` | regulations.cn | regulations.cn | cn | CN-2025 | 1.0.0 | SAFE, GACC, PBOC - 25 rules |
| `in_rbi_rules.json` | regulations.in | regulations.in | in | IN-2025 | 1.0.0 | RBI, FEMA, AD banks - 25 rules |
| `bd_bangladesh_bank.json` | regulations.bd | regulations.bd | bd | BD-2025 | 1.0.0 | BB, LCAF, RMG - 25 rules |
| `sg_eta_2021.json` | regulations.sg | regulations.sg | sg | SG-2025 | 1.0.0 | ETA, TradeTrust - 17 rules |
| `jp_japan_rules.json` | regulations.jp | regulations.jp | jp | JP-2025 | 1.0.0 | METI, NACCS - 10 rules |
| `kr_korea_rules.json` | regulations.kr | regulations.kr | kr | KR-2025 | 1.0.0 | KITA, UNI-PASS - 11 rules |
| `vn_vietnam_rules.json` | regulations.vn | regulations.vn | vn | VN-2025 | 1.0.0 | SBV, VNACCS - 11 rules |
| `th_thailand_rules.json` | regulations.th | regulations.th | th | TH-2025 | 1.0.0 | BOT, NSW - 12 rules |
| `my_malaysia_rules.json` | regulations.my | regulations.my | my | MY-2025 | 1.0.0 | BNM, JAKIM - 12 rules |
| `ph_philippines_rules.json` | regulations.ph | regulations.ph | ph | PH-2025 | 1.0.0 | BSP, BOC - 12 rules |
| `id_indonesia_rules.json` | regulations.id | regulations.id | id | ID-2025 | 1.0.0 | BI, CEISA - 12 rules |
| `tw_taiwan_rules.json` | regulations.tw | regulations.tw | tw | TW-2025 | 1.0.0 | CBC, BOFT - 12 rules |
| `hk_hongkong_rules.json` | regulations.hk | regulations.hk | hk | HK-2025 | 1.0.0 | TID, CEPA - 12 rules |
| `au_australia_rules.json` | regulations.au | regulations.au | au | AU-2025 | 1.0.0 | ABF, BICON - 12 rules |
| `nz_newzealand_rules.json` | regulations.nz | regulations.nz | nz | NZ-2025 | 1.0.0 | RBNZ, MPI - 10 rules |
| `kh_cambodia_rules.json` | regulations.kh | regulations.kh | kh | KH-2025 | 1.0.0 | NBC, EBA - 10 rules |
| `pk_pakistan_rules.json` | regulations.pk | regulations.pk | pk | PK-2025 | 1.0.0 | SBP, WeBOC - 12 rules |

#### Europe (4 regions/countries)

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `eu_customs_general.json` | regulations.eu | regulations.eu | eu | EU-2025 | 1.0.0 | UCC, TARIC - 20 rules |
| `uk_etda_ebl.json` | regulations.uk | regulations.uk | gb | UK-2025 | 1.0.0 | ETDA, ECJU - 15 rules |
| `de_germany_rules.json` | regulations.de | regulations.de | de | DE-2025 | 1.0.0 | BAFA, ATLAS - 14 rules |
| `nl_netherlands_rules.json` | regulations.nl | regulations.nl | nl | NL-2025 | 1.0.0 | Rotterdam, VAT - 11 rules |

#### Middle East & Africa (14 countries)

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `ae_uae_compliance.json` | regulations.ae | regulations.ae | ae | UAE-2025 | 1.0.0 | CBUAE, ETTSL - 20 rules |
| `sa_saudi_rules.json` | regulations.sa | regulations.sa | sa | SA-2025 | 1.0.0 | ZATCA, SABER - 12 rules |
| `eg_egypt_rules.json` | regulations.eg | regulations.eg | eg | EG-2025 | 1.0.0 | CBE, NAFEZA - 12 rules |
| `qa_qatar_rules.json` | regulations.qa | regulations.qa | qa | QA-2025 | 1.0.0 | QCB, LNG - 11 rules |
| `kw_kuwait_rules.json` | regulations.kw | regulations.kw | kw | KW-2025 | 1.0.0 | CBK, GCC - 9 rules |
| `bh_bahrain_rules.json` | regulations.bh | regulations.bh | bh | BH-2025 | 1.0.0 | CBB, Alba - 9 rules |
| `om_oman_rules.json` | regulations.om | regulations.om | om | OM-2025 | 1.0.0 | CBO, Salalah - 10 rules |
| `jo_jordan_rules.json` | regulations.jo | regulations.jo | jo | JO-2025 | 1.0.0 | CBJ, QIZ - 10 rules |
| `ma_morocco_rules.json` | regulations.ma | regulations.ma | ma | MA-2025 | 1.0.0 | BAM, Tanger Med - 11 rules |
| `za_southafrica_rules.json` | regulations.za | regulations.za | za | ZA-2025 | 1.0.0 | SARB, SACU - 12 rules |
| `ng_nigeria_rules.json` | regulations.ng | regulations.ng | ng | NG-2025 | 1.0.0 | CBN, Form M - 12 rules |
| `ke_kenya_rules.json` | regulations.ke | regulations.ke | ke | KE-2025 | 1.0.0 | CBK, EAC - 12 rules |
| `gh_ghana_rules.json` | regulations.gh | regulations.gh | gh | GH-2025 | 1.0.0 | BOG, COCOBOD - 11 rules |
| `kz_kazakhstan_rules.json` | regulations.kz | regulations.kz | kz | KZ-2025 | 1.0.0 | NBK, EAEU - 11 rules |

#### Americas (9 countries)

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `us_mode_isp98.json` | mode.us | mode.us | us | US-2025 | 1.0.0 | OFAC, EAR, UCC - 24 rules |
| `mx_mexico_rules.json` | regulations.mx | regulations.mx | mx | MX-2025 | 1.0.0 | SAT, IMMEX - 12 rules |
| `br_brazil_rules.json` | regulations.br | regulations.br | br | BR-2025 | 1.0.0 | BCB, SISCOMEX - 12 rules |
| `ar_argentina_rules.json` | regulations.ar | regulations.ar | ar | AR-2025 | 1.0.0 | BCRA, SIRA - 12 rules |
| `cl_chile_rules.json` | regulations.cl | regulations.cl | cl | CL-2025 | 1.0.0 | Banco Central - 11 rules |
| `co_colombia_rules.json` | regulations.co | regulations.co | co | CO-2025 | 1.0.0 | BanRep, MUISCA - 12 rules |
| `pe_peru_rules.json` | regulations.pe | regulations.pe | pe | PE-2025 | 1.0.0 | BCRP, SUNAT - 12 rules |
| `pa_panama_rules.json` | regulations.pa | regulations.pa | pa | PA-2025 | 1.0.0 | Canal, Colón FZ - 10 rules |
| `lk_srilanka_rules.json` | regulations.lk | regulations.lk | lk | LK-2025 | 1.0.0 | CBSL, BOI - 10 rules |

#### Turkey

| File | Domain (in JSON) | Rulebook | Jurisdiction | Rulebook Ver | Ruleset Ver | Notes |
|------|-----------------|----------|--------------|--------------|-------------|-------|
| `tr_turkey_rules.json` | regulations.tr | regulations.tr | tr | TR-2025 | 1.0.0 | CBRT, BİLGE - 12 rules |

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

### Batch 3: Cross-Document (1 file - use v3!)
- [ ] `lcopilot_crossdoc_v3.json` - Domain: `icc`, Rulebook: `icc.lcopilot.crossdoc` ← **USE THIS ONE** (100 context-aware rules)

### Batch 4: Opinions/DOCDEX (2 merged files)
- [ ] `icc_opinions_merged.json` - Domain: `icc`, Rulebook: `icc.opinions` (60 opinions)
- [ ] `docdex_cases_merged.json` - Domain: `icc`, Rulebook: `icc.docdex` (42 cases)

### Batch 5: Bank Profiles (10 files)
- [ ] `bank_profiles.json` - Domain: `bank.*`, Rulebook: `bank.profiles`
- [ ] `bank_profiles_china.json` - Domain: `bank.china`, Rulebook: `bank.china`
- [ ] `bank_profiles_india.json` - Domain: `bank.india`, Rulebook: `bank.india`
- [ ] All regional bank profiles...

### Batch 6: FTAs (10 files)
- [ ] `fta_rcep_origin.json` - Domain: `fta.rcep`, Rulebook: `fta.rcep`
- [ ] `fta_cptpp_origin.json` - Domain: `fta.cptpp`, Rulebook: `fta.cptpp`
- [ ] All FTA files...

### Batch 7: Sanctions (5 files)
- [ ] `sanctions_screening.json` - Domain: `sanctions.*`, Rulebook: `sanctions.screening`
- [ ] `sanctions_ofac_detailed.json` - Domain: `sanctions.ofac`, Rulebook: `sanctions.ofac`
- [ ] All sanctions files...

### Batch 8: Commodities (13 files)
- [ ] `commodity_agriculture.json` - Domain: `commodity.agriculture`
- [ ] `commodity_textiles.json` - Domain: `commodity.textiles`
- [ ] All commodity files...

### Batch 9: Country Regulations (48 files)
- [ ] `cn_safe_china.json` - Domain: `regulations.cn`, Rulebook: `regulations.cn`
- [ ] `in_rbi_rules.json` - Domain: `regulations.in`, Rulebook: `regulations.in`
- [ ] All country files...

---

## ⚠️ TIPS

1. **Large files may timeout** - `isbp745_v2.json` is 431KB. If it fails, try during low-traffic times.

2. **Use the right domain** - The dropdown must match the domain in the JSON file:

   | Domain | Description | Sub-domains |
   |--------|-------------|-------------|
   | `icc` | ICC Core publications | `icc.ucp600`, `icc.isbp745`, `icc.eucp`, `icc.isp98`, `icc.urdg758`, `icc.urc522`, `icc.eurc`, `icc.urr725`, `icc.urf800`, `icc.urbpo750`, `icc.urdtt`, `icc.incoterms`, `icc.opinions`, `icc.docdex`, `icc.lcopilot.crossdoc` |
   | `swift` | SWIFT MT messages | `swift.mt700`, `swift.mt707`, `swift.mt760`, `swift.mt767`, `swift.mt768`, `swift.mt400`, `swift.mt410`, `swift.mt412`, `swift.mt416`, `swift.mt420`, `swift.mt422`, `swift.mt430` |
   | `iso20022` | ISO 20022 standards | `iso20022.trade`, `iso20022.tsrv` |
   | `fta` | Free Trade Agreements | `fta.rcep`, `fta.cptpp`, `fta.usmca`, `fta.afcfta`, `fta.eu_uk`, `fta.acfta`, `fta.mercosur`, `fta.eu_japan`, `fta.eu_korea`, `fta.ceta`, `fta.korus`, `fta.efta`, `fta.gcc`, `fta.sadc`, `fta.comesa`, `fta.ecowas`, `fta.pacific_alliance`, `fta.eaeu`, `fta.asean`, `fta.ausfta`, `fta.eusfta`, `fta.evfta`, `fta.us_israel`, `fta.uschile`, `fta.uspanama`, `fta.ussfta`, `fta.ctpa`, `fta.ptpa`, `fta.pem`, `fta.eu_mexico` |
   | `sanctions` | Sanctions screening | `sanctions.ofac`, `sanctions.ofac.us`, `sanctions.eu`, `sanctions.un`, `sanctions.uk`, `sanctions.global`, `sanctions.vessel`, `sanctions.port`, `sanctions.cn`, `sanctions.ae`, `sanctions.swiss`, `sanctions.checklist` |
   | `commodity` | Commodity-specific rules | `commodity.agriculture`, `commodity.textiles`, `commodity.chemicals`, `commodity.electronics`, `commodity.energy`, `commodity.mining`, `commodity.automotive`, `commodity.pharma`, `commodity.food`, `commodity.beverage`, `commodity.machinery`, `commodity.precious_metals`, `commodity.timber`, `commodity.seafood` |
   | `bank` | Bank profiles | `bank.hsbc`, `bank.citi`, `bank.icbc`, `bank.boc`, `bank.scb`, `bank.jpmorgan`, `bank.bofa`, `bank.deutsche`, `bank.bnp`, `bank.socgen`, `bank.mufg`, `bank.smbc`, `bank.mizuho`, `bank.dbs`, `bank.uob`, `bank.nab`, `bank.anz`, `bank.china`, `bank.india`, `bank.canada`, `bank.europe`, `bank.asean`, `bank.latam`, `bank.mena`, `bank.islamic`, etc. |
   | `regulations` | Country regulations | `regulations.cn`, `regulations.in`, `regulations.bd`, `regulations.sg`, `regulations.ae`, `regulations.eu`, `regulations.uk`, `regulations.us`, `regulations.jp`, `regulations.kr`, `regulations.vn`, `regulations.th`, `regulations.my`, `regulations.ph`, `regulations.id`, `regulations.tw`, `regulations.hk`, `regulations.au`, `regulations.nz`, `regulations.de`, `regulations.nl`, `regulations.sa`, `regulations.eg`, `regulations.ng`, `regulations.za`, `regulations.ke`, `regulations.mx`, `regulations.br`, `regulations.ar`, `regulations.cl`, `regulations.co`, `regulations.pe`, `regulations.pa`, `regulations.lk`, `regulations.tr`, `regulations.kw`, `regulations.bh`, `regulations.qa`, `regulations.om`, `regulations.jo`, `regulations.ma`, `regulations.gh`, `regulations.kz`, `regulations.kh`, `regulations.pk` |
   | `export_control` | Export control rules | `export_control.us`, `export_control.eu` |
   | `law` | Legal frameworks | `law.ucc.us` |
   | `mode` | Mode-specific rules | `mode.us` |

3. **Version format** - Use semantic versioning: `1.0.0`, `2.0.0`, etc.

4. **Notes are optional** - But helpful for tracking what's in each file.

5. **Don't duplicate** - Check if already uploaded before re-uploading.

6. **Domain must match JSON** - The domain in the uploader MUST match what's inside the JSON file's `"domain"` field!

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

