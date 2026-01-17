import streamlit as st
import pandas as pd
import os

# 1. Setup the Page
st.set_page_config(page_title="Bridging Brain", layout="wide", initial_sidebar_state="collapsed")

# 2. Smart Data Loading
@st.cache_data
def load_data():
    file_path = "data.csv"
    # We use engine='python' and on_bad_lines to handle messy Excel exports
    df = pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip', encoding_errors='ignore')
    # Clean up column names (remove spaces/tabs)
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()

    # --- THE INTERFACE ---
    st.title("🏦 Bridging Brain v1.0")
    st.markdown("---")
    
    # Search Box
    query = st.text_input("Describe the deal (e.g. 70% LTV semi-commercial in Scotland):", placeholder="Start typing...")

    if query:
        q = query.lower()
        results = []

        for idx, row in df.iterrows():
            score = 0
            matches = []

            # A. Geography Check (Scotland/NI)
            if "scot" in q:
                if "scot" in str(row.get("Which geographies don't you lend in?", "")).lower():
                    score -= 100 # Skip this lender
                else:
                    score += 10
                    matches.append("Lends in Scotland")

            # B. Asset Type Logic
            if "semi" in q or "mixed" in q:
                score += 15
                matches.append("Mixed-Use appetite")
            
            if "land" in q:
                score += 15
                matches.append("Land specialist")

            # C. Keyword Universal Search (Matches any text in the row)
            row_text = " ".join(row.astype(str).lower())
            if q in row_text:
                score += 5
            
            # D. Only include if they aren't ruled out
            if score > 0:
                results.append({
                    "Lender": row.get('Name of Lender', 'Unknown'),
                    "Contact": row.get('Central number for new enquiries', 'N/A'),
                    "Score": score,
                    "Details": matches,
                    "Full_Row": row
                })

        # --- DISPLAY RESULTS ---
        if results:
            # Sort by highest score first
            sorted_results = sorted(results, key=lambda x: x['Score'], reverse=True)
            
            st.subheader(f"Found {len(sorted_results)} Potential Lenders")
            
            for res in sorted_results:
                with st.expander(f"⭐ {res['Lender']} (Score: {res['Score']})"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"📞 **Contact:** {res['Contact']}")
                        if res['Details']:
                            st.write(f"✅ {', '.join(res['Details'])}")
                    with col2:
                        # Show the full breakdown of their questionnaire response
                        st.write("**Lender Notes:**")
                        st.write(res['Full_Row'].dropna().to_dict())
        else:
            st.warning("No perfect matches. Try searching for just the asset type (e.g., 'Land').")

except Exception as e:
    st.error(f"Waiting for clean data... Error: {e}")
    st.info("Check: Is your file on GitHub named 'data.csv' (all lowercase)?")
