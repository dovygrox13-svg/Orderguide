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
    df.columns = df.columns.str.strip()
    return df

st.title("📦 Commissary Inventory Manager")
raw_data = st.text_area("Paste inventory dump below:", height=300)

if st.button("Run Calculation"):
    try:
        # 1. Force tab-separation to fix the "smeared" column issue
        df_in = pd.read_csv(io.StringIO(raw_data), sep='\t')
        df_in.columns = df_in.columns.str.strip()
        
        # 2. Summing Logic: Find all columns containing 'Qty' (Qty, Qty2, Qty3)
        qty_cols = [c for c in df_in.columns if 'qty' in c.lower()]
        df_in['total_raw_qty'] = df_in[qty_cols].sum(axis=1)
        
        # 3. Aggregate by 'Item'
        totals = df_in.groupby('Item')['total_raw_qty'].sum().reset_index()
        
        # 4. Merge with Master
        master = get_master()
        final = pd.merge(totals, master, on='Item', how='inner')
        
        # 5. Math
        final['total_units'] = final['total_raw_qty'] * pd.to_numeric(final['conversion_factor'], errors='coerce').fillna(1)
        final['order_needed'] = np.where(
            final['total_units'] <= pd.to_numeric(final['reorder_trigger'], errors='coerce'),
            np.ceil(pd.to_numeric(final['par_level'], errors='coerce') - final['total_units']),
            0
        )
        
        # 6. Display
        st.table(final[final['order_needed'] > 0][['Item', 'total_units', 'par_level', 'order_needed']])
        
    except Exception as e:
        st.error(f"Error: {e}. If it says 'Item', check if you have an 'Item' column in your paste.")
        st.write("Headers found by the code:", list(df_in.columns) if 'df_in' in locals() else "No data read")
