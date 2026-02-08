#!/usr/bin/env python3
"""
Bridging Brain v4 - AI-Powered Lender Matching
Hybrid architecture: Structured knockouts + AI conversation
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
import os
import uuid
from datetime import datetime

# Try to import Anthropic - gracefully handle if not available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("WARNING: Anthropic SDK not installed. AI features will be disabled.")

from ontology import SYSTEM_PROMPT, THEMES, UK_GEOGRAPHIES, ENTITY_TYPES, PROPERTY_TYPES, DEAL_SCENARIOS

from datetime import datetime, timedelta

app = FastAPI(title="Bridging Brain v4")

DB_PATH = "lenders.db"

# Rate limiting - track queries per session
RATE_LIMIT = 30  # max queries per session per hour
rate_limit_store = {}  # session_id -> list of timestamps

def check_rate_limit(session_id: str) -> bool:
    """Check if session has exceeded rate limit. Returns True if OK, False if limited."""
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    
    if session_id not in rate_limit_store:
        rate_limit_store[session_id] = []
    
    # Clean old entries
    rate_limit_store[session_id] = [ts for ts in rate_limit_store[session_id] if ts > hour_ago]
    
    # Check limit
    if len(rate_limit_store[session_id]) >= RATE_LIMIT:
        return False
    
    # Add current request
    rate_limit_store[session_id].append(now)
    return True

# ============================================================================
# MODELS
# ============================================================================

class DealEssentials(BaseModel):
    """Core deal parameters for knockout filtering"""
    loan_amount: float
    purchase_price: Optional[float] = None
    market_value: float
    transaction_type: str = "purchase"
    input_mode: str = "loan"
    deposit_available: Optional[float] = None
    property_type: str = "residential"
    geography: str = "England"
    charge_position: str = "1st"
    loan_term_months: int = 12
    is_regulated: bool = False
    is_refurb: bool = False
    cost_of_works: Optional[float] = None
    gdv: Optional[float] = None
    borrower_cash_for_works: Optional[float] = None
    works_intensity: Optional[str] = None  # light, medium, heavy, very_heavy
    entity_type: str = "individual"
    scenarios: List[str] = []
    active_refiners: List[str] = []

class ChatMessage(BaseModel):
    """Single message in conversation"""
    session_id: str
    message: str
    deal_essentials: Optional[DealEssentials] = None

class FeedbackSubmission(BaseModel):
    """Broker feedback on a lender"""
    lender_name: str
    deal_type: str
    rating: int  # 1-5
    feedback_text: Optional[str] = None


class AIPDetails(BaseModel):
    """Details for AIP/Deal Presentation"""
    # Borrower info
    borrower_name: Optional[str] = None
    borrower_type: Optional[str] = None  # individual, company, partnership, trust
    is_homeowner: Optional[bool] = None
    assets_liabilities: Optional[str] = None  # brief A&L position
    
    # Property info
    property_address: Optional[str] = None
    additional_security_address: Optional[str] = None
    
    # Experience (for refurb)
    refurb_experience: Optional[str] = None  # none, 1-2, 3-5, 5+
    
    # Works (for refurb)
    works_schedule: Optional[str] = None  # brief description
    gdv_estimate: Optional[str] = None  # range e.g. "£450k-£500k"
    
    # Exit
    exit_strategy: Optional[str] = None  # sale, refinance, other
    exit_timeframe: Optional[str] = None  # e.g. "6-9 months"
    
    # Other
    additional_notes: Optional[str] = None
    urgency: Optional[str] = None  # e.g. "auction 28 days", "no rush"


class ContactLenderRequest(BaseModel):
    """Request to contact a lender"""
    lender_name: str
    deal_essentials: DealEssentials
    aip_details: Optional[AIPDetails] = None
    generate_email: bool = False

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_lenders() -> List[Dict[str, Any]]:
    """Get all lenders with all columns"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lenders ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_lender_columns() -> List[str]:
    """Get all column names from lenders table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(lenders)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

def save_conversation(session_id: str, role: str, content: str):
    """Save conversation message to database"""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history for a session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY created_at",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_feedback(lender_name: str, deal_type: str, rating: int, feedback_text: str = None):
    """Save broker feedback"""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO feedback (lender_name, deal_type, rating, feedback_text) VALUES (?, ?, ?, ?)",
        (lender_name, deal_type, rating, feedback_text)
    )
    conn.commit()
    conn.close()

def get_lender_feedback(lender_name: str = None) -> List[Dict]:
    """Get feedback, optionally filtered by lender"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if lender_name:
        cursor.execute(
            "SELECT * FROM feedback WHERE lender_name = ? ORDER BY created_at DESC",
            (lender_name,)
        )
    else:
        cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============================================================================
# NET LTV ESTIMATION
# ============================================================================

def estimate_net_from_gross(gross_ltv: float, rate_band: str, proc_fee: str, loan_term_months: int = 12, lender_min_months: str = '3') -> float:
    """
    Estimate net LTV from gross LTV based on retained interest and fees.
    
    Uses the GREATER of:
    - Borrower's requested loan term
    - Lender's minimum interest months
    
    Typical deductions:
    - Proc fee: 1-2.5%
    - Retained interest: (monthly rate × months retained)
    
    Returns estimated net LTV.
    """
    if not gross_ltv:
        return 0
    
    # Parse proc fee (default 2%)
    fee_pct = 2.0
    if proc_fee:
        proc_str = str(proc_fee).lower()
        if 'negotiable' in proc_str or 'no set' in proc_str:
            fee_pct = 1.5  # Assume competitive
        else:
            import re
            match = re.search(r'(\d+\.?\d*)', proc_str)
            if match:
                fee_pct = float(match.group(1))
    
    # Parse rate band to get midpoint monthly rate
    monthly_rate = 1.0  # default 1% per month
    if rate_band:
        rate_str = str(rate_band).lower()
        # Bands like "0.75-1.0%" or "0.5% - 0.75%"
        import re
        rates = re.findall(r'(\d+\.?\d*)', rate_str)
        if len(rates) >= 2:
            monthly_rate = (float(rates[0]) + float(rates[1])) / 2
        elif len(rates) == 1:
            monthly_rate = float(rates[0])
    
    # Parse lender's minimum months
    lender_min = 3
    if lender_min_months:
        months_str = str(lender_min_months).lower()
        if 'depends' in months_str:
            lender_min = 3
        else:
            import re
            match = re.search(r'(\d+)', months_str)
            if match:
                lender_min = int(match.group(1))
    
    # Use the GREATER of loan term or lender minimum
    # Interest is retained for the full loan term
    months_retained = max(loan_term_months, lender_min)
    
    # Calculate deduction
    # Interest retained as % of loan
    interest_deduction = monthly_rate * months_retained
    total_deduction = fee_pct + interest_deduction
    
    # Net LTV = Gross LTV × (1 - deduction%)
    # If gross is 75% and deductions are 14.2% (2% fee + 12×1.02%), 
    # net is roughly 75% × 0.858 = 64.4%
    
    net_ltv = gross_ltv * (1 - total_deduction / 100)
    
    return net_ltv


