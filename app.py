import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

# 1. Connect to the Database Claude created
def load_db_data():
    conn = sqlite3.connect('bridging_brain.db')
    # We join the main lenders table with their LTV and Refurb criteria
    query = """
    SELECT l.name, l.bdm_name, l.bdm_phone, l.interest_rate_band, l.proc_fee,
           ltv.resi_investment_1st, ltv.semi_commercial_1st,
           refurb.additional_notes, l.end_comments
    FROM lenders l
    LEFT JOIN ltv_criteria ltv ON l.id = ltv.lender_id
    LEFT JOIN refurb_criteria refurb ON l.id = refurb.lender_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

try:
    df = load_db_data()
    st.title("🏦 Bridging Brain: Professional Assistant")
    
    query = st.text_input("Describe the deal (e.g., Equitable charge semi-commercial):")
    
    if query:
        q = query.lower()
        search_terms = [w for w in q.split() if len(w) > 3]
        
        results = []
        for _, row in df.iterrows():
            # Create a searchable string from all columns
            row_content = " ".join(row.fillna('').astype(str).values).lower()
            score = sum(1 for term in search_words if term in row_content)
            
            if score > 0:
                results.append({"data": row, "score": score})

        # --- 3 COLUMN TRAFFIC LIGHTS ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("### 🟢 High Appetite")
            # Logic: Matches 2+ keywords
            for r in [x for x in results if x['score'] >= 2]:
                with st.expander(f"⭐ {r['data']['name']}"):
                    st.write(f"📞 BDM: {r['data']['bdm_name']} - {r['data']['bdm_phone']}")
                    st.write(f"💰 Rate: {r['data']['interest_rate_band']}")
                    st.write(f"📝 Notes: {r['data']['end_comments']}")

        with col2:
            st.warning("### 🟡 Possible")
            # Logic: Matches 1 keyword
            for r in [x for x in results if x['score'] == 1]:
                with st.expander(f"{r['data']['name']}"):
                    st.write(f"📞 Contact: {r['data']['bdm_name']}")

        with col3:
            st.error("### 🔴 Low Probability")
            st.write("Lenders with 0 matches are hidden.")

except Exception as e:
    st.error(f"Database Error: {e}")
    st.info("Make sure 'bridging_brain.db' is uploaded to the same folder as this app.")
