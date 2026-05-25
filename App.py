import streamlit as st
import pandas as pd
import io

# --- 🔗 LINK YOUR GOOGLE SHEET ---
GSHEET_URL = "PASTE_YOUR_GOOGLE_SHEET_URL_HERE"

@st.cache_data(ttl=5)
def get_master():
    csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    df = pd.read_csv(csv_url)
    df.columns = [c.lower().strip() for c in df.columns]
    # Default conversion to 1 if blank
    df['conversion_factor'] = pd.to_numeric(df['conversion_factor'], errors='coerce').fillna(1)
    return df

st.title("📦 Commissary Multi-Column Manager")

raw_data = st.text_area("Paste your full inventory table here (including headers):", height=300)

if st.button("Run Multi-Column Calculation"):
    try:
        # 1. Parse the tab-separated or CSV data
        data = io.StringIO(raw_data)
        df_in = pd.read_csv(data, sep='\t') # Assumes tab-separated from spreadsheet
        
        # 2. Reshape: Combine the 3 UofM/Qty pairs into one long list
        # This takes UofM1/Qty1, UofM2/Qty2, and UofM3/Qty3 and stacks them
        part1 = df_in[['Item', 'UofM', 'Qty']].rename(columns={'Item':'item_name', 'UofM':'unit', 'Qty':'qty'})
        part2 = df_in[['Item', 'UofM2', 'Qty2']].rename(columns={'Item':'item_name', 'UofM2':'unit', 'Qty2':'qty'})
        part3 = df_in[['Item', 'UofM3', 'Qty3']].rename(columns={'Item':'item_name', 'UofM3':'unit', 'Qty3':'qty'})
        
        full_df = pd.concat([part1, part2, part3]).dropna(subset=['qty'])
        full_df['item_name'] = full_df['item_name'].str.lower().str.strip()
        
        # 3. Merge with Master Pars
        master = get_master()
        merged = pd.merge(full_df, master, on='item_name', how='left')
        
        # 4. Calculate total in Master Units
        merged['conversion_factor'] = merged['conversion_factor'].fillna(1)
        merged['total_stock'] = merged['qty'] * merged['conversion_factor']
        
        # 5. Group by item to get grand total
        final = merged.groupby('item_name')[['total_stock', 'par_level', 'reorder_trigger']].first().reset_index()
        final['current_stock'] = merged.groupby('item_name')['total_stock'].sum().values
        
        # 6. Calc Order
        import numpy as np
        final['order_needed'] = np.where(
            final['current_stock'] <= final['reorder_trigger'],
            np.ceil(final['par_level'] - final['current_stock']),
            0
        )
        
        st.table(final[final['order_needed'] > 0][['item_name', 'current_stock', 'par_level', 'order_needed']])
        
    except Exception as e:
        st.error(f"Data format error: {e}")
