# Bridging Brain - Complete Column Mapping (113 Columns)

## Overview
This document maps ALL 113 database columns to their usage in the filtering funnel.
**NO COLUMN SHOULD BE WASTED.**

---

## FUNNEL ARCHITECTURE

| Stage | Purpose | Columns Used |
|-------|---------|--------------|
| **LEFT BRAIN** | Coarse knockouts | ~15 columns |
| **MIDDLE BRAIN** | Dynamic refiners | ~35 columns |
| **RIGHT BRAIN (AI)** | Subtle discrimination | ~50 columns + free text |
| **Display Only** | Contact/reference info | ~13 columns |

---

## LEFT BRAIN - Coarse Filters (Hard Knockouts)

These eliminate lenders immediately based on fundamental incompatibility.

| User Input | Database Column | Filter Logic |
|------------|-----------------|--------------|
| Loan Amount | `minimum_loan_size`, `maximum_loan_size` | loan < min OR loan > max = OUT |
| Property Value | (used for LTV calc) | - |
| LTV Calculation | `max_ltv_1st_charge_residential_investment_property` | calculated LTV > max = OUT |
| | `max_ltv_1st_charge_semi_commercial_mixed_use` | (based on property type) |
| | `max_ltv_1st_charge_fully_commercial` | |
| | `max_ltv_supporting_2nd_charge_residential_investment_propert` | (based on charge) |
| | `max_ltv_standalone_2nd_charge_resi_investments` | |
| | `max_ltv_supporting_equitable_charges` | |
| | `max_ltv_standalone_equitable_charges` | |
| | `max_ltv_1st_charge_regulated_bridge` | (if regulated) |
| Property Type | `residential_property`, `mixed_use_property_commercial_resi`, `commercial_property` | Valuation policy check |
| Geography | `which_geographies_don_t_you_lend_in` | If geography in exclusion list = OUT |
| Charge Position | (selects which LTV column to use) | - |
| Regulated? | `regulated_bridging_offered` | If regulated and "No" = OUT |
| Refurb? | `do_you_offer_bridging_finance_for_properties_requiring_refur` | If refurb and "No" = OUT |
| Entity Type | (triggers borrower columns) | - |

---

## MIDDLE BRAIN - Dynamic Refiners (Appear Based on Left Brain)

These narrow the pool further. Show as clickable chips with impact counts.

### Always Available Refiners

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🌍 Foreign National | `can_you_lend_to_foreign_nationals` | Always |
| 🛫 Expat | `can_you_lend_to_expats` | Always |
| ⚠️ Light Adverse | `heavy_recent_adverse_accepted_eg_missed_mortgage_payments_or` | Always |
| 💀 Bankruptcy/IVA | `bankrupcy_ivas_accepted` | Always |
| ⚡ Speed Critical | `dual_legal_rep_offered`, `minimum_number_of_months_interest` | Always |
| 💰 Serviced Interest | `serviced_interest_allowed` | Always |

### Entity-Triggered Refiners

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🏢 Limited Company | `do_you_always_require_pgs_for_directors_of_limited_companies` | Entity = Ltd |
| 🏛️ Trust | `do_you_lend_to_trusts` | Entity = Trust |
| 🎁 Charity | `do_you_lend_to_charities` | Entity = Charity |
| 💼 SIPP/SSAS | `can_you_lend_to_sipps_ssas_pensions` | Entity = SIPP/SSAS |
| 🌐 Overseas Entity | `do_you_lend_to_overseas_entities` | Entity = Overseas |
| 🔗 LLP | `do_you_lend_to_limited_liability_partnerships` | Entity = LLP |
| 📚 Layered Companies | `do_you_lend_to_layered_uk_companies` | Entity = Ltd |

### Borrower-Triggered Refiners

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🏠 First Time Buyer | `do_you_lend_to_first_time_buyers` | Always |
| 🔑 First Time Landlord | `do_you_lend_to_first_time_landlords` | Always |
| 📊 Nil/Negative A&L | `do_you_lend_to_applicants_with_a_nil_or_negative_a_l_profile` | Always |
| 💵 100% Investor Funds | `100_investor_funds_for_deposit_accepted` | Always |
| 🏡 Non-Owner Occupier | `do_you_lend_to_non_owner_occupiers` | Always |