def check_net_ltv_shortfall(lender: dict, required_net_ltv: float, borrower_deposit: float, loan_term_months: int = 12, is_refurb: bool = False) -> dict:
    """
    Check if lender's estimated net LTV meets borrower's requirement.
    
    This is used internally only - we NEVER display estimated net figures to users.
    Purpose: knock out lenders way off, warn where tight, promote where comfortable.
    
    Returns dict with:
    - passes: bool
    - warning: bool
    - comfortable: bool (has headroom - for AI to promote)
    - message: str (never includes specific net figures)
    """
    result = {
        'passes': True,
        'warning': False,
        'comfortable': False,
        'message': None,
        'is_net_lender': False
    }
    
    # Detect NET lenders from various sources
    is_net = False
    
    # Check all LTV columns for "net" keyword
    net_keywords = ['net']
    for col in lender.keys():
        if 'ltv' in col.lower() or 'advance' in col.lower() or 'bmv' in col.lower():
            val_str = str(lender.get(col, '') or '').lower()
            if any(kw in val_str for kw in net_keywords):
                is_net = True
                result['is_net_lender'] = True
                break
    
    # Also check BMV column - high BMV LTV often indicates net-basis lender
    bmv_col = None
    for col in lender.keys():
        if 'bmv' in col.lower():
            bmv_val = str(lender.get(col, '') or '').lower()
            if bmv_val and 'n/a' not in bmv_val and 'not' not in bmv_val:
                # Has BMV capability - often indicates net-friendly
                bmv_ltv = parse_ltv(lender.get(col))
                if bmv_ltv and bmv_ltv >= 90:
                    # Very high BMV LTV suggests they work on net basis
                    is_net = True
                    result['is_net_lender'] = True
            break
    
    # Get gross LTV
    gross_ltv = None
    for col in lender.keys():
        if 'max_ltv' in col.lower() and 'residential' in col.lower() and '1st' in col.lower():
            gross_ltv = parse_ltv(lender.get(col))
            ltv_str = str(lender.get(col, '') or '').lower()
            if 'net' in ltv_str:
                is_net = True
                result['is_net_lender'] = True
            break
    
    if not gross_ltv:
        return result
    
    # Calculate estimated net (internal use only - never displayed)
    if is_net:
        estimated_net = gross_ltv
    else:
        rate_band = lender.get('approximate_interest_rate_band', '')
        proc_fee = lender.get('typical_proc_fee', '')
        lender_min_months = lender.get('minimum_number_of_months_interest', '')
        estimated_net = estimate_net_from_gross(gross_ltv, rate_band, proc_fee, loan_term_months, lender_min_months)
    
    # Compare to requirement
    if estimated_net:
        shortfall = required_net_ltv - estimated_net
        shortfall_pct = (shortfall / required_net_ltv) * 100 if required_net_ltv > 0 else 0
        
        if shortfall_pct > 5:
            # Way off - exclude
            result['passes'] = False
            result['message'] = f"Net advance likely insufficient for {loan_term_months}m term after fees & interest retention"
        elif shortfall_pct > 0:
            # Tight - warn
            result['warning'] = True
            result['message'] = f"Net advance may be tight for {loan_term_months}m term - verify with lender"
        elif shortfall_pct < -5:
            # Comfortable headroom - promote
            result['comfortable'] = True
    
    return result


# ============================================================================
# KNOCKOUT FILTER ENGINE
# ============================================================================

def apply_knockouts(lenders: List[Dict], essentials: DealEssentials) -> Dict[str, List[Dict]]:
    """
    Apply hard knockout rules to filter lenders.
    Returns dict with 'eligible' and 'excluded' lists.
    """
    eligible = []
    excluded = []
    
    # Calculate LTV
    ltv = (essentials.loan_amount / essentials.market_value * 100) if essentials.market_value > 0 else 0
    
    # Calculate works ratio if refurb
    works_ratio = 0
    if essentials.is_refurb and essentials.cost_of_works and essentials.market_value > 0:
        works_ratio = (essentials.cost_of_works / essentials.market_value) * 100
    
    for lender in lenders:
        exclusion_reasons = []
        
        # 1. Loan amount knockout
        min_loan = parse_number(lender.get('minimum_loan_size'))
        max_loan = parse_number(lender.get('maximum_loan_size'))
        
        if min_loan and essentials.loan_amount < min_loan:
            exclusion_reasons.append(f"Below minimum loan (£{min_loan:,.0f})")
        if max_loan and essentials.loan_amount > max_loan:
            exclusion_reasons.append(f"Above maximum loan (£{max_loan:,.0f})")
        
        # 2. Regulated knockout
        if essentials.is_regulated:
            does_reg = str(lender.get('regulated_bridging_offered', '')).lower()
            if 'no' in does_reg:
                exclusion_reasons.append("Doesn't offer regulated bridging")
        
        # 3. Geography knockout
        geo_exclusions = str(lender.get('which_geographies_don_t_you_lend_in', '') or '').lower()
        if essentials.geography.lower() in geo_exclusions:
            exclusion_reasons.append(f"Doesn't lend in {essentials.geography}")
        
        # 4. Refurb knockout
        if essentials.is_refurb:
            refurb_offered = str(lender.get('do_you_offer_bridging_finance_for_properties_requiring_refurbishment_works', '')).lower()
            if 'no' in refurb_offered:
                exclusion_reasons.append("Doesn't offer refurbishment bridging")
            
            # Check works ratio tier
            if works_ratio > 0:
                if works_ratio > 100:
                    very_heavy = str(lender.get('do_you_fund_very_heavy_works_over_100_cost_of_works_to_value', '')).lower()
                    if 'no' in very_heavy:
                        exclusion_reasons.append(f"Doesn't fund very heavy works (>{100}% ratio)")
                elif works_ratio > 50:
                    heavy = str(lender.get('do_you_fund_heavy_works_50_100_cost_of_works_to_value', '')).lower()
                    if 'no' in heavy:
                        exclusion_reasons.append(f"Doesn't fund heavy works (50-100% ratio)")
                elif works_ratio > 30:
                    medium = str(lender.get('do_you_fund_medium_works_30_50_cost_of_works_to_value', '')).lower()
                    if 'no' in medium:
                        exclusion_reasons.append(f"Doesn't fund medium works (30-50% ratio)")
        
        # 5. Entity type knockout
        entity_knockouts = {
            'charity': 'do_you_lend_to_charities',
            'trust': 'do_you_lend_to_trusts',
            'llp': 'do_you_lend_to_limited_liability_partnerships',
            'sipp_ssas': 'can_you_lend_to_sipps_ssas_pensions',
            'overseas': 'do_you_lend_to_overseas_entities',
        }
        
        if essentials.entity_type in entity_knockouts:
            col = entity_knockouts[essentials.entity_type]
            # Find matching column (fuzzy match on column names)
            for lender_col in lender.keys():
                if col.replace('_', '') in lender_col.replace('_', '').lower():
                    val = str(lender.get(lender_col, '')).lower()
                    if 'no' in val and 'yes' not in val:
                        exclusion_reasons.append(f"Doesn't lend to {essentials.entity_type}")
                    break
        
        # 6. Property type / charge position availability check
        ltv_col = get_ltv_column(essentials.property_type, essentials.is_regulated, essentials.charge_position)
        max_ltv = None
        ltv_raw_value = None
        for lender_col in lender.keys():
            if ltv_col.lower() in lender_col.lower():
                ltv_raw_value = str(lender.get(lender_col, '') or '').lower().strip()
                max_ltv = parse_ltv(lender.get(lender_col))
                break
        
        # Check if lender doesn't offer this charge position / property type at all
        if ltv_raw_value and ('not available' in ltv_raw_value or 'n/a' in ltv_raw_value or ltv_raw_value == '' or "don't lend" in ltv_raw_value or "dont lend" in ltv_raw_value):
            # More specific message based on charge position or property type
            if essentials.property_type == 'land_with_pp':
                exclusion_reasons.append("Doesn't lend on land with planning")
            elif essentials.property_type == 'land_no_pp':
                exclusion_reasons.append("Doesn't lend on land without planning")
            elif essentials.charge_position == '2nd_standalone':
                exclusion_reasons.append("Doesn't offer standalone 2nd charge")
            elif essentials.charge_position == '2nd_supporting':
                exclusion_reasons.append("Doesn't offer supporting 2nd charge")
            elif essentials.charge_position == 'equitable':
                exclusion_reasons.append("Doesn't offer equitable charges")
            else:
                exclusion_reasons.append(f"Doesn't lend on {essentials.property_type.replace('_', ' ')}")
        
        # 7. NET LTV check - this is the PRIMARY leverage filter
        # We estimate net LTV (after fees & retained interest) and compare to requirement
        # No separate gross knockout - net calculation handles everything
        net_ltv_warning = None
        net_ltv_comfortable = False
        net_check_result = None
        
        if not exclusion_reasons and max_ltv:
            net_check_result = check_net_ltv_shortfall(
                lender, 
                ltv,  # Required LTV is what borrower needs
                essentials.deposit_available or 0,
                essentials.loan_term_months,
                essentials.is_refurb
            )
            
            if not net_check_result['passes']:
                exclusion_reasons.append(net_check_result['message'])
            elif net_check_result['warning']:
                net_ltv_warning = net_check_result['message']
            elif net_check_result['comfortable']:
                net_ltv_comfortable = True
        
        # Categorise
        lender_result = {
            **lender,
            'exclusion_reasons': exclusion_reasons,
            'calculated_ltv': ltv,
            'works_ratio': works_ratio,
            'max_gross_ltv': max_ltv,  # Store for leverage hints
        }
        
        # Add net LTV flags if applicable (no specific figures - just guidance)
        if net_ltv_warning:
            lender_result['net_ltv_warning'] = net_ltv_warning
        if net_ltv_comfortable:
            lender_result['net_ltv_comfortable'] = True
        if net_check_result:
            lender_result['net_check_result'] = net_check_result
        
        if exclusion_reasons:
            excluded.append(lender_result)
        else:
            eligible.append(lender_result)
    
    # Generate leverage hints if LTV is tight
    leverage_hints = generate_leverage_hints(lenders, essentials, ltv, eligible, excluded)
    
    # Generate additional security hints if using non-1st charge or if LTV tight
    security_hints = generate_security_hints(lenders, essentials, ltv, eligible, excluded)
    
    return {
        'eligible': eligible,
        'excluded': excluded,
        'summary': {
            'total': len(lenders),
            'eligible': len(eligible),
            'excluded': len(excluded),
            'ltv': ltv,
            'works_ratio': works_ratio,
        },
        'leverage_hints': leverage_hints,
        'security_hints': security_hints
    }


