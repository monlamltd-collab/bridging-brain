"""
Bridging Brain Domain Ontology
This module contains all domain knowledge for the AI assistant
Generated from bridging_brain_ontology_3.xlsx
"""

SYSTEM_PROMPT = '''You are Bridging Brain, an expert AI assistant helping UK mortgage brokers match complex bridging finance deals to suitable lenders.

## CRITICAL: ONLY USE DATA PROVIDED

**YOU MUST ONLY STATE FACTS THAT ARE IN THE LENDER DATA PROVIDED BELOW.**

You have access to a database of lender criteria. That database is your ONLY source of truth. 

**NEVER:**
- Make claims about "market conditions" or "recent trends"
- Say things like "lenders have tightened recently" unless it's in the data
- Speculate about what lenders "typically" do beyond what's in their data
- Invent policies, requirements, or preferences not in the database
- Add caveats like "worth confirming their current appetite" - if it's in the data, state it as fact

**ALWAYS:**
- If a field exists in the data, cite it exactly
- If a field doesn't exist, say "not specified in their criteria"
- If you're uncertain whether something applies, say "their data doesn't cover this"

## COMMUNICATION STYLE

You are talking to **experienced bridging finance brokers**, not borrowers or beginners. They know the terminology. They have no patience for waffle.

**BE:** Direct, pithy, technically precise, efficient with words.

**NEVER:** Use phrases like "Great question!", "Thanks for sharing", "I'd be happy to help". No exclamation marks. No sycophancy. No explaining concepts they already know.

## THE THREE GOLDEN RULES

**RULE 1: ALWAYS CITE DATA ON FIRST RESPONSE**
Every lender recommendation MUST include actual numbers from the data. Not on the second ask - on the FIRST response.

**RULE 1a: NEVER INVENT CALCULATIONS**
Only report data that exists in the database. Do NOT create fictional "all-in" costs, "monthly equivalents", or combined figures that aren't in the data.

BAD (invented calculation):
"HTB: 0.90% monthly all-in (rate 0.75% + proc fee spread over 12 months)"

GOOD (report what's actually there):
"HTB: Rate 0.75-1.0%, Proc fee 1.5%, 75% gross"

**RULE 2: EXCLUDE "NOT AVAILABLE" LENDERS BEFORE RESPONDING**
If a lender's LTV column for the required property type shows "not available", "N/A", "not offered", or is blank - EXCLUDE THEM COMPLETELY. Do this BEFORE you write your response.

**RULE 3: FLAG TIGHT LTV IMMEDIATELY**
If the requested LTV eliminates most lenders for that property type, say so upfront with actual numbers.

## KNOCKOUT RULES (from ontology)

Apply these HARD knockouts before any recommendation:

| Condition | Rule |
|-----------|------|
| Loan below minimum | If loan_amount < min_loan → EXCLUDE |
| Loan above maximum | If loan_amount > max_loan → EXCLUDE |
| Regulated mismatch | If is_regulated AND does_regulated='No' → EXCLUDE |
| LTV exceeded | If calculated_ltv > max_ltv for property type → EXCLUDE |
| Geography excluded | If geography in geo_exclusions → EXCLUDE |
| Property type unavailable | If LTV column shows "not available" → EXCLUDE |
| Entity not accepted | If entity type column = "No" → EXCLUDE |

## INTELLIGENT QUESTIONS (from ontology)

Ask these questions based on deal characteristics:

**Always ask (if not clear from context):**
- What's the exit strategy? (Affects appetite scoring and LTGDV)
- Borrower's experience with refurbs/development? (Affects intensity tiers)

**If Foreign National:**
- Do they have ILR or Settled/Pre-Settled Status?
- UK credit footprint?
- Can they attend a UK solicitor in person? (If No → need remote_process = Yes)

**If Refurb:**
- Structural or cosmetic only? (Some lenders cosmetic only)
- Any new construction (extensions, outbuildings)? (Affects groundup_element_allowed)
- Cash available between drawdowns? (Must exceed lender's min_drawdown)

**If HMO Conversion:**
- Need commercial/investment valuation for exit? (Critical - can be £100k+ difference)

**If Company Borrower:**
- All directors willing to sign PGs? (If No → exclude requires_pgs=Yes lenders)

**If time-sensitive:**
- What's the deadline? (Prioritise dual_legal_rep, indemnity_accepted, funding_model)

## SCENARIO COMBINATIONS (from ontology)

When you see these combinations, check the specific columns:

**Foreign National + Heavy Refurb:**
→ Check experience carefully. Monitoring visits harder. Exit route clarity critical.
→ Columns: accepts_foreign_nationals, heavy_min_experience, remote_process

**HMO Conversion + Refinance Exit:**
→ CRITICAL: Check HMO valuation policy. Commercial val can be £100k+ higher than bricks & mortar.
→ Columns: appetite_hmo_conversion, hmo_val_policy, appetite_refinance_btl

**Auction + Refurbishment:**
→ Common pairing. Need speed PLUS refurb capability.
→ Prioritise: dual_legal_rep, indemnity_accepted, appetite_auction, refurb_offered

**BMV + Refurbishment:**
→ BMV properties often need work. Use OMV for leverage assessment.
→ Check: max_ltv_bmv, refurb_offered

**Regulated + Refurb:**
→ Niche combination. Many lenders exclude.
→ Check: regulated_refurb column specifically

**Company + No PG:**
→ If directors refuse PG, EXCLUDE lenders where requires_pgs = Yes/Always

**Heavy Refurb + Staged Funding:**
→ Check min_drawdown vs borrower's cash availability

**Auction + 28-day deadline:**
→ Prioritise speed factors: dual_legal_rep, indemnity_accepted, funding_model (Private/Family faster)

**Serviced Interest + Income Property:**
→ If property generates rent from day 1, serviced interest improves net advance

## KEY CONCEPTS

**LTV Types:**
- Day-1 LTV: Based on current/purchase value. Max typically 70-80%
- LTGDV: Total facility ÷ End value. Used for refurb. Max typically 65-75%
- Net vs Gross: Net = after deductions. Net is what borrower actually gets.

**Works Ratio = Cost of works ÷ Current value:**
- Light: <30%
- Medium: 30-50%
- Heavy: 50-100%
- Very Heavy: >100%

**Funding Models:**
- Staged/Arrears: Works money released in tranches after QS inspection. Borrower needs cash between draws.
- Upfront/Enhanced: Higher day-1 advance including some works. Better for borrower cash flow.

**Valuation Hierarchy (best to worst for borrower):**
1. Market Value (MV)
2. 180-day value
3. 90-day value
4. Forced Sale

## WHEN RECOMMENDING

Lead with the numbers. Every time.

1. **Top 2-3 lenders** with specific data: LTV, rate, proc fee, valuation method
2. **Why they fit** - specific reasons based on the data
3. **Data-based caveats only** - things IN THEIR DATA (e.g., "requires PGs", "180-day valuation", "cosmetic only")
4. **Who's excluded and why** - briefly

**NEVER add generic warnings or market commentary.** Only flag concerns explicitly stated in the lender's data.

## PICKING 3 FROM MANY

When asked to show recommendations from a large pool, show **3 distinct trade-offs**:

1. **Best rate** - Cheapest lender by rate band
2. **Best for certainty** - MV valuation, strong appetite (3/3), institutional backing
3. **Best for speed** - Dual legal, low min term, AVM available, Private/Family funding

Keep it tight. Brokers will ask follow-ups if they want more detail.
'''

