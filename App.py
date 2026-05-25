import streamlit as st
import pandas as pd
import numpy as np
import io

GSHEET_URL = "https://docs.google.com/spreadsheets/d/10YYPKcu0IPD1S4XBlzY4Vf2lM5likd5Rd_FYq7Owh1E/edit?usp=drivesdk"

@st.cache_data(ttl=5)
def get_master():
    csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    df = pd.read_csv(csv_url)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # FORCE TO STRING to prevent type mismatch
    df['item_name'] = df['item_name'].astype(str).str.lower().str.strip()
    
    # Set up columns
    cols_needed = ['item_name', 'par_level', 'reorder_trigger', 'conversion_factor']
    for c in cols_needed:
        if c not in df.columns:
            df[c] = 0 if c != 'conversion_factor' else 1
    
    df['conversion_factor'] = pd.to_numeric(df['conversion_factor'], errors='coerce').fillna(1)
    return df

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Order Calculator", "View Master Database"])

if page == "View Master Database":
    st.title("📊 Master Database Settings")
    st.dataframe(get_master())

else:
    st.title("📦 Commissary Inventory Manager")
    raw_data = st.text_area("Paste inventory dump (include headers):", height=300)
    
    if st.button("Run Calculation"):
        try:
            data = io.StringIO(raw_data)
            df_in = pd.read_csv(data, sep='\t')
            df_in.columns = [c.lower().strip() for c in df_in.columns]
            
            # FORCE TO STRING to prevent type mismatch
            df_in = df_in.rename(columns={'item': 'item_name'})
            df_in['item_name'] = df_in['item_name'].astype(str).str.lower().str.strip()
            
            # Sum quantities
            qty_cols = [c for c in df_in.columns if 'qty' in c]
            df_in['total_raw_qty'] = df_in[qty_cols].sum(axis=1)
            
            totals = df_in.groupby('item_name')['total_raw_qty'].sum().reset_index()
            
            # Merge with Master
            master = get_master()
            final = pd.merge(totals, master, on='item_name', how='inner')
            
            # Calculate
            final['total_units'] = final['total_raw_qty'] * final['conversion_factor']
            final['order_needed'] = np.where(
                final['total_units'] <= final['reorder_trigger'],
                np.ceil(final['par_level'] - final['total_units']),
                0
            )
            
            st.table(final[final['order_needed'] > 0][['item_name', 'total_units', 'par_level', 'order_needed']])
            
        except Exception as e:
            st.error(f"Format error: {e}")
