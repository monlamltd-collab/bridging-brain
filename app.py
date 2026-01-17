import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Bridging Brain", layout="wide")

@st.cache_data
def load_data():
    # This looks for the clean 'data.csv' file you just uploaded
    return pd.read_csv("data.csv")

try:
    df = load_data()
    st.title("🏦 Bridging Brain v1.0")
    st.markdown("### Your AI Bridging Assistant")

    query = st.text_input("Describe the deal requirements:", placeholder="e.g. 70% LTV semi-commercial with probate")

    if query:
        q = query.lower()
        results = []
        for idx, row in df.iterrows():
            score = 0
            reasons = []
            
            # Smart logic: if you type 'semi', we check the mixed-use column
            if "semi" in q or "mixed" in q:
                score += 20
                reasons.append("Lends on Semi-Commercial/Mixed Use")

            # Smart logic: Check 'Appetite Scores' from your spreadsheet
            appetite_cols = [c for c in df.columns if "appetite" in c.lower()]
            for col in appetite_cols:
                niche_match = re.findall(r"\[(.*?)\]", col)
                if niche_match and niche_match[0].lower() in q:
                    val = pd.to_numeric(row[col], errors='coerce')
                    if val >= 2:
                        score += (val * 10)
                        reasons.append(f"Strong appetite for {niche_match[0]}")

            if score > 0:
                results.append({
                    "Lender": row['Name of Lender'], 
                    "Score": score, 
                    "Reasons": reasons, 
                    "Contact": row['Central number for new enquiries']
                })

        if results:
            # Show the best matches at the top
            for res in sorted(results, key=lambda x: x['Score'], reverse=True):
                with st.expander(f"⭐ {res['Lender']} (Match: {res['Score']} pts)"):
                    st.write(" | ".join(res['Reasons']))
                    st.info(f"📞 **Call BDM:** {res['Contact']}")
        else:
            st.warning("No lenders found for that specific search. Try checking your LTV or asset type.")

except Exception as e:
    st.error("Checking for data.csv... Please ensure your spreadsheet is named 'data.csv' in GitHub.")
