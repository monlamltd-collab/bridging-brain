import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

@st.cache_data
def load_data():
    # Load with basic settings to ensure the file opens
    df = pd.read_csv("data.csv", quoting=3, on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    # Force the entire spreadsheet to be strings (text) immediately
    return df.astype(str)

try:
    df = load_data()
    st.title("🏦 Bridging Brain: Underwriting Assistant")
    
    query = st.text_input("Describe the deal in plain English:", placeholder="e.g. Find me a lender for equitable charges")

    if query:
        q = query.lower()
        results = []

        # The keywords our 'Brain' recognizes
        targets = ["equitable", "charge", "scotland", "semi", "mixed", "land", "probate", "hmo", "refurb"]

        for idx, row in df.iterrows():
            score = 0
            # We combine the row into one long string carefully to avoid the 'Series' error
            row_text = " ".join(row.values).lower()

            # Check for matches
            matched_words = []
            for t in targets:
                if t in q and t in row_text:
                    score += 25
                    matched_words.append(t.title())

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
                    "Details": row.to_dict()
                })

        # --- THE 3-SECTION LAYOUT ---
        if results:
            high_col, med_col, low_col = st.columns(3)

            with high_col:
                st.subheader("🟢 High Appetite")
                for r in [x for x in results if x['Color'] == 'green']:
                    with st.expander(f"⭐ {r['Lender']} ({r['Score']} pts)"):
                        st.write(f"📞 **Contact:** {r['Contact']}")
                        st.write("---")
                        st.write(r['Details'])

            with med_col:
                st.subheader("🟡 Possible")
                for r in [x for x in results if x['Color'] == 'orange']:
                    with st.expander(f"{r['Lender']}"):
                        st.write(f"📞 **Contact:** {r['Contact']}")
                        st.write(r['Details'])

            with low_col:
                st.subheader("🔴 Low Probability")
                for r in [x for x in results if x['Color'] == 'red']:
                    st.write(f"❌ {r['Lender']}")
        else:
            st.warning("I couldn't find those specific terms. Try keywords like 'Equitable' or 'Scotland'.")

except Exception as e:
    st.error(f"Technical Error: {e}")