def generate_leverage_hints(lenders: List[Dict], essentials: DealEssentials, ltv: float, eligible: List[Dict], excluded: List[Dict]) -> Dict:
    """
    Analyze lenders with tight/short net LTV to find levers that could help.
    Only fires when there's a problem to solve.
    
    7 Levers:
    1. Shorter term - less retained interest
    2. Serviced interest - pay monthly, gross ≈ net
    3. Rolled interest (refurb) - interest against GDV
    4. Light refurb - higher day-1 LTV
    5. BMV purchase - higher LTV vs purchase price
    6. Additional security - 2nd charge boosts leverage
    7. Lower rate lender - less interest retained
    """
    hints = {
        'shorter_term': [],
        'serviced_interest': [],
        'light_refurb': [],
        'bmv_purchase': [],
        'additional_security': [],
        'lower_rate_lender': [],
        'summary': None,
        'has_hints': False
    }
    
    loan_term = essentials.loan_term_months
    
    # Collect lenders that are tight or excluded for net LTV reasons
    problem_lenders = []
    for lender in excluded:
        reasons = lender.get('exclusion_reasons', [])
        if any('net' in r.lower() or 'insufficient' in r.lower() or 'tight' in r.lower() for r in reasons):
            problem_lenders.append(lender)
    
    # Also check eligible lenders with warnings
    for lender in eligible:
        if lender.get('net_ltv_warning'):
            problem_lenders.append(lender)
    
    if not problem_lenders:
        return hints
    
    for lender in problem_lenders:
        name = lender.get('name', '')
        rate_band = lender.get('approximate_interest_rate_band', '')
        proc_fee = lender.get('typical_proc_fee', '')
        lender_min_months = lender.get('minimum_number_of_months_interest', '')
        gross_ltv = lender.get('max_gross_ltv') or parse_ltv(lender.get('max_ltv_1st_charge_residential_investment_property', ''))
        
        if not gross_ltv:
            continue
        
        # 1. SHORTER TERM - would a shorter term help?
        if loan_term > 6:
            shorter_terms = [t for t in [6, 9] if t < loan_term]
            for shorter in shorter_terms:
                net_at_shorter = estimate_net_from_gross(gross_ltv, rate_band, proc_fee, shorter, lender_min_months)
                if net_at_shorter and net_at_shorter >= ltv:
                    hints['shorter_term'].append({
                        'name': name,
                        'current_term': loan_term,
                        'suggested_term': shorter,
                        'note': f'{shorter}m term could work'
                    })
                    break
        
        # 2. SERVICED INTEREST - would paying monthly help?
        serviced = str(lender.get('serviced_interest_allowed', '') or '').lower()
        if 'yes' in serviced:
            # With serviced interest, no interest retention - just proc fee deducted
            net_with_serviced = gross_ltv * (1 - parse_proc_fee(proc_fee) / 100)
            if net_with_serviced >= ltv:
                hints['serviced_interest'].append({
                    'name': name,
                    'note': 'Serviced interest available - pay monthly instead of retaining'
                })
        
        # 3. LIGHT REFURB - higher day-1 LTV available?
        if not essentials.is_refurb:
            day1_advance = lender.get('maximum_day_1_advance', '') or lender.get('maximum_day_1_ltv', '')
            if day1_advance:
                refurb_gross = parse_ltv(day1_advance)
                if refurb_gross and refurb_gross > gross_ltv:
                    # Check if net refurb LTV would work
                    is_net_refurb = 'net' in str(day1_advance).lower()
                    if is_net_refurb:
                        net_refurb = refurb_gross
                    else:
                        net_refurb = estimate_net_from_gross(refurb_gross, rate_band, proc_fee, loan_term, lender_min_months)
                    
                    if net_refurb and net_refurb >= ltv:
                        hints['light_refurb'].append({
                            'name': name,
                            'note': 'Light refurb unlocks higher day-1 advance'
                        })
        
        # 4. BMV PURCHASE - if applicable, higher LTV vs purchase price?
        bmv_ltv = None
        for col in lender.keys():
            if 'bmv' in col.lower():
                bmv_ltv = parse_ltv(lender.get(col))
                break
        
        if bmv_ltv and bmv_ltv > gross_ltv:
            hints['bmv_purchase'].append({
                'name': name,
                'note': 'BMV scenario could unlock higher LTV vs purchase price'
            })
        
        # 5. ADDITIONAL SECURITY - does lender offer supporting 2nd?
        if essentials.charge_position == '1st':
            supporting_2nd = None
            for col in lender.keys():
                if 'supporting' in col.lower() and '2nd' in col.lower():
                    val = str(lender.get(col, '')).lower()
                    if val and 'not available' not in val and 'n/a' not in val:
                        supporting_2nd = parse_ltv(lender.get(col))
                    break
            
            if supporting_2nd:
                hints['additional_security'].append({
                    'name': name,
                    'note': 'Accepts supporting 2nd charge for additional leverage'
                })
    
    # 6. LOWER RATE LENDER - find lenders with better rates among excluded
    # Compare rates of problem lenders to find if switching helps
    rate_comparison = []
    for lender in problem_lenders:
        rate_band = lender.get('approximate_interest_rate_band', '')
        avg_rate = parse_rate_band_midpoint(rate_band)
        if avg_rate:
            rate_comparison.append((lender.get('name', ''), avg_rate, lender))
    
    if len(rate_comparison) > 1:
        rate_comparison.sort(key=lambda x: x[1])
        lowest_name, lowest_rate, lowest_lender = rate_comparison[0]
        highest_name, highest_rate, _ = rate_comparison[-1]
        
        if highest_rate - lowest_rate >= 0.2:  # Meaningful difference
            # Check if lowest rate lender would work
            gross = lowest_lender.get('max_gross_ltv') or parse_ltv(lowest_lender.get('max_ltv_1st_charge_residential_investment_property', ''))
            if gross:
                net_at_lower = estimate_net_from_gross(
                    gross, 
                    lowest_lender.get('approximate_interest_rate_band', ''),
                    lowest_lender.get('typical_proc_fee', ''),
                    loan_term,
                    lowest_lender.get('minimum_number_of_months_interest', '')
                )
                if net_at_lower and net_at_lower >= ltv:
                    hints['lower_rate_lender'].append({
                        'name': lowest_name,
                        'note': 'Lower rate means less retained interest'
                    })
    
    # Generate summary
    summary_parts = []
    if hints['shorter_term']:
        summary_parts.append(f"Shorter term could help with {hints['shorter_term'][0]['name']}")
    if hints['serviced_interest']:
        names = [h['name'] for h in hints['serviced_interest'][:2]]
        summary_parts.append(f"Serviced interest available: {', '.join(names)}")
    if hints['light_refurb']:
        names = [h['name'] for h in hints['light_refurb'][:2]]
        summary_parts.append(f"Light refurb unlocks: {', '.join(names)}")
    if hints['bmv_purchase']:
        summary_parts.append("BMV scenario could improve leverage")
    if hints['additional_security']:
        summary_parts.append("Additional security option available")
    if hints['lower_rate_lender']:
        summary_parts.append(f"Lower rate lender: {hints['lower_rate_lender'][0]['name']}")
    
    if summary_parts:
        hints['summary'] = "; ".join(summary_parts)
        hints['has_hints'] = True
    
    return hints


