import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain", layout="wide")

@st.cache_data
def load_data():
    # This version is designed to be very 'forgiving' of messy data
    df = pd.read_csv("data.csv", sep=None, engine='python', on_bad_lines='skip')
    df.columns = df.columns.str.strip() # Remove hidden spaces from headers
    return df

try:
    df = load_data()
    st.title("🏦 Bridging Brain v1.0")
    
    query = st.text_input("Type a lender name, LTV, or criteria (e.g. Scotland):")

    if query:
        # This looks through every row and every column for your search term
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            st.success(f"Found {len(results)} matches")
            for _, row in results.iterrows():
                # We use .get() so it doesn't crash if a column name is slightly different
                lender = row.get('Name of Lender', 'Lender Name Not Found')
                phone = row.get('Central number for new enquiries', 'No number listed')
                
                with st.expander(f"⭐ {lender}"):
                    st.write(f"📞 **Contact:** {phone}")
                    st.write("---")
                    # This shows all the other info from the spreadsheet for that lender
                    st.dataframe(row.dropna()) 
        else:
            st.warning("No lenders found with that criteria.")

except Exception as e:
    st.error(f"Data Error: {e}")
