import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain Debug", layout="wide")

@st.cache_data
def load_data():
    # We'll use a safer way to read the file
    df = pd.read_csv("data.csv", on_bad_lines='skip')
    df.columns = df.columns.str.strip() 
    return df

try:
    df = load_data()
    st.title("🏦 Bridging Brain v1.0")

    # --- DEBUG SECTION: This lets us see if data exists ---
    with st.expander("🛠️ Debug: See your raw data"):
        st.write("Total Rows found:", len(df))
        st.write("Column Names:", list(df.columns))
        st.dataframe(df.head(5)) # Shows the first 5 rows

    query = st.text_input("Search for a lender (try just one word):")

    if query:
        # We'll search by converting everything to a string first
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            st.success(f"Found {len(results)} matches")
            for _, row in results.iterrows():
                st.write(f"### {row.get('Name of Lender', 'Unknown')}")
                st.write(row.dropna().to_dict())
        else:
            st.warning(f"No match for '{query}'. Check the 'Debug' section above to see if your data loaded.")

except Exception as e:
    st.error(f"Critical Error: {e}")
