#!/usr/bin/env python3
"""Organize rule JSON files into folders"""
import os
import shutil
from pathlib import Path

# Base directory
base_dir = Path(__file__).parent

# Define folder structure and file mappings
folders = {
    "icc_core": [
        "incoterms2020.json", "urr725.json", "urf800.json", "urbpo750.json",
        "urdtt.json", "eurc_v1.1.json", "urc522.json", "urdg758.json",
        "ucp600.json", "isp98.json", "isbp745.json", "isbp745_v2.json",
        "eucp_v2.1_fixed.json", "icc.ucp600-2007-v1.0.0.json", "eucp v2.1.json"
    ],
    "messaging": [
        "swift_mt700.json", "swift_mt400_collections.json", 
        "swift_mt760_guarantees.json", "iso20022_trade.json",
        "iso20022_guarantees_standby.json"
    ],
    "crossdoc": [
        "lcopilot_crossdoc_v3.json", "lcopilot_crossdoc_v2.json",
        "lcopilot_crossdoc.json"
    ],
    "opinions_docdex": [
        "icc_opinions_key.json", "icc_opinions_additional.json",
        "docdex_cases_key.json", "docdex_cases_additional.json"
    ],
    "bank_profiles": [
        "bank_profiles.json", "additional_bank_profiles.json",
        "bank_profiles_china.json", "bank_profiles_india.json",
        "bank_profiles_canada.json", "bank_profiles_europe.json",
        "bank_profiles_asean.json", "bank_profiles_latam.json",
        "bank_profiles_mena.json", "bank_profiles_islamic.json"
    ],
    "fta_origin": [
        "fta_rcep_origin.json", "fta_cptpp_origin.json",
        "fta_usmca_origin.json", "fta_afcfta_origin.json",
        "fta_eu_uk_tca.json", "fta_asean_china.json",
        "fta_mercosur.json", "fta_eu_partnerships.json",
        "fta_us_bilateral.json", "fta_regional_blocs.json"
    ],
    "sanctions": [
        "sanctions_screening.json", "sanctions_ofac_detailed.json",
        "sanctions_eu_detailed.json", "sanctions_un_uk.json",
        "sanctions_vessel_shipping.json"
    ],
    "commodities": [
        "commodity_agriculture.json", "commodity_textiles.json",
        "commodity_chemicals.json", "commodity_electronics.json",
        "commodity_energy.json", "commodity_mining.json",
        "commodity_automotive.json", "commodity_pharma.json",
        "commodity_food_beverage.json", "commodity_machinery.json",
        "commodity_precious_metals.json", "commodity_timber_wood.json",
        "commodity_seafood.json"
    ],
    "jurisdiction_modes": [
        "us_mode_isp98.json"
    ],
    "country_rules": [
        "bd_bangladesh_bank.json", "in_rbi_rules.json", "sg_eta_2021.json",
        "ae_uae_compliance.json", "uk_etda_ebl.json", "cn_safe_china.json",
        "eu_customs_general.json", "de_germany_rules.json", "jp_japan_rules.json",
        "kr_korea_rules.json", "vn_vietnam_rules.json", "th_thailand_rules.json",
        "my_malaysia_rules.json", "ph_philippines_rules.json", "tw_taiwan_rules.json",
        "hk_hongkong_rules.json", "id_indonesia_rules.json", "tr_turkey_rules.json",
        "ng_nigeria_rules.json", "br_brazil_rules.json", "au_australia_rules.json",
        "mx_mexico_rules.json", "za_southafrica_rules.json", "eg_egypt_rules.json",
        "sa_saudi_rules.json", "pk_pakistan_rules.json", "cl_chile_rules.json",
        "co_colombia_rules.json", "pe_peru_rules.json", "ar_argentina_rules.json",
        "ke_kenya_rules.json", "lk_srilanka_rules.json", "pa_panama_rules.json",
        "gh_ghana_rules.json", "kz_kazakhstan_rules.json", "jo_jordan_rules.json",
        "ma_morocco_rules.json", "kh_cambodia_rules.json", "qa_qatar_rules.json",
        "nl_netherlands_rules.json", "nz_newzealand_rules.json", "kw_kuwait_rules.json",
        "bh_bahrain_rules.json", "om_oman_rules.json"
    ]
}

def main():
    moved = 0
    errors = []
    
    # Create folders and move files
    for folder_name, files in folders.items():
        folder_path = base_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        print(f"\n📁 {folder_name}/")
        
        for filename in files:
            src = base_dir / filename
            dst = folder_path / filename
            
            if src.exists():
                try:
                    shutil.move(str(src), str(dst))
                    print(f"  ✓ {filename}")
                    moved += 1
                except Exception as e:
                    errors.append(f"{filename}: {e}")
                    print(f"  ✗ {filename} - {e}")
            else:
                print(f"  - {filename} (not found)")
    
    print(f"\n{'='*50}")
    print(f"✅ Moved: {moved} files")
    if errors:
        print(f"❌ Errors: {len(errors)}")
        for err in errors:
            print(f"   {err}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()

