import streamlit as st
import pandas as pd
import numpy as np
import io

# 1. REPLACE THIS WITH YOUR ACTUAL GOOGLE SHEET URL
GSHEET_URL = "https://docs.google.com/spreadsheets/d/10YYPKcu0IPD1S4XBlzY4Vf2lM5likd5Rd_FYq7Owh1E/edit?usp=drivesdk"

@st.cache_data(ttl=5)
def get_master():
    csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    return df

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Order Calculator", "View Master Database"])

if page == "View Master Database":
    st.title("📊 Master Database")
    st.dataframe(get_master())

else:
    st.title("📦 Commissary Inventory Manager")
    raw_data = st.text_area("Paste inventory dump:", height=300)
    
    if st.button("Run Calculation"):
        try:
            # 1. Load Data
            df_in = pd.read_csv(io.StringIO(raw_data), sep='\t')
            
            # 2. Automatically find the first numeric column to use as 'Quantity'
            numeric_cols = df_in.select_dtypes(include=[np.number]).columns
            qty_col = numeric_cols[0] 
            
            # 3. Aggregate totals by 'Item'
            totals = df_in.groupby('Item')[qty_col].sum().reset_index()
            
            # 4. Pull rules from Master Sheet
            master = get_master()
            
            # 5. Merge on 'Item'
            final = pd.merge(totals, master, on='Item', how='inner')
            
            # 6. Math
            final['total_units'] = final[qty_col] * pd.to_numeric(final['conversion_factor'], errors='coerce').fillna(1)
            final['order_needed'] = np.where(
                final['total_units'] <= pd.to_numeric(final['reorder_trigger'], errors='coerce'),
                np.ceil(pd.to_numeric(final['par_level'], errors='coerce') - final['total_units']),
                0
            )
            
            st.table(final[final['order_needed'] > 0][['Item', 'total_units', 'par_level', 'order_needed']])
            
        except Exception as e:
            st.error(f"Error: {e}. Please ensure your dump has an 'Item' column.")