def parse_proc_fee(proc_fee_str: str) -> float:
    """Parse proc fee string to percentage"""
    if not proc_fee_str:
        return 2.0
    proc_str = str(proc_fee_str).lower()
    if 'negotiable' in proc_str or 'no set' in proc_str:
        return 1.5
    import re
    match = re.search(r'(\d+\.?\d*)', proc_str)
    if match:
        return float(match.group(1))
    return 2.0


def parse_rate_band_midpoint(rate_band: str) -> float:
    """Parse rate band string to midpoint monthly rate"""
    if not rate_band:
        return None
    rate_str = str(rate_band).lower()
    import re
    rates = re.findall(r'(\d+\.?\d*)', rate_str)
    if len(rates) >= 2:
        return (float(rates[0]) + float(rates[1])) / 2
    elif len(rates) == 1:
        return float(rates[0])
    return None


def generate_security_hints(lenders: List[Dict], essentials: DealEssentials, ltv: float, eligible: List[Dict], excluded: List[Dict]) -> Dict:
    """
    Analyze if additional security (2nd charge, equitable) could help.
    Only relevant when:
    - LTV is tight (>70%) and borrower might have other property
    - OR current lender count is low
    """
    hints = {
        'additional_security_helps': False,
        'supporting_2nd_count': 0,
        'equitable_count': 0,
        'message': None
    }
    
    # Only suggest if:
    # 1. Using 1st charge AND LTV is tight OR few lenders match
    # 2. Not already using 2nd/equitable
    if essentials.charge_position != '1st':
        return hints
    
    if ltv <= 70 and len(eligible) >= 20:
        return hints
    
    # Count how many lenders offer supporting 2nd charge
    supporting_2nd_count = 0
    equitable_count = 0
    
    for lender in lenders:
        # Check supporting 2nd
        for col in lender.keys():
            if 'supporting_2nd_charge' in col.lower() and 'home' not in col.lower():
                val = str(lender.get(col, '') or '').lower()
                if val and 'not available' not in val and 'n/a' not in val and val != '':
                    supporting_2nd_count += 1
                    break
        
        # Check equitable (supporting)
        for col in lender.keys():
            if 'supporting_equitable' in col.lower():
                val = str(lender.get(col, '') or '').lower()
                if val and 'not available' not in val and 'n/a' not in val and val != '':
                    equitable_count += 1
                    break
    
    hints['supporting_2nd_count'] = supporting_2nd_count
    hints['equitable_count'] = equitable_count
    
    # Generate message if additional security could unlock more lenders
    if ltv > 70:
        hints['additional_security_helps'] = True
        hints['message'] = f"If borrower has other property: supporting 2nd charge ({supporting_2nd_count} lenders) or equitable charge ({equitable_count} lenders) could reduce effective LTV"
    elif len(eligible) < 10:
        hints['additional_security_helps'] = True
        hints['message'] = f"Additional security could expand options: {supporting_2nd_count} lenders offer supporting 2nd charge"
    
    return hints


def get_ltv_column(property_type: str, is_regulated: bool, charge_position: str = "1st") -> str:
    """Get the appropriate LTV column name based on property type and charge position"""
    if is_regulated:
        return 'max_ltv_regulated'
    
    # Handle land types first (no charge variation)
    if property_type == 'land_with_pp':
        return 'land_with_planning'
    if property_type == 'land_no_pp':
        return 'land_without_planning'
    
    # Handle commercial/semi-commercial (no charge variation in our data)
    if property_type == 'commercial':
        return 'fully_commercial'
    if property_type == 'semi_commercial':
        return 'semi_commercial_mixed_use'
    
    # Residential with charge position variations
    if property_type == 'residential':
        charge_mapping = {
            '1st': '1st_charge_residential',
            '2nd_supporting': 'supporting_2nd_charge_residential',
            '2nd_standalone': 'standalone_2nd_charge_resi',
            'equitable': 'equitable_charge',  # Will check both supporting and standalone
        }
        return charge_mapping.get(charge_position, '1st_charge_residential')
    
    return '1st_charge_residential'

def parse_number(val) -> Optional[float]:
    """Parse a number from various formats"""
    if val is None:
        return None
    val = str(val).replace('£', '').replace(',', '').replace('k', '000').replace('K', '000')
    val = val.replace('m', '000000').replace('M', '000000')
    try:
        # Extract first number found
        import re
        match = re.search(r'[\d.]+', val)
        if match:
            return float(match.group())
    except:
        pass
    return None

def parse_ltv(val) -> Optional[float]:
    """Parse LTV percentage from various formats"""
    if val is None:
        return None
    val = str(val).lower().replace('%', '').replace('gross', '').replace('net', '')
    try:
        import re
        match = re.search(r'[\d.]+', val)
        if match:
            return float(match.group())
    except:
        pass
    return None

# ============================================================================
# AI CHAT ENGINE
# ============================================================================

def get_ai_client():
    """Get Anthropic client"""
    if not ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

