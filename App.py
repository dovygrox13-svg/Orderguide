import streamlit as st
import pandas as pd
import numpy as np
import io

# REPLACE THIS WITH YOUR ACTUAL GOOGLE SHEET URL
GSHEET_URL = "https://docs.google.com/spreadsheets/d/10YYPKcu0IPD1S4XBlzY4Vf2lM5likd5Rd_FYq7Owh1E/edit?usp=drivesdk"

@st.cache_data(ttl=5)
def get_master():
    csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    df = pd.read_csv(csv_url)
    # Match your sheet's naming convention
    df.columns = df.columns.str.lower().str.strip()
    # Ensure item_name is string for perfect matching
    df['item_name'] = df['item'].astype(str).str.lower().str.strip()
    return df

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Order Calculator", "View Master Database"])

if page == "View Master Database":
    st.title("📊 Master Database")
    st.dataframe(get_master())

else:
    st.title("📦 Inventory Manager")
    raw_data = st.text_area("Paste inventory dump:", height=300)
    
    if st.button("Run Calculation"):
        try:
            # 1. Load Data
            df_in = pd.read_csv(io.StringIO(raw_data), sep='\t')
            df_in.columns = df_in.columns.str.lower().str.strip()
            # Standardize item name to 'item_name'
            df_in = df_in.rename(columns={'item': 'item_name'})
            df_in['item_name'] = df_in['item_name'].astype(str).str.lower().str.strip()
            
            # 2. Sum all qty columns
            qty_cols = [c for c in df_in.columns if 'qty' in c]
            df_in['total_raw_qty'] = df_in[qty_cols].sum(axis=1)
            
            # 3. Aggregate
            totals = df_in.groupby('item_name')['total_raw_qty'].sum().reset_index()
            
            # 4. Merge
            master = get_master()
            final = pd.merge(totals, master, on='item_name', how='inner')
            
            # 5. Math
            conv = pd.to_numeric(final['conversion_factor'], errors='coerce').fillna(1)
            par = pd.to_numeric(final['par_level'], errors='coerce').fillna(0)
            trig = pd.to_numeric(final['reorder_trigger'], errors='coerce').fillna(0)
            
            final['total_units'] = final['total_raw_qty'] * conv
            final['order_needed'] = np.where(final['total_units'] <= trig, np.ceil(par - final['total_units']), 0)
            
            # 6. Display
            st.table(final[final['order_needed'] > 0][['item_name', 'total_units', 'par_level', 'order_needed']])
            
        except Exception as e:
            st.error(f"Error: {e}")
