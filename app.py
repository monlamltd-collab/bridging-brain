import streamlit as st
import pandas as pd
import csv

st.set_page_config(page_title="Bridging Brain", layout="wide")

@st.cache_data
def load_data():
    # quoting=3 tells pandas to ignore all quote marks and treat them as normal text
    # on_bad_lines='skip' ensures that if row 72 is truly mangled, it just skips it
    df = pd.read_csv("data.csv", quoting=3, on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
    st.title("🏦 Bridging Brain v1.0")

    query = st.text_input("Search for a lender or criteria:")

    if query:
        # Search across all columns
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            st.success(f"Found {len(results)} matches")
            for _, row in results.iterrows():
                lender = row.get('Name of Lender', 'Unknown Lender')
                with st.expander(f"⭐ {lender}"):
                    # Clean up the display so it doesn't show NaN (empty) values
                    st.write(row.dropna().to_dict())
        else:
            st.warning(f"No match found for '{query}'.")

except Exception as e:
    st.error(f"Almost there! We found a glitch in the spreadsheet text: {e}")
    st.info("Tip: This usually happens if a lender used a double-quote (quote marks) in their answer.")