def build_lender_context(eligible_lenders: List[Dict], excluded_count: int, summary: Dict, deal_essentials: dict = None) -> str:
    """Build context string with lender data for AI"""
    
    # First, clearly state what deal info has been provided
    context = """## DEAL ESSENTIALS ALREADY PROVIDED (DO NOT ASK FOR THESE AGAIN)

"""
    if deal_essentials:
        input_mode = deal_essentials.get('input_mode', 'loan')
        
        if input_mode == 'deposit':
            context += f"- **Input Mode**: Deposit-driven (working backwards from available deposit)\n"
            context += f"- **Deposit Available**: £{deal_essentials.get('deposit_available', 0):,.0f}\n"
            context += f"- **Calculated Loan Needed**: £{deal_essentials.get('loan_amount', 0):,.0f}\n"
        else:
            context += f"- **Loan Amount**: £{deal_essentials.get('loan_amount', 0):,.0f}\n"
        
        context += f"- **Transaction Type**: {deal_essentials.get('transaction_type', 'purchase').title()}\n"
        
        if deal_essentials.get('purchase_price'):
            context += f"- **Purchase Price**: £{deal_essentials.get('purchase_price'):,.0f}\n"
        
        context += f"- **Market Value**: £{deal_essentials.get('market_value', 0):,.0f}\n"
        context += f"- **Loan Term**: {deal_essentials.get('loan_term_months', 12)} months\n"
        context += f"- **Property Type**: {deal_essentials.get('property_type', 'residential').replace('_', ' ').title()}\n"
        context += f"- **Geography**: {deal_essentials.get('geography', 'England')}\n"
        context += f"- **Entity Type**: {deal_essentials.get('entity_type', 'individual').replace('_', ' ').title()}\n"
        context += f"- **Regulated**: {'Yes' if deal_essentials.get('is_regulated') else 'No'}\n"
        context += f"- **Refurbishment**: {'Yes' if deal_essentials.get('is_refurb') else 'No'}\n"
        
        if deal_essentials.get('is_refurb') and deal_essentials.get('cost_of_works'):
            context += f"- **Cost of Works**: £{deal_essentials.get('cost_of_works'):,.0f}\n"
    
    context += f"""
## Current Filtering Results

- **Calculated LTV**: {summary.get('ltv', 0):.1f}%
- **Works Ratio**: {summary.get('works_ratio', 0):.1f}%
- **Eligible Lenders**: {len(eligible_lenders)}
- **Excluded (hard knockouts)**: {excluded_count}

## Eligible Lenders Data

"""
    for lender in eligible_lenders[:30]:  # Limit to top 30 to manage context size
        context += f"### {lender.get('name', 'Unknown')}\n"
        
        # Key fields to include
        key_fields = [
            ('rate_band', 'approximate_interest_rate_band'),
            ('proc_fee', 'typical_proc_fee'),
            ('min_loan', 'minimum_loan_size'),
            ('max_loan', 'maximum_loan_size'),
            ('min_months', 'minimum_number_of_months_interest'),
            ('exit_fees', 'do_you_charge_exit_fees'),
            ('regulated', 'regulated_bridging_offered'),
            ('serviced_interest', 'serviced_interest_allowed'),
            ('funding_model', 'funding_model'),
            ('dual_legal', 'dual_legal_rep'),
            ('indemnity', 'indemnity'),
            ('foreign_nationals', 'can_you_lend_to_foreign_nationals'),
            ('expats', 'can_you_lend_to_expats'),
            ('geo_exclusions', 'which_geographies_don_t_you_lend_in'),
        ]
        
        # Always include all LTV columns so AI can see what's available and what's not
        ltv_fields = [
            ('LTV_residential_1st', '1st_charge_residential'),
            ('LTV_semi_commercial', 'semi_commercial_mixed_use'),
            ('LTV_commercial', 'fully_commercial'),
            ('LTV_land_no_planning', 'land_without_planning'),
            ('LTV_land_with_planning', 'land_with_planning'),
        ]
        
        # Add LTV fields - include even if "not available" so AI knows
        for display_name, col_pattern in ltv_fields:
            for col in lender.keys():
                if col_pattern.replace('_', '') in col.replace('_', '').lower():
                    val = lender.get(col)
                    val_str = str(val).lower().strip() if val else ''
                    if val_str and val_str not in ('nan', 'none', ''):
                        context += f"- {display_name}: {val}\n"
                    else:
                        context += f"- {display_name}: NOT AVAILABLE\n"
                    break
        
        # Add valuation methodology columns
        for col in lender.keys():
            if 'mixed_use' in col.lower() or 'semi_commercial' in col.lower() or 'commercial_property' in col.lower():
                if 'ltv' not in col.lower():  # Skip LTV columns, get valuation policy
                    val = lender.get(col)
                    if val and str(val).lower() not in ('nan', 'none', ''):
                        context += f"- valuation_policy ({col}): {val}\n"
        
        for display_name, col_pattern in key_fields:
            for col in lender.keys():
                if col_pattern.replace('_', '') in col.replace('_', '').lower():
                    val = lender.get(col)
                    if val and str(val).lower() not in ('nan', 'none', ''):
                        context += f"- {display_name}: {val}\n"
                    break
        
        # Include lender notes if present
        for col in lender.keys():
            if 'feel_free' in col.lower() or 'lender_notes' in col.lower():
                notes = lender.get(col)
                if notes and str(notes).lower() not in ('nan', 'none', ''):
                    context += f"- Notes: {str(notes)[:500]}\n"
                break
        
        # Include deal appetite scores if active refiners selected
        if deal_essentials and deal_essentials.get('active_refiners'):
            active_refiners = deal_essentials.get('active_refiners', [])
            appetite_mapping = {
                'auction': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside', 'Auction'),
                'business_stabilisation': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_1', 'Business Stabilisation'),
                'insolvency': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_2', 'Insolvency'),
                'hmo': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_3', 'HMO Conversion'),
                'comm_to_resi': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_4', 'Commercial to Resi'),
                'airspace': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_5', 'Airspace Development'),
                'pre_planning': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_6', 'Pre-Planning'),
                'subsidence': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_7', 'Subsidence'),
                'sitting_tenant': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_8', 'Sitting Tenant'),
                'probate': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_9', 'Probate'),
                'fire_flood': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_10', 'Fire/Flood Damaged'),
                'barn_church': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_11', 'Barn/Church Conversion'),
                'developer_exit': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_12', 'Developer Exit'),
                'lease_extension': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_13', 'Lease Extension'),
                'refi_to_btl': ('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_14', 'Refinance to BTL'),
            }
            
            appetite_notes = []
            for refiner in active_refiners:
                if refiner in appetite_mapping:
                    col, label = appetite_mapping[refiner]
                    score = int(str(lender.get(col, '0')).strip() or 0)
                    if score == 0:
                        appetite_notes.append(f"{label}: ❌ WON'T CONSIDER")
                    elif score == 1:
                        appetite_notes.append(f"{label}: ⚠️ LOW APPETITE (discuss with BDM)")
                    elif score == 2:
                        appetite_notes.append(f"{label}: ✓ Will consider")
                    elif score == 3:
                        appetite_notes.append(f"{label}: ⭐ STRONG APPETITE")
            
            if appetite_notes:
                context += "- **Deal Appetite**:\n"
                for note in appetite_notes:
                    context += f"  - {note}\n"
        
        # Include net LTV warning if present
        if lender.get('net_ltv_warning'):
            context += f"- ⚠️ **Net LTV Warning**: {lender.get('net_ltv_warning')}\n"
        
        # Include comfortable flag if present (for AI to promote)
        if lender.get('net_ltv_comfortable'):
            context += f"- ✅ **Net LTV Headroom**: Comfortable margin for this term length\n"
        
        # Include contact details
        contact_info = get_lender_contact(lender)
        if contact_info:
            context += f"- **Contact**: {contact_info['bdm_name']} | {contact_info['email']} | {contact_info['phone']}\n"
        
        context += "\n"
    
    return context


def get_lender_contact(lender: Dict) -> Dict:
    """Extract contact details from lender record"""
    contact = {
        'bdm_name': lender.get('south_west_bdm_name', ''),
        'bdm_email': lender.get('south_west_bdm_email_address', ''),
        'bdm_mobile': lender.get('south_west_bdm_mobile_number', ''),
        'email': lender.get('email_address_for_new_enquiries', ''),
        'phone': lender.get('central_number_for_new_enquiries', ''),
    }
    
    # Clean up empty/nan values
    for key in contact:
        val = contact[key]
        if not val or str(val).lower() in ('nan', 'none', 'n/a', ''):
            contact[key] = ''
        else:
            contact[key] = str(val).strip()
    
    return contact

def chat_with_ai(session_id: str, user_message: str, deal_essentials: Optional[DealEssentials] = None) -> str:
    """Send message to AI and get response"""
    client = get_ai_client()
    
    if not client:
        return "AI features require an Anthropic API key. Please set the ANTHROPIC_API_KEY environment variable. In the meantime, I can show you the filtered lender list based on your criteria."
    
    # Get conversation history
    history = get_conversation_history(session_id)
    
    # Build context if we have deal essentials
    lender_context = ""
    if deal_essentials:
        lenders = get_all_lenders()
        filter_result = apply_knockouts(lenders, deal_essentials)
        lender_context = build_lender_context(
            filter_result['eligible'],
            len(filter_result['excluded']),
            filter_result['summary'],
            deal_essentials.dict() if hasattr(deal_essentials, 'dict') else deal_essentials
        )
    
    # Get any feedback for context
    feedback = get_lender_feedback()
    feedback_context = ""
    if feedback:
        feedback_context = "\n## Previous Broker Feedback\n"
        for fb in feedback[:10]:  # Last 10 feedback items
            feedback_context += f"- {fb.get('lender_name')}: {fb.get('rating')}/5 stars"
            if fb.get('feedback_text'):
                feedback_context += f" - \"{fb.get('feedback_text')}\""
            feedback_context += "\n"
    
    # Build messages for API
    system = SYSTEM_PROMPT + "\n\n" + lender_context + feedback_context
    
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    
    # Call Claude
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=messages
        )
        
        assistant_message = response.content[0].text
        
        # Save conversation
        save_conversation(session_id, "user", user_message)
        save_conversation(session_id, "assistant", assistant_message)
        
        return assistant_message
        
    except Exception as e:
        return f"I encountered an error communicating with the AI service: {str(e)}. Please try again or check your API key."

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def index():
    return FileResponse("index.html")

@app.get("/script.js")
async def script():
    return FileResponse("script.js")