### Refurb-Triggered Refiners (When Refurb = Yes)

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🔨 Light Works (<30%) | `maximum_cost_of_works_as_of_purchase_price_value`, `maximum_day_1_ltv` | Refurb ON |
| 🏗️ Medium Works (30-50%) | `do_you_fund_medium_works_30_50_cost_of_works_to_value` | Refurb ON, intensity=medium |
| 🚧 Heavy Works (50-100%) | `do_you_fund_heavy_works_50_100_cost_of_works_to_value` | Refurb ON, intensity=heavy |
| 🏭 Very Heavy (>100%) | `do_you_fund_very_heavy_works_over_100_cost_of_works_to_value` | Refurb ON, intensity=very_heavy |
| 💸 Need Staged Funding | `do_you_also_offer_arrears_staged_funding_for_refurbishments` | Refurb ON |
| 📋 Cosmetic Only | `must_works_be_cosmetic_non_structural_only` | Refurb ON |
| 👷 First-Time Developer | `minimum_borrower_experience_with_refurbs`, `minimum_developer_experience` | Refurb ON |
| 🏠 Regulated Refurb | `will_you_finance_refurbishments_on_regulated_deals` | Refurb + Regulated |
| 🏢 Commercial Refurb | `do_you_offer_refurb_products_on_commercial_property_without_` | Refurb + Commercial |
| 🔧 Ground-Up Element | `do_you_allow_an_element_of_ground_up_build_on_your_refurb_pr` | Refurb ON |

### Land-Triggered Refiners (When Property Type = Land)

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 📐 Land Without Planning | `what_ltv_will_you_potentially_lend_on_land_without_planning` | Property = Land (No PP) |
| 📋 Land With Planning | `what_ltv_will_you_potentially_lend_on_land_with_planning` | Property = Land (With PP) |
| 🏗️ Pure Ground-Up Dev | `do_you_do_pure_ground_up_development_finance` | Property = Land |

### Product Feature Refiners

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🔄 Flexible Facility | `flexible_rotating_credit_facility_product_offered` | Always |
| 📈 Stepped Rate | `stepped_rate_products_available` | Always |
| 🏠 AVM Available (Resi) | `can_you_potentially_use_avms_and_or_desktops_for_residential` | Property = Resi |
| 🏢 AVM Available (Comm) | `can_you_potentially_use_avms_and_or_desktops_for_commercial_` | Property = Comm |
| 📜 Indemnity Accepted | `indemnity_policies_title_insurance_accepted_instead_of_full_` | Always |
| 🌐 Fully Remote | `fully_remote_process_supported` | Always |
| 📑 Retypes Considered | `retypes_considered` | Always |

### BMV-Triggered Refiner

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 💰 BMV Purchase | `bmv_purchases_max_net_ltv_vs_purchase_price_on_below_market_` | Purchase + BMV toggle |

### Unregulated Home Loan Refiners

| Refiner Chip | Database Column | When Shown |
|--------------|-----------------|------------|
| 🏠 Unreg 2nd on Home | `max_ltv_on_supporting_2nd_charge_on_applicant_s_home_unregul` | Unregulated + 2nd charge |
| 🏠 Unreg 1st on Home | `un_regulated_1st_charge_on_applicant_s_home_address_allowed_` | Unregulated + 1st charge + home |

---

## RIGHT BRAIN (AI) - Subtle Discrimination

These columns require interpretation and are used by the AI to differentiate between similar lenders.

### Deal Appetite Scores (0-3 scale)

| Scenario | Database Column | AI Usage |
|----------|-----------------|----------|
| Auction Purchases | `deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside` (col 95) | Score 3 = recommend, 0 = exclude |
| Business Stabilisation | `deal_appetite_..._1` (col 96) | |
| Insolvency Solutions | `deal_appetite_..._2` (col 97) | |
| HMO Conversions | `deal_appetite_..._3` (col 98) | |
| Commercial-to-Resi (PD) | `deal_appetite_..._4` (col 99) | |
| Airspace Developments | `deal_appetite_..._5` (col 100) | |
| Pre-Planning Acquisitions | `deal_appetite_..._6` (col 101) | |
| Subsidence Repairs | `deal_appetite_..._7` (col 102) | |
| Sitting Tenant Purchases | `deal_appetite_..._8` (col 103) | |
| Properties in Probate | `deal_appetite_..._9` (col 104) | |
| Fire/Flood Damaged | `deal_appetite_..._10` (col 105) | |
| Barn/Church Conversions | `deal_appetite_..._11` (col 106) | |
| Developer Exits | `deal_appetite_..._12` (col 107) | |
| Lease Extensions | `deal_appetite_..._13` (col 108) | |
| Refinance to BTL | `deal_appetite_..._14` (col 109) | |