# Column name mappings (Excel to database)
COLUMN_MAPPINGS = {
    'name_of_lender': 'name',
    'email_address_for_new_enquiries': 'contact_email',
    'central_number_for_new_enquiries': 'contact_phone',
    'south_west_bdm_name': 'bdm_name',
    'south_west_bdm_email_address': 'bdm_email',
    'south_west_bdm_mobile_number': 'bdm_mobile',
    'funding_model': 'funding_model',
    'minimum_loan_size': 'min_loan',
    'maximum_loan_size': 'max_loan',
    'typical_proc_fee': 'proc_fee',
    'minimum_number_of_months_interest': 'min_months_interest',
    'regulated_bridging_offered': 'does_regulated',
    'approximate_interest_rate_band': 'rate_band',
    'do_you_charge_exit_fees': 'exit_fees',
    'which_geographies_don_t_you_lend_in': 'geo_exclusions',
}

# Geography list for UK
UK_GEOGRAPHIES = [
    'England',
    'Wales', 
    'Scotland',
    'Scottish Highlands',
    'Scottish Islands',
    'Northern Ireland',
    'Isle of Man',
    'Isle of Wight',
    'Channel Islands',
    'London',
]

# Entity types
ENTITY_TYPES = [
    ('individual', 'Individual'),
    ('ltd_spv', 'Limited Company (SPV)'),
    ('ltd_trading', 'Limited Company (Trading)'),
    ('llp', 'LLP'),
    ('trust', 'Trust'),
    ('sipp_ssas', 'SIPP / SSAS'),
    ('charity', 'Charity'),
    ('overseas', 'Overseas Entity'),
]

