import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bridging Brain v1.0", layout="wide")

@st.cache_data
def load_data():
    # Final 'Safe' Load
    df = pd.read_csv("data.csv", on_bad_lines='skip', encoding_errors='ignore')
    df.columns = df.columns.str.strip()
    return df.fillna("Not Specified")

try:
    df = load_data()
    st.title("🏦 Bridging Brain: Underwriting Assistant")
    
    query = st.text_input("Describe your deal:", placeholder="e.g. Find me a lender for equitable charges")
    
    if query:
        q = query.lower()
        # Split your sentence into words
        search_words = [w for w in q.split() if len(w) > 3] # Only look for words longer than 3 letters
        
        green_list = []
        orange_list = []

        for idx, row in df.iterrows():
            # Create one big string of all data in this row
            row_str = " ".join(row.astype(str).values).lower()
            
            # Count how many of your words appear in this row
            match_count = sum(1 for word in search_words if word in row_str)

            if match_count >= 2:
                green_list.append(row)
            elif match_count == 1:
                orange_list.append(row)

        # --- 3 COLUMN DISPLAY ---
        col1, col2, col3 = st.columns(3)

        with col1:
            st.success("### 🟢 High Appetite")
            for r in green_list:
                with st.expander(f"⭐ {r['Name of Lender']}"):
                    st.write(f"📞 **Contact:** {r['Central number for new enquiries']}")
                    st.write(r.to_dict())

        with col2:
            st.warning("### 🟡 Possible")
            for r in orange_list:
                with st.expander(f"{r['Name of Lender']}"):
                    st.write(f"📞 **Contact:** {r['Central number for new enquiries']}")
                    st.write(r.to_dict())

        with col3:
            st.error("### 🔴 Low Probability")
            st.write("Lenders not matching key terms are excluded from this view.")

except Exception as e:
    st.error(f"Error: {e}")
