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
    df['conversion_factor'] = pd.to_numeric(df['conversion_factor'], errors='coerce').fillna(1)
    return df

st.title("📦 Commissary Multi-Column Manager")
raw_data = st.text_area("Paste your full inventory table here:", height=300)

if st.button("Run Calculation"):
    try:
        # 1. Read as Tab Separated
        data = io.StringIO(raw_data)
        df_in = pd.read_csv(data, sep='\t')
        
        # 2. STANDARDIZATION: Rename your columns to match expected names
        df_in = df_in.rename(columns={
            'Item': 'item_name', 
            'UofM': 'unit', 'Qty': 'qty',
            'UofM2': 'unit2', 'Qty2': 'qty2',
            'UofM3': 'unit3', 'Qty3': 'qty3'
        })
        
        # 3. Reshape the 3 sets of columns into one clean list
        part1 = df_in[['item_name', 'unit', 'qty']]
        part2 = df_in[['item_name', 'unit2', 'qty2']].rename(columns={'unit2': 'unit', 'qty2': 'qty'})
        part3 = df_in[['item_name', 'unit3', 'qty3']].rename(columns={'unit3': 'unit', 'qty3': 'qty'})
        
        full_df = pd.concat([part1, part2, part3]).dropna(subset=['qty'])
        full_df['item_name'] = full_df['item_name'].str.lower().str.strip()
        
        # 4. Merge and Calculate
        master = get_master()
        merged = pd.merge(full_df, master, on='item_name', how='left')
        
        merged['conversion_factor'] = merged['conversion_factor'].fillna(1)
        merged['total_stock'] = merged['qty'] * merged['conversion_factor']
        
        # 5. Aggregate and Result
        final = merged.groupby('item_name').agg({
            'total_stock': 'sum',
            'par_level': 'first',
            'reorder_trigger': 'first'
        }).reset_index()
        
        final['order_needed'] = np.where(
            final['total_stock'] <= final['reorder_trigger'],
            np.ceil(final['par_level'] - final['total_stock']),
            0
        )
        
        st.table(final[final['order_needed'] > 0][['item_name', 'total_stock', 'par_level', 'order_needed']])
        
    except Exception as e:
        st.error(f"Format error: {e}")