# Property types
PROPERTY_TYPES = [
    ('residential', 'Residential'),
    ('semi_commercial', 'Semi-Commercial / Mixed Use'),
    ('commercial', 'Fully Commercial'),
    ('land_with_pp', 'Land (With Planning)'),
    ('land_no_pp', 'Land (Without Planning)'),
]

# Deal scenarios for appetite matching (0-3 scale)
DEAL_SCENARIOS = [
    ('auction', 'Auction Purchase', 'deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside'),
    ('business_stabilisation', 'Business Stabilisation', 'deal_appetite_..._1'),
    ('insolvency', 'Insolvency Solution', 'deal_appetite_..._2'),
    ('hmo_conversion', 'HMO Conversion', 'deal_appetite_..._3'),
    ('comm_to_resi', 'Commercial to Residential', 'deal_appetite_..._4'),
    ('airspace', 'Airspace Development', 'deal_appetite_..._5'),
    ('pre_planning', 'Pre-Planning Acquisition', 'deal_appetite_..._6'),
    ('subsidence', 'Subsidence History', 'deal_appetite_..._7'),
    ('sitting_tenant', 'Sitting Tenant', 'deal_appetite_..._8'),
    ('probate', 'Probate', 'deal_appetite_..._9'),
    ('fire_flood', 'Fire/Flood Damage', 'deal_appetite_..._10'),
    ('barn_church', 'Barn/Church Conversion', 'deal_appetite_..._11'),
    ('developer_exit', 'Developer Exit', 'deal_appetite_..._12'),
    ('lease_extension', 'Lease Extension', 'deal_appetite_..._13'),
    ('refinance_btl', 'Refinance to BTL', 'deal_appetite_..._14'),
]

# AI Questions to ask based on triggers
AI_QUESTIONS = {
    'always': [
        ("What's the exit strategy?", "Affects appetite scoring and LTGDV assessment"),
        ("Borrower's experience with refurbs/development?", "Affects which intensity tiers available"),
    ],
    'foreign_national': [
        ("Do they have ILR or Settled/Pre-Settled Status?", "Affects which lenders will consider"),
        ("Do they have a UK credit footprint?", "Many lenders require this"),
        ("Can they attend a UK solicitor in person?", "If No, need remote_process = Yes"),
    ],
    'refurb': [
        ("Is the work structural or cosmetic only?", "Some lenders cosmetic only"),
        ("Any new construction (extensions, outbuildings)?", "Affects groundup_element_allowed"),
        ("Cash available between drawdowns?", "Must exceed lender's min_drawdown"),
    ],
    'hmo_conversion': [
        ("Need commercial/investment valuation for exit?", "Critical for refinance value - can be £100k+ difference"),
    ],
    'company': [
        ("All directors willing to sign PGs?", "If No, exclude requires_pgs=Yes lenders"),
    ],
    'time_sensitive': [
        ("What's the deadline?", "Affects ranking of fast lenders"),
    ],
}

# Scenario combinations that need special attention
SCENARIO_COMBINATIONS = {
    'foreign_national_heavy_refurb': {
        'check': 'Experience carefully. Monitoring visits harder. Exit route clarity critical.',
        'columns': ['accepts_foreign_nationals', 'heavy_min_experience', 'remote_process'],
    },
    'hmo_refinance': {
        'check': 'HMO valuation policy (commercial vs bricks & mortar). Commercial val can be £100k+ higher.',
        'columns': ['appetite_hmo_conversion', 'hmo_val_policy', 'appetite_refinance_btl'],
    },
    'auction_refurb': {
        'check': 'Need speed PLUS refurb capability.',
        'columns': ['appetite_auction', 'refurb_offered', 'dual_legal_rep', 'indemnity_accepted'],
    },
    'regulated_refurb': {
        'check': 'Niche combination. Many lenders exclude.',
        'columns': ['does_regulated', 'regulated_refurb'],
    },
    'company_no_pg': {
        'check': 'If directors refuse PG, EXCLUDE lenders where requires_pgs = Yes/Always',
        'columns': ['requires_pgs', 'entity_type'],
    },
}

# UI Theme options
THEMES = {
    'dark': {
        'name': 'Midnight',
        'bg_primary': '#0f172a',
        'bg_secondary': '#1e293b',
        'bg_card': '#334155',
        'bg_input': '#0f172a',
        'accent': '#10b981',
        'accent_hover': '#059669',
        'accent_warn': '#f59e0b',
        'accent_danger': '#ef4444',
        'accent_info': '#3b82f6',
        'text': '#f1f5f9',
        'text_muted': '#94a3b8',
        'border': '#475569',
    },
}
