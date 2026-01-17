import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

@st.cache_data
def load_data():
    # Load and immediately force everything to string to kill that 'lower' error
    df = pd.read_csv("data.csv", quoting=3, on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    return df.astype(str)

try:
    df = load_data()
    st.title("🏦 Bridging Brain: Underwriting Assistant")
    
    # Text input and a physical button for ease of use
    query = st.text_input("Describe the deal in plain English:")
    search_button = st.button("🔍 Analyze Deal")

    if query or search_button:
        q = query.lower()
        results = []
        
        # Keywords for the brain to trigger on
        targets = ["equitable", "charge", "scotland", "semi", "mixed", "land", "probate", "hmo", "refurb"]

        # Loop through data and score
        for idx, row in df.iterrows():
            score = 0
            # Combine all row data into one searchable string safely
            combined_text = " ".join(row.values).lower()
            
            for t in targets:
                if t in q and t in combined_text:
                    score += 25

            if score >= 50: color = "green"
            elif score >= 25: color = "orange"
            else: color = "red"

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
                        st.json(r['Details']) # Clean way to see all data

            with med_col:
                st.subheader("🟡 Possible")
                for r in [x for x in results if x['Color'] == 'orange']:
                    with st.expander(f"{r['Lender']}"):
                        st.write(f"📞 **Contact:** {r['Contact']}")
                        st.json(r['Details'])

            with low_col:
                st.subheader("🔴 Low Probability")
                for r in [x for x in results if x['Color'] == 'red']:
                    st.write(f"❌ {r['Lender']}")
        else:
            st.warning("No matches found. Try keywords like 'Equitable' or 'Scotland'.")

except Exception as e:
    st.error(f"Technical Error: {e}")
