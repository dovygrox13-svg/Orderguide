import streamlit as st
import pandas as pd
import io

# --- 🔗 LINK YOUR GOOGLE SHEET ---
GSHEET_URL = "PASTE_YOUR_GOOGLE_SHEET_URL_HERE" # Put your link here again!

def get_csv_url(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    return url

@st.cache_data(ttl=5)
def load_master_database():
    try:
        csv_url = get_csv_url(GSHEET_URL)
        df = pd.read_csv(csv_url)
        df.columns = [col.lower().strip() for col in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['item_name', 'par_level', 'reorder_trigger'])

st.title("📦 Fast-Paste Order Guide")

# Password Protection
password = st.text_input("Manager Password:", type="password")
if password == "shopmanager123":
    st.sidebar.success("Logged In!")
    st.sidebar.markdown(f"[✏️ Edit Pars in Google Sheets]({GSHEET_URL})")

st.subheader("📋 Paste Raw Inventory Data")
st.write("Format: **item_name, in_stock** (one per line)")
raw_data = st.text_area("Paste your list here:", height=200, placeholder="Milk, 2\nBread, 5\nEggs, 1")

if st.button("Run Calculation"):
    try:
        # Convert pasted text into a table
        data = io.StringIO(raw_data)
        inv_df = pd.read_csv(data, names=['item_name', 'in_stock'], header=None)
        inv_df['item_name'] = inv_df['item_name'].str.lower().str.strip()
        inv_df['in_stock'] = pd.to_numeric(inv_df['in_stock'], errors='coerce')
        
        master = load_master_database()
        merged = pd.merge(inv_df, master, on='item_name', how='inner')
        
        merged['order_qty'] = merged.apply(
            lambda row: max(0, row['par_level'] - row['in_stock']) if row['in_stock'] <= row['reorder_trigger'] else 0, axis=1
        )
        
        results = merged[merged['order_qty'] > 0][['item_name', 'in_stock', 'par_level', 'order_qty']]
        
        st.subheader("🛒 Suggested Order")
        st.table(results)
    except:
        st.error("Make sure you paste as 'Item, Count' (e.g., Milk, 5)")
