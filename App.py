import streamlit as st
import pandas as pd


GSHEET_URL = "https://docs.google.com/spreadsheets/d/10YYPKcu0IPD1S4XBlzY4Vf2lM5likd5Rd_FYq7Owh1E/edit?usp=drivesdk"

def get_csv_url(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    return url

# Load live pars from Google Sheets
@st.cache_data(ttl=5)  # Syncs with your sheet every 5 seconds
def load_master_database():
    try:
        csv_url = get_csv_url(GSHEET_URL)
        df = pd.read_csv(csv_url)
        df.columns = [col.lower().strip() for col in df.columns]
        df['par_level'] = pd.to_numeric(df['par_level'], errors='coerce').fillna(0)
        df['reorder_trigger'] = pd.to_numeric(df['reorder_trigger'], errors='coerce').fillna(0)
        df['item_name'] = df['item_name'].astype(str).str.lower().str.strip()
        return df
    except Exception as e:
        return pd.DataFrame(columns=['item_name', 'par_level', 'reorder_trigger'])

# --- APP LAYOUT ---
st.set_page_config(page_title="Shop Order Guide", page_icon="📦", layout="centered")

st.title("📦 Shop Order & Par Guide")
st.write("This portal automatically compares your current inventory counts against the master par levels saved in your Google Sheet.")

# --- MANAGER VIEW ---
with st.sidebar:
    st.header("🛠️ Manager Settings")
    password = st.text_input("Enter Manager Password:", type="password")
    if password == "shopmanager123":
        st.success("Connected to Database!")
        st.markdown(f"[✏️ Open Live Google Sheet to Edit Pars]({GSHEET_URL})")
        st.subheader("Current Master Pars:")
        st.dataframe(load_master_database(), use_container_width=True)

st.divider()

# --- STAFF CALCULATOR ---
st.subheader("📋 Step 1: Upload Current Counts")
uploaded_file = st.file_uploader("Drop today's inventory sheet here (Excel or CSV)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Read uploaded counts
        if uploaded_file.name.endswith('.csv'):
            inv_df = pd.read_csv(uploaded_file)
        else:
            inv_df = pd.read_excel(uploaded_file)
            
        # Clean uploaded headers
        inv_df.columns = [col.lower().strip() for col in inv_df.columns]
        
        # Standardize items
        if 'item_name' in inv_df.columns and 'in_stock' in inv_df.columns:
            inv_df['item_name'] = inv_df['item_name'].astype(str).str.lower().str.strip()
            inv_df['in_stock'] = pd.to_numeric(inv_df['in_stock'], errors='coerce').fillna(0)
            
            # Pull fresh data from Google Sheets
            master_sheet = load_master_database()
            
            if master_sheet.empty:
                st.error("Could not read data from Google Sheets. Make sure your link is correct and general access is set to 'Anyone with link'.")
            else:
                # Compare Uploaded Stock against Google Sheet Master Pars
                merged = pd.merge(inv_df, master_sheet, on='item_name', how='inner')
                
                # Math calculation for ordering
                merged['order_qty'] = merged.apply(
                    lambda row: max(0, row['par_level'] - row['in_stock']) if row['in_stock'] <= row['reorder_trigger'] else 0, 
                    axis=1
                )
                
                # Filter out items that don't need ordering
                order_sheet = merged[merged['order_qty'] > 0][['item_name', 'in_stock', 'par_level', 'order_qty']]
                
                st.subheader("🛒 Step 2: Your Suggested Order Sheet")
                if not order_sheet.empty:
                    # Capitalize for clean display
                    order_sheet['item_name'] = order_sheet['item_name'].str.title()
                    st.dataframe(order_sheet, use_container_width=True)
                    
                    # One-click download button for ordering
                    csv = order_sheet.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download This Order List", csv, "needed_orders.csv", "text/csv")
                else:
                    st.success("✅ Everything is perfectly stocked! No orders needed right now.")
        else:
            st.error("Your uploaded file must have columns named exactly: 'item_name' and 'in_stock'")
                
    except Exception as e:
        st.error(f"Error compiling order list: {e}")