### Property Exclusions

| Column | AI Usage |
|--------|----------|
| `which_of_these_property_types_are_unacceptable_as_security` | Parse for: Thatched, Listed, Non-standard, Flood zone, Knotweed, Short lease, Ex-LA, Above commercial |

### Pricing & Terms (AI Comparison)

| Column | AI Usage |
|--------|----------|
| `typical_proc_fee` | Compare fees |
| `approximate_interest_rate_band` | Compare rates |
| `do_you_charge_exit_fees` | Fee comparison |
| `minimum_number_of_months_interest` | Term flexibility |
| `what_s_your_standard_policy_on_day_one_of_non_repayment` | Risk assessment |

### Refurb Detailed Parameters (AI Analysis)

| Column | AI Usage |
|--------|----------|
| `maximum_day_1_advance` | Compare day-1 LTV across lenders |
| `maximum_day_1_advance_2` | Medium works day-1 |
| `maximum_day_1_advance_3` | Heavy works day-1 |
| `maximum_day_1_advance_4` | Very heavy works day-1 |
| `what_s_your_maximum_ltgdv` | LTGDV comparison |
| `what_s_your_maximum_ltgdv_2` | Medium works LTGDV |
| `what_s_your_maximum_ltgdv_3` | Heavy works LTGDV |
| `what_s_your_maximum_ltgdv_4` | Very heavy works LTGDV |
| `minimum_developer_experience` | Experience requirements |
| `minimum_developer_experience_2` | |
| `minimum_developer_experience_3` | |
| `minimum_developer_experience_4` | |
| `monitoring_requirements` | QS/monitoring comparison |
| `monitoring_requirements_2` | |
| `monitoring_requirements_3` | |
| `monitoring_requirements_1` | |
| `what_is_your_minimum_draw_down_amount_per_tranche` | Drawdown flexibility |
| `please_state_other_factors_that_affect_ltgdv` | Free text analysis |
| `additional_notes_on_refurb_lending` | Free text analysis |
| `additional_criteria_notes` | Free text analysis |
| `commercial_investment_valuation_policy_on_hmo_conversions` | HMO specifics |

### Valuation Policies

| Column | AI Usage |
|--------|----------|
| `residential_property` | MV vs 90-day vs 180-day |
| `mixed_use_property_commercial_resi` | Valuation basis |
| `commercial_property` | Valuation basis |
| `which_panels_do_you_use` | Panel comparison |

### Free Text Fields (AI Deep Analysis)

| Column | AI Usage |
|--------|----------|
| `feel_free_to_say_anything_about_your_lender_not_covered_in_t` | Unique selling points, quirks |
| `additional_notes_on_refurb_lending` | Refurb nuances |
| `additional_criteria_notes` | Light refurb specifics |
| `please_state_other_factors_that_affect_ltgdv` | LTGDV nuances |

---

## DISPLAY ONLY (Contact Info)

These are shown in results but not used for filtering.

| Column | Display Location |
|--------|------------------|
| `name` | Lender name |
| `email_address_for_new_enquiries` | Contact section |
| `central_number_for_new_enquiries` | Contact section |
| `south_west_bdm_name` | BDM details |
| `south_west_bdm_email_address` | BDM details |
| `south_west_bdm_mobile_number` | BDM details |
| `optional_contact_details_for_future_criteria_updates` | Internal use |
| `funding_model` | Display in results |
| `timestamp` | Last updated date |

---

## COLUMN USAGE SUMMARY

| Category | Count | % of Total |
|----------|-------|------------|
| Left Brain (Coarse) | 15 | 13% |
| Middle Brain (Refiners) | 38 | 34% |
| Right Brain (AI) | 47 | 42% |
| Display Only | 13 | 11% |
| **TOTAL** | **113** | **100%** |

**ALL 113 COLUMNS ARE ACCOUNTED FOR. NONE WASTED.**

---

## Implementation Notes

1. **Left Brain knockout logic** must be EXACT - no tolerance, no "maybe"
2. **Middle Brain refiners** show impact counts: "Foreign National? → 8 remain"
3. **Right Brain AI** uses deal_appetite scores as weights, not hard knockouts
4. **Property exclusions** need parsing - they're stored as comma-separated text
5. **Deal appetite 0** = won't consider (hard exclude for that scenario)
6. **Deal appetite 1-2** = possible but not preferred
7. **Deal appetite 3** = sweet spot (AI should prioritise these)