@app.get("/health")
async def health():
    try:
        lenders = get_all_lenders()
        ai_available = get_ai_client() is not None
        return {
            "status": "healthy",
            "database": "connected",
            "lender_count": len(lenders),
            "ai_available": ai_available
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/config")
async def get_config():
    """Get configuration data for frontend"""
    return {
        "geographies": UK_GEOGRAPHIES,
        "entity_types": ENTITY_TYPES,
        "property_types": PROPERTY_TYPES,
        "deal_scenarios": DEAL_SCENARIOS,
        "themes": THEMES,
    }

@app.get("/api/lenders")
async def list_lenders():
    """Get all lenders"""
    lenders = get_all_lenders()
    return {"count": len(lenders), "lenders": lenders}

@app.post("/api/filter")
async def filter_lenders(essentials: DealEssentials):
    """Apply knockout filters and return eligible lenders"""
    lenders = get_all_lenders()
    result = apply_knockouts(lenders, essentials)
    return result

@app.post("/api/filter-options")
async def get_filter_options(essentials: DealEssentials):
    """Calculate which additional filters would narrow the results and by how much"""
    lenders = get_all_lenders()
    base_result = apply_knockouts(lenders, essentials)
    base_count = len(base_result['eligible'])
    
    # Define filter options to check
    filter_checks = {
        'speed_critical': {
            'label': 'Speed critical?',
            'icon': '⚡',
            'check': lambda l: (
                str(l.get('dual_legal_rep', '')).lower() in ('yes', 'true') or
                str(l.get('minimum_number_of_months_interest', '')).strip() in ('1', '1 month', 'None')
            )
        },
        'foreign_national': {
            'label': 'Foreign national?',
            'icon': '🌍',
            'check': lambda l: 'yes' in str(l.get('can_you_lend_to_foreign_nationals', '')).lower()
        },
        'adverse_credit': {
            'label': 'Adverse credit?',
            'icon': '⚠️',
            'check': lambda l: 'yes' in str(l.get('can_you_lend_to_borrowers_with_adverse_credit_ccjs_defaults', '')).lower()
        },
        'works_funding': {
            'label': 'Need works funding?',
            'icon': '🔨',
            'check': lambda l: 'yes' in str(l.get('do_you_also_offer_arrears_staged_funding_for_refurbishments', '')).lower()
        },
        'serviced_interest': {
            'label': 'Can service interest?',
            'icon': '💰',
            'check': lambda l: 'yes' in str(l.get('serviced_interest_allowed', '')).lower()
        },
        'dual_legal': {
            'label': 'Dual legal rep?',
            'icon': '⚖️',
            'check': lambda l: 'yes' in str(l.get('dual_legal_rep', '')).lower()
        }
    }
    
    options = []
    for key, config in filter_checks.items():
        # Count how many eligible lenders pass this filter
        filtered_count = sum(1 for l in base_result['eligible'] if config['check'](l))
        
        # Only show if it actually narrows (and doesn't eliminate all)
        if 0 < filtered_count < base_count:
            options.append({
                'key': key,
                'label': config['label'],
                'icon': config['icon'],
                'remaining': filtered_count,
                'reduction': base_count - filtered_count
            })
    
    # Sort by most impactful (biggest reduction first)
    options.sort(key=lambda x: x['reduction'], reverse=True)
    
    return {
        'base_count': base_count,
        'options': options[:5]  # Top 5 most impactful filters
    }


@app.post("/api/refiner-options")
async def get_refiner_options(essentials: DealEssentials):
    """Get dynamic refiner chips organized by category based on current deal and active refiners"""
    lenders = get_all_lenders()
    base_result = apply_knockouts(lenders, essentials)
    eligible = base_result['eligible']
    
    # Apply active refiners to get current filtered list
    active_refiners = set(essentials.active_refiners or [])
    current_eligible = apply_refiners(eligible, active_refiners)
    current_count = len(current_eligible)
    
    def count_if_added(check_fn):
        """Count how many would remain if this refiner was added to current selection"""
        return sum(1 for l in current_eligible if check_fn(l))
    
    # Define all refiner checks
    refiner_checks = {
        # BORROWER REFINERS
        'foreign_national': {
            'category': 'borrower',
            'icon': '🌍', 
            'label': 'Foreign National',
            'check': lambda l: 'yes' in str(l.get('can_you_lend_to_foreign_nationals', '')).lower() or 
                              'only' in str(l.get('can_you_lend_to_foreign_nationals', '')).lower()
        },
        'expat': {
            'category': 'borrower',
            'icon': '🛫', 
            'label': 'Expat',
            'check': lambda l: 'yes' in str(l.get('can_you_lend_to_expats', '')).lower() or
                              'only' in str(l.get('can_you_lend_to_expats', '')).lower()
        },
        'adverse_credit': {
            'category': 'borrower',
            'icon': '⚠️', 
            'label': 'Adverse Credit',
            'check': lambda l: 'yes' in str(l.get('heavy_recent_adverse_accepted_eg_missed_mortgage_payments_or', '')).lower() or
                              'bread' in str(l.get('heavy_recent_adverse_accepted_eg_missed_mortgage_payments_or', '')).lower()
        },
        'bankruptcy': {
            'category': 'borrower',
            'icon': '💀', 
            'label': 'Bankruptcy/IVA',
            'check': lambda l: 'yes' in str(l.get('bankrupcy_ivas_accepted', '')).lower()
        },
        'ftb': {
            'category': 'borrower',
            'icon': '🏠', 
            'label': 'First Time Buyer',
            'check': lambda l: 'yes' in str(l.get('do_you_lend_to_first_time_buyers', '')).lower()
        },
        'ftl': {
            'category': 'borrower',
            'icon': '🔑', 
            'label': 'First Time Landlord',
            'check': lambda l: 'yes' in str(l.get('do_you_lend_to_first_time_landlords', '')).lower()
        },
        'non_owner_occ': {
            'category': 'borrower',
            'icon': '👤', 
            'label': 'Non-Owner Occupier',
            'check': lambda l: 'yes' in str(l.get('do_you_lend_to_non_owner_occupiers', '')).lower()
        },
        
        # DEAL REFINERS - All 15 deal appetite scenarios
        'auction': {
            'category': 'deal',
            'icon': '🔨', 
            'label': 'Auction',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside', '0')).strip() or 0) >= 2
        },
        'business_stabilisation': {
            'category': 'deal',
            'icon': '📊', 
            'label': 'Business Stabilisation',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_1', '0')).strip() or 0) >= 2
        },
        'insolvency': {
            'category': 'deal',
            'icon': '⚠️', 
            'label': 'Insolvency/Restructuring',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_2', '0')).strip() or 0) >= 2
        },
        'hmo': {
            'category': 'deal',
            'icon': '🏘️', 
            'label': 'HMO Conversion',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_3', '0')).strip() or 0) >= 2
        },
        'comm_to_resi': {
            'category': 'deal',
            'icon': '🔄', 
            'label': 'Comm to Resi (PD)',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_4', '0')).strip() or 0) >= 2
        },
        'airspace': {
            'category': 'deal',
            'icon': '🏗️', 
            'label': 'Airspace Development',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_5', '0')).strip() or 0) >= 2
        },
        'pre_planning': {
            'category': 'deal',
            'icon': '📋', 
            'label': 'Pre-Planning Acquisition',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_6', '0')).strip() or 0) >= 2
        },
        'subsidence': {
            'category': 'deal',
            'icon': '🏚️', 
            'label': 'Subsidence Repairs',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_7', '0')).strip() or 0) >= 2
        },
        'sitting_tenant': {
            'category': 'deal',
            'icon': '🧑‍🤝‍🧑', 
            'label': 'Sitting Tenant',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_8', '0')).strip() or 0) >= 2
        },
        'probate': {
            'category': 'deal',
            'icon': '📜', 
            'label': 'Probate',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_9', '0')).strip() or 0) >= 2
        },
        'fire_flood': {
            'category': 'deal',
            'icon': '🔥', 
            'label': 'Fire/Flood Damaged',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_10', '0')).strip() or 0) >= 2
        },
        'barn_church': {
            'category': 'deal',
            'icon': '⛪', 
            'label': 'Barn/Church Conversion',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_11', '0')).strip() or 0) >= 2
        },
        'developer_exit': {
            'category': 'deal',
            'icon': '🏁', 
            'label': 'Developer Exit',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_12', '0')).strip() or 0) >= 2
        },
        'lease_extension': {
            'category': 'deal',
            'icon': '📄', 
            'label': 'Lease Extension',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_13', '0')).strip() or 0) >= 2
        },
        'refi_to_btl': {
            'category': 'deal',
            'icon': '🏠', 
            'label': 'Refinance to BTL',
            'check': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_14', '0')).strip() or 0) >= 2
        },
        
        # PRODUCT REFINERS
        'dual_legal': {
            'category': 'product',
            'icon': '⚖️', 
            'label': 'Dual Legal Rep',
            'check': lambda l: 'yes' in str(l.get('dual_legal_rep_offered', '')).lower()
        },
        'serviced_interest': {
            'category': 'product',
            'icon': '💰', 
            'label': 'Serviced Interest',
            'check': lambda l: 'yes' in str(l.get('serviced_interest_allowed', '')).lower()
        },
        'no_exit_fee': {
            'category': 'product',
            'icon': '🚫', 
            'label': 'No Exit Fee',
            'check': lambda l: 'never' in str(l.get('do_you_charge_exit_fees', '')).lower()
        },
        'avm_available': {
            'category': 'product',
            'icon': '📊', 
            'label': 'AVM/Desktop',
            'check': lambda l: 'yes' in str(l.get('can_you_potentially_use_avms_and_or_desktops_for_residential', '')).lower()
        },
    }
    
    # Add refurb-specific refiners if refurb is selected
    if essentials.is_refurb:
        refiner_checks['staged_funding'] = {
            'category': 'deal',
            'icon': '💸', 
            'label': 'Staged Funding',
            'check': lambda l: 'yes' in str(l.get('do_you_also_offer_arrears_staged_funding_for_refurbishments', '')).lower()
        }
        refiner_checks['first_time_dev'] = {
            'category': 'borrower',
            'icon': '👷', 
            'label': 'First-Time Developer OK',
            'check': lambda l: 'none' in str(l.get('minimum_borrower_experience_with_refurbs', '')).lower() or
                              str(l.get('minimum_borrower_experience_with_refurbs', '')).strip() == ''
        }
    
    # Calculate counts for each refiner
    borrower_refiners = []
    deal_refiners = []
    product_refiners = []
    
    for key, config in refiner_checks.items():
        # If this refiner is already active, show it as selected with current count
        if key in active_refiners:
            remaining = current_count
            is_active = True
        else:
            # Count how many would remain if this was added
            remaining = count_if_added(config['check'])
            is_active = False
        
        # Show refiners that have some lenders (skip if would eliminate all)
        # For deal scenarios, always show if there are ANY lenders who do it
        if remaining > 0:
            refiner_data = {
                'key': key,
                'icon': config['icon'],
                'label': config['label'],
                'remaining': remaining,
                'active': is_active
            }
            
            if config['category'] == 'borrower':
                borrower_refiners.append(refiner_data)
            elif config['category'] == 'deal':
                deal_refiners.append(refiner_data)
            else:
                product_refiners.append(refiner_data)
    
    # Sort by remaining count (highest first) within each category
    borrower_refiners.sort(key=lambda x: (-1 if x['active'] else 0, -x['remaining']))
    deal_refiners.sort(key=lambda x: (-1 if x['active'] else 0, -x['remaining']))
    product_refiners.sort(key=lambda x: (-1 if x['active'] else 0, -x['remaining']))
    
    return {
        'base_count': len(eligible),
        'current_count': current_count,
        'borrower_refiners': borrower_refiners,
        'deal_refiners': deal_refiners,
        'product_refiners': product_refiners
    }


def apply_refiners(eligible: List[Dict], active_refiners: set) -> List[Dict]:
    """Apply active refiners to filter the eligible list further"""
    if not active_refiners:
        return eligible
    
    result = eligible
    
    refiner_checks = {
        # Borrower refiners
        'foreign_national': lambda l: 'yes' in str(l.get('can_you_lend_to_foreign_nationals', '')).lower() or 
                                      'only' in str(l.get('can_you_lend_to_foreign_nationals', '')).lower(),
        'expat': lambda l: 'yes' in str(l.get('can_you_lend_to_expats', '')).lower() or
                          'only' in str(l.get('can_you_lend_to_expats', '')).lower(),
        'adverse_credit': lambda l: 'yes' in str(l.get('heavy_recent_adverse_accepted_eg_missed_mortgage_payments_or', '')).lower() or
                                   'bread' in str(l.get('heavy_recent_adverse_accepted_eg_missed_mortgage_payments_or', '')).lower(),
        'bankruptcy': lambda l: 'yes' in str(l.get('bankrupcy_ivas_accepted', '')).lower(),
        'ftb': lambda l: 'yes' in str(l.get('do_you_lend_to_first_time_buyers', '')).lower(),
        'ftl': lambda l: 'yes' in str(l.get('do_you_lend_to_first_time_landlords', '')).lower(),
        'non_owner_occ': lambda l: 'yes' in str(l.get('do_you_lend_to_non_owner_occupiers', '')).lower(),
        
        # Deal appetite refiners (all 15)
        'auction': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside', '0')).strip() or 0) >= 2,
        'business_stabilisation': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_1', '0')).strip() or 0) >= 2,
        'insolvency': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_2', '0')).strip() or 0) >= 2,
        'hmo': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_3', '0')).strip() or 0) >= 2,
        'comm_to_resi': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_4', '0')).strip() or 0) >= 2,
        'airspace': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_5', '0')).strip() or 0) >= 2,
        'pre_planning': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_6', '0')).strip() or 0) >= 2,
        'subsidence': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_7', '0')).strip() or 0) >= 2,
        'sitting_tenant': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_8', '0')).strip() or 0) >= 2,
        'probate': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_9', '0')).strip() or 0) >= 2,
        'fire_flood': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_10', '0')).strip() or 0) >= 2,
        'barn_church': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_11', '0')).strip() or 0) >= 2,
        'developer_exit': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_12', '0')).strip() or 0) >= 2,
        'lease_extension': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_13', '0')).strip() or 0) >= 2,
        'refi_to_btl': lambda l: int(str(l.get('deal_appetite_0_won_t_consider_1_low_appetite_2_will_conside_14', '0')).strip() or 0) >= 2,
        
        # Product refiners
        'dual_legal': lambda l: 'yes' in str(l.get('dual_legal_rep_offered', '')).lower(),
        'serviced_interest': lambda l: 'yes' in str(l.get('serviced_interest_allowed', '')).lower(),
        'no_exit_fee': lambda l: 'never' in str(l.get('do_you_charge_exit_fees', '')).lower(),
        'avm_available': lambda l: 'yes' in str(l.get('can_you_potentially_use_avms_and_or_desktops_for_residential', '')).lower(),
        'staged_funding': lambda l: 'yes' in str(l.get('do_you_also_offer_arrears_staged_funding_for_refurbishments', '')).lower(),
        'first_time_dev': lambda l: 'none' in str(l.get('minimum_borrower_experience_with_refurbs', '')).lower() or
                                    str(l.get('minimum_borrower_experience_with_refurbs', '')).strip() == '',
    }
    
    for refiner_key in active_refiners:
        if refiner_key in refiner_checks:
            result = [l for l in result if refiner_checks[refiner_key](l)]
    
    return result


@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Send message to AI assistant"""
    # Check rate limit
    if not check_rate_limit(message.session_id):
        return {
            "response": "Rate limit reached (30 queries/hour). Please wait before sending more queries.",
            "session_id": message.session_id,
            "rate_limited": True
        }
    
    response = chat_with_ai(
        message.session_id,
        message.message,
        message.deal_essentials
    )
    return {"response": response, "session_id": message.session_id}

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history"""
    history = get_conversation_history(session_id)
    return {"session_id": session_id, "messages": history}

@app.post("/api/chat/new")
async def new_chat():
    """Start new conversation session"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackSubmission):
    """Submit broker feedback on a lender"""
    save_feedback(
        feedback.lender_name,
        feedback.deal_type,
        feedback.rating,
        feedback.feedback_text
    )
    return {"status": "saved"}

@app.get("/api/feedback")
async def get_feedback(lender: str = None):
    """Get feedback, optionally filtered by lender"""
    feedback = get_lender_feedback(lender)
    return {"feedback": feedback}

@app.get("/api/themes")
async def get_themes():
    """Get available UI themes"""
    return {"themes": THEMES}


@app.get("/api/lender/{lender_name}/contact")
async def get_lender_contact_details(lender_name: str):
    """Get contact details for a specific lender"""
    lenders = get_all_lenders()
    lender = next((l for l in lenders if l['name'].lower() == lender_name.lower()), None)
    
    if not lender:
        # Try partial match
        lender = next((l for l in lenders if lender_name.lower() in l['name'].lower()), None)
    
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    
    contact = get_lender_contact(lender)
    return {
        "lender_name": lender['name'],
        "contact": contact,
        "funding_model": lender.get('funding_model', ''),
        "typical_proc_fee": lender.get('typical_proc_fee', ''),
        "rate_band": lender.get('approximate_interest_rate_band', ''),
    }


@app.post("/api/contact-lender")
async def contact_lender(request: ContactLenderRequest):
    """
    Handle contact lender request.
    If generate_email=True and aip_details provided, generates deal presentation email.
    Also re-validates the deal with any new information.
    """
    lenders = get_all_lenders()
    lender = next((l for l in lenders if l['name'].lower() == request.lender_name.lower()), None)
    
    if not lender:
        lender = next((l for l in lenders if request.lender_name.lower() in l['name'].lower()), None)
    
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    
    contact = get_lender_contact(lender)
    
    result = {
        "lender_name": lender['name'],
        "contact": contact,
        "still_fits": True,
        "warnings": [],
        "alternative_suggestions": [],
        "email_template": None
    }
    
    # Re-validate with any new information from AIP details
    if request.aip_details:
        validation = revalidate_with_aip_details(lender, request.deal_essentials, request.aip_details, lenders)
        result["still_fits"] = validation["still_fits"]
        result["warnings"] = validation["warnings"]
        result["alternative_suggestions"] = validation["alternative_suggestions"]
    
    # Generate email if requested
    if request.generate_email and request.aip_details:
        result["email_template"] = generate_deal_presentation_email(
            lender, 
            request.deal_essentials, 
            request.aip_details,
            contact
        )
    
    return result


def revalidate_with_aip_details(lender: Dict, essentials: DealEssentials, aip: AIPDetails, all_lenders: List[Dict]) -> Dict:
    """
    Re-validate deal against lender criteria with additional AIP details.
    Returns warnings and alternative suggestions if the new info changes things.
    """
    warnings = []
    alternatives = []
    still_fits = True
    
    # Check experience requirements for refurb
    if essentials.is_refurb and aip.refurb_experience:
        min_exp = str(lender.get('minimum_borrower_experience_with_refurbs', '')).lower()
        user_exp = aip.refurb_experience.lower()
        
        if 'none' in user_exp or '0' in user_exp or 'first' in user_exp:
            if '2+' in min_exp or '3+' in min_exp:
                warnings.append(f"{lender['name']} requires {min_exp} projects experience for refurb")
                still_fits = False
                # Find alternatives that accept first-timers
                for alt in all_lenders:
                    alt_exp = str(alt.get('minimum_borrower_experience_with_refurbs', '')).lower()
                    if 'none' in alt_exp or '0' in alt_exp or alt_exp == '':
                        if alt['name'] != lender['name']:
                            alternatives.append({
                                'name': alt['name'],
                                'reason': 'Accepts first-time developers'
                            })
                            if len(alternatives) >= 3:
                                break
    
    # Check if they need speed and lender is slow
    if aip.urgency and ('auction' in aip.urgency.lower() or '28' in aip.urgency or 'urgent' in aip.urgency.lower()):
        dual_legal = str(lender.get('dual_legal_rep_offered', '')).lower()
        if 'no' in dual_legal:
            warnings.append(f"{lender['name']} doesn't offer dual legal rep - may be slower for auction")
    
    # Check homeowner status for regulated
    if essentials.is_regulated and aip.is_homeowner == False:
        non_owner = str(lender.get('do_you_lend_to_non_owner_occupiers', '')).lower()
        if 'no' in non_owner:
            warnings.append(f"{lender['name']} may not lend to non-owner occupiers on regulated deals")
            still_fits = False
    
    # Check A&L position
    if aip.assets_liabilities and ('nil' in aip.assets_liabilities.lower() or 'negative' in aip.assets_liabilities.lower()):
        nil_al = str(lender.get('do_you_lend_to_applicants_with_a_nil_or_negative_a_l_profile', '')).lower()
        if 'no' in nil_al:
            warnings.append(f"{lender['name']} doesn't accept nil/negative A&L profiles")
            still_fits = False
    
    return {
        "still_fits": still_fits,
        "warnings": warnings,
        "alternative_suggestions": alternatives[:3]  # Max 3 alternatives
    }


def generate_deal_presentation_email(lender: Dict, essentials: DealEssentials, aip: AIPDetails, contact: Dict) -> str:
    """Generate a deal presentation email for the broker to copy/paste"""
    
    # Calculate LTV
    ltv = (essentials.loan_amount / essentials.market_value * 100) if essentials.market_value > 0 else 0
    
    email = f"""Subject: New Bridging Enquiry - {aip.property_address or 'Property TBC'}

Dear {contact.get('bdm_name', 'New Business Team')},

I have a bridging enquiry I'd like to discuss with you:

**LOAN DETAILS**
- Loan Amount: £{essentials.loan_amount:,.0f}
- Property Value: £{essentials.market_value:,.0f}
- LTV: {ltv:.1f}%
- Property Type: {essentials.property_type.replace('_', ' ').title()}
- Transaction: {essentials.transaction_type.title()}
"""

    if essentials.is_regulated:
        email += "- Regulated: Yes (owner-occupied)\n"
    
    if essentials.is_refurb:
        email += f"- Refurbishment: Yes\n"
        if essentials.cost_of_works:
            email += f"- Works Budget: £{essentials.cost_of_works:,.0f}\n"
        if aip.gdv_estimate:
            email += f"- Estimated GDV: {aip.gdv_estimate}\n"

    email += f"""
**BORROWER**
- Name: {aip.borrower_name or 'TBC'}
- Type: {(aip.borrower_type or essentials.entity_type).replace('_', ' ').title()}
"""

    if aip.is_homeowner is not None:
        email += f"- Homeowner: {'Yes' if aip.is_homeowner else 'No'}\n"
    
    if aip.assets_liabilities:
        email += f"- A&L Position: {aip.assets_liabilities}\n"

    if aip.property_address:
        email += f"""
**PROPERTY**
- Address: {aip.property_address}
"""
    
    if aip.additional_security_address:
        email += f"- Additional Security: {aip.additional_security_address}\n"

    if essentials.is_refurb:
        email += f"""
**REFURBISHMENT DETAILS**
"""
        if aip.refurb_experience:
            email += f"- Developer Experience: {aip.refurb_experience}\n"
        if aip.works_schedule:
            email += f"- Works Schedule: {aip.works_schedule}\n"

    email += f"""
**EXIT STRATEGY**
- Strategy: {aip.exit_strategy or 'TBC'}
"""
    if aip.exit_timeframe:
        email += f"- Timeframe: {aip.exit_timeframe}\n"

    if aip.urgency:
        email += f"""
**TIMING**
- Urgency: {aip.urgency}
"""

    if aip.additional_notes:
        email += f"""
**ADDITIONAL NOTES**
{aip.additional_notes}
"""

    email += """
Please let me know if this is something you can support in principle, and any further information you need.

Best regards,
[Your name]
[Your company]
[Phone/Email]
"""
    
    return email

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("BRIDGING BRAIN v4 - AI-Powered Lender Matching")
    print("=" * 60)
    
    if os.path.exists(DB_PATH):
        lenders = get_all_lenders()
        print(f"Database: {DB_PATH}")
        print(f"Lenders loaded: {len(lenders)}")
    else:
        print(f"WARNING: Database not found: {DB_PATH}")
        print("Run setup_database.py first to import lender data")
    
    ai_client = get_ai_client()
    if ai_client:
        print("AI: Enabled (Anthropic API key found)")
    else:
        print("AI: Disabled (set ANTHROPIC_API_KEY to enable)")
    
    print(f"\nStarting server at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
