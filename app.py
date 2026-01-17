import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Bridging Brain", layout="wide")

# This new logic checks exactly where the file is hiding
@st.cache_data
def load_data():
    file_path = os.path.join(os.getcwd(), "data.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        # This will tell us EXACTLY what the computer sees
        available_files = os.listdir(os.getcwd())
        return f"Error: I can see these files: {available_files}"

data = load_data()

if isinstance(data, str):
    st.error(data)
    st.info("Check if 'data.csv' is spelled correctly (no capitals) in your GitHub list.")
else:
    st.title("🏦 Bridging Brain v1.0")
    query = st.text_input("Describe the deal:", placeholder="e.g. 70% LTV semi-comm")
    
    if query:
        # Simple search across the 'Name of Lender' column
        mask = data['Name of Lender'].str.contains(query, case=False, na=False)
        results = data[mask]
        
        if not results.empty:
            for _, row in results.iterrows():
                with st.expander(f"⭐ {row['Name of Lender']}"):
                    st.write(f"📞 Contact: {row['Central number for new enquiries']}")
        else:
            st.warning("No matches found.")
