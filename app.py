import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

@st.cache_data
def load_data():
    # Using the 'tough' settings we discovered earlier
    df = pd.read_csv("data.csv", quoting=3, on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
    st.title("🏦 Bridging Brain: Professional Underwriting Assistant")
    
    # --- NATURAL LANGUAGE SEARCH ---
    query = st.text_input("Describe the deal in plain English:", placeholder="e.g. 75% LTV equitable charge on a semi-commercial in Scotland")

    if query:
        q = query.lower()
        results = []

        for idx, row in df.iterrows():
            score = 0
            reasons = []
            row_str = " ".join(row.astype(str).lower())

            # 1. SMART KEYWORD MATCHING (Natural Language)
            # This looks for the "intent" behind your sentence
            keywords = {
                "equitable": 40, 
                "charge": 10,
                "scotland": 30,
                "semi": 20,
                "mixed": 20,
                "land": 25,
                "probate": 20
            }

            for word, points in keywords.items():
                if word in q and word in row_str:
                    score += points
                    reasons.append(f"Matched: {word.title()}")

            # 2. TRAFFIC LIGHT LOGIC
            status = "🔴 Unlikely"
            color = "red"
            if score > 50:
                status = "🟢 High Appetite"
                color = "green"
            elif score > 20:
                status = "🟡 Possible"
                color = "orange"

            if score > 0:
                results.append({
                    "Lender": row.get('Name of Lender', 'Unknown'),
                    "Contact": row.get('Central number for new enquiries', 'N/A'),
                    "Score": score,
                    "Status": status,
                    "Color": color,
                    "Data": row
                })

        # --- 3-SECTION LAYOUT ---
        if results:
            # Sort by highest score
            sorted_res = sorted(results, key=lambda x: x['Score'], reverse=True)
            
            top_col, mid_col, low_col = st.columns(3)

            with top_col:
                st.header("🟢 Strong Matches")
                for r in [x for x in sorted_res if x['Color'] == 'green']:
                    with st.expander(f"{r['Lender']}"):
                        st.write(f"📞 {r['Contact']}")
                        st.info(f"Score: {r['Score']}")

            with mid_col:
                st.header("🟡 Possible")
                for r in [x for x in sorted_res if x['Color'] == 'orange']:
                    with st.expander(f"{r['Lender']}"):
                        st.write(f"📞 {r['Contact']}")

            with low_col:
                st.header("🔴 Low Match")
                for r in [x for x in sorted_res if x['Color'] == 'red']:
                    st.write(f"~~{r['Lender']}~~")
        else:
            st.warning("No lenders found for that specific criteria.")

except Exception as e:
    st.error(f"System Error: {e}")
