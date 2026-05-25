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
    # Ensure numeric columns are clean
    df['par_level'] = pd.to_numeric(df['par_level'], errors='coerce').fillna(0)
    df['reorder_trigger'] = pd.to_numeric(df['reorder_trigger'], errors='coerce').fillna(0)
    df['conversion_factor'] = pd.to_numeric(df['conversion_factor'], errors='coerce').fillna(1)
    return df

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Order Calculator", "View Master Database"])

if page == "View Master Database":
    st.title("📊 Master Database Settings")
    master = get_master()
    st.write("This is what the system uses for your Par Levels and Triggers.")
    st.dataframe(master)

elif page == "Order Calculator":
    st.title("📦 Commissary Inventory Manager")
    raw_data = st.text_area("Paste your inventory table here:", height=300)
    
    if st.button("Run Calculation"):
        try:
            # 1. Load Data
            data = io.StringIO(raw_data)
            df_in = pd.read_csv(data, sep='\t')
            df_in = df_in.rename(columns={'Item': 'item_name', 'Qty': 'qty', 'Qty2': 'qty2', 'Qty3': 'qty3'})
            df_in['item_name'] = df_in['item_name'].str.lower().str.strip()
            
            # 2. Melt and Agg
            df_melted = df_in.melt(id_vars=['item_name'], value_vars=['qty', 'qty2', 'qty3'], value_name='qty').dropna()
            totals = df_melted.groupby('item_name')['qty'].sum().reset_index()
            
            # 3. Merge with Master
            master = get_master()
            final = pd.merge(totals, master, on='item_name', how='inner')
            
            # 4. Calculate
            final['total_units'] = final['qty'] * final['conversion_factor']
            final['order_needed'] = np.where(
                final['total_units'] <= final['reorder_trigger'],
                np.ceil(final['par_level'] - final['total_units']),
                0
            )
            
            # 5. Display Result
            st.table(final[final['order_needed'] > 0][['item_name', 'total_units', 'par_level', 'order_needed']])
            
        except Exception as e:
            st.error(f"Format error: {e}")
