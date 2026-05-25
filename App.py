import streamlit as st
import pandas as pd
import numpy as np
import io

GSHEET_URL = "https://docs.google.com/spreadsheets/d/10YYPKcu0IPD1S4XBlzY4Vf2lM5likd5Rd_FYq7Owh1E/edit?usp=drivesdk"

@st.cache_data(ttl=5)
def get_master():
    csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    df = pd.read_csv(csv_url)
    # This force-cleans the master sheet headers to exactly "Item"
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
            df_in = pd.read_csv(io.StringIO(raw_data), sep='\t')
            # This force-cleans the paste headers to exactly "Item"
            df_in.columns = df_in.columns.str.strip()
            
            # Use the second column index (position 1) to identify items
            item_col_name = df_in.columns[1]
            
            # Combine all qty columns
            qty_cols = [c for c in df_in.columns if 'qty' in c.lower()]
            df_in['total_raw_qty'] = df_in[qty_cols].sum(axis=1)
            
            # Grouping
            totals = df_in.groupby(item_col_name)['total_raw_qty'].sum().reset_index()
            totals = totals.rename(columns={item_col_name: 'Item'})
            
            # Merging
            master = get_master()
            final = pd.merge(totals, master, on='Item', how='inner')
            
            # Math
            final['total_units'] = final['total_raw_qty'] * pd.to_numeric(final['conversion_factor'], errors='coerce').fillna(1)
            final['order_needed'] = np.where(
                final['total_units'] <= pd.to_numeric(final['reorder_trigger'], errors='coerce'),
                np.ceil(pd.to_numeric(final['par_level'], errors='coerce') - final['total_units']),
                0
            )
            
            st.table(final[final['order_needed'] > 0][['Item', 'total_units', 'par_level', 'order_needed']])
            
        except Exception as e:
            st.error(f"Error: {e}")
