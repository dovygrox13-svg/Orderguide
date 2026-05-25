import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 🔗 LINK YOUR GOOGLE SHEET ---
GSHEET_URL = "PASTE_YOUR_GOOGLE_SHEET_URL_HERE" 

@st.cache_data(ttl=5)
def get_data():
    try:
        csv_url = GSHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
        df = pd.read_csv(csv_url)
        df.columns = [c.lower().strip() for c in df.columns]
        # Ensure conversion is numeric; default to 1 if blank
        df['conversion_factor'] = pd.to_numeric(df['conversion_factor'], errors='coerce').fillna(1)
        return df
    except:
        return pd.DataFrame(columns=['item_name', 'par_level', 'reorder_trigger', 'conversion_factor'])

st.title("📦 Commissary Inventory Manager")

# Password Protection
password = st.text_input("Manager Password:", type="password")
if password == "shopmanager123":
    st.sidebar.success("Logged In!")
    st.sidebar.markdown(f"[✏️ Edit Pars in Google Sheets]({GSHEET_URL})")

st.subheader("📋 Paste Raw Inventory Data")
st.write("Format: **item_name, count, unit**")
raw_data = st.text_area("Paste here:", placeholder="Focaccia, 1, Tray\nFocaccia, 5, Slice")

if st.button("Calculate Orders"):
    try:
        data = io.StringIO(raw_data)
        df_in = pd.read_csv(data, names=['item_name', 'qty', 'unit'], header=None)
        df_in['item_name'] = df_in['item_name'].str.lower().str.strip()
        
        master = get_data()
        
        # Merge input with master database for conversion factors
        merged = pd.merge(df_in, master, on='item_name', how='left')
        
        # Apply conversion factor
        merged['total_units'] = merged['qty'] * merged['conversion_factor']
        
        # Combine duplicates by item name
        totals = merged.groupby('item_name')[['total_units', 'par_level', 'reorder_trigger']].first().reset_index()
        totals['current_stock'] = merged.groupby('item_name')['total_units'].sum().values
        
        # Calculate Order: (Par - Current) if below Trigger
        totals['order_needed'] = np.where(
            totals['current_stock'] <= totals['reorder_trigger'], 
            np.ceil(totals['par_level'] - totals['current_stock']), 
            0
        )
        
        # Show only items to order
        final_orders = totals[totals['order_needed'] > 0][['item_name', 'current_stock', 'par_level', 'order_needed']]
        st.table(final_orders)
        
    except Exception as e:
        st.error(f"Format error: {e}. Use 'item, count, unit'")
