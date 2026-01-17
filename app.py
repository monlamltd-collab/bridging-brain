import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("data.csv", quoting=3, on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
    st.title("🏦 Bridging Brain: Underwriting Assistant")
    
    query = st.text_input("Describe the deal in plain English:", placeholder="e.g. Find me a lender for equitable charges")

    if query:
        q = query.lower()
        results = []

        # Keywords the 'Brain' looks for in your sentence
        # We can add more to this list later!
        targets = ["equitable", "charge", "scotland", "semi", "mixed", "land", "probate", "hmo"]

        for idx, row in df.iterrows():
            score = 0
            reasons = []
            
            # This line fixes the error you just saw: 
            # It turns the whole row into one long string of text safely
            row_content = " ".join(row.fillna('').astype(str).lower())

            for t in targets:
                if t in q and t in row_content:
                    score += 25
                    reasons.append(f"Matched {t.title()}")

            # Traffic Light Logic
            if score >= 50:
                color = "green"
            elif score >= 25:
                color = "orange"
            else:
                color = "red"

            if score > 0:
                results.append({
                    "Lender": row.get('Name of Lender', 'Unknown'),
                    "Contact": row.get('Central number for new enquiries', 'N/A'),
                    "Score": score,
                    "Color": color,
                    "Details": row.dropna().to_dict()
                })

        # --- THE 3-SECTION LAYOUT ---
        if results:
            high_col, med_col, low_col = st.columns(3)

            with high_col:
                st.subheader("🟢 High Appetite")
                for r in [x for x in results if x['Color'] == 'green']:
                    with st.expander(f"⭐ {r['Lender']}"):
                        st.write(f"📞 {r['Contact']}")
                        st.write(r['Details'])

            with med_col:
                st.subheader("🟡 Possible")
                for r in [x for x in results if x['Color'] == 'orange']:
                    with st.expander(f"{r['Lender']}"):
                        st.write(f"📞 {r['Contact']}")
                        st.write(r['Details'])

            with low_col:
                st.subheader("🔴 Low Probability")
                # Showing just the names here to keep it clean
                for r in [x for x in results if x['Color'] == 'red']:
                    st.write(f"- {r['Lender']}")
        else:
            st.warning("No lenders found. Try using different keywords like 'Equitable' or 'Land'.")

except Exception as e:
    st.error(f"Error: {e}")
