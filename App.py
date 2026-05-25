import streamlit as st
import pandas as pd
import io

# Set up page config
st.set_page_config(page_title="Restaurant Order Generator", layout="wide")

# 1. INITIALIZE MASTER ITEM DATA (The Backend)
# In a full production app, this could be saved to a CSV or database.
if 'items_df' not in st.session_state:
    # Starting data using your Focaccia example
    st.session_state.items_df = pd.DataFrame([
        {
            "Item Name": "Focaccia Bread",
            "Par Quantity (Trays)": 12.0,
            "Trigger Level (Trays)": 11.1,
            "Conversion Rate (Slices/Tray)": 16.0
        }
    ])

# 2. SIDEBAR NAVIGATION
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["📋 Staff Portal", "⚙️ Manager Dashboard"])

# ---------------------------------------------------------
# PAGE 1: STAFF PORTAL
# ---------------------------------------------------------
if page == "📋 Staff Portal":
    st.title("📋 Restaurant365 Order Generator")
    st.write("Copy the entire inventory report from R365 and paste it below.")
    
    # Text area for staff to paste raw data
    pasted_data = st.text_area("Paste R365 Inventory Dump Here:", height=300, placeholder="Item Name\tQuantity\tLocation...")
    
    if st.button("🚀 Generate Order List", type="primary"):
        if not pasted_data.strip():
            st.error("Please paste some data first!")
        else:
            try:
                # Convert pasted text into a dataframe (assuming Tab-separated from Excel/R365)
                # If R365 uses commas, we can adjust 'sep' to ','
                raw_df = pd.read_csv(io.StringIO(pasted_data), sep="\t")
                
                # Standardize column names to fix potential spacing issues
                raw_df.columns = raw_df.columns.str.strip()
                
                # Dynamic column matching based on typical R365 exports
                # Looks for columns containing 'item' or 'name', and 'qty' or 'count'
                item_col = next((c for c in raw_df.columns if 'item' in c.lower() or 'name' in c.lower()), raw_df.columns[0])
                qty_col = next((c for c in raw_df.columns if 'qty' in c.lower() or 'count' in c.lower() or 'on hand' in c.lower()), raw_df.columns[1])
                
                # Clean up the staff input data
                staff_inventory = raw_df[[item_col, qty_col]].copy()
                staff_inventory.columns = ["Item Name", "Current Count"]
                staff_inventory["Current Count"] = pd.to_numeric(staff_inventory["Current Count"], errors='coerce').fillna(0)
                
                # Group by Item Name to combine duplicate items across different locations
                combined_inventory = staff_inventory.groupby("Item Name", as_index=False)["Current Count"].sum()
                
                # Merge with Manager's master rules
                master_rules = st.session_state.items_df
                merged_df = pd.merge(master_rules, combined_inventory, on="Item Name", how="inner")
                
                # RUN THE MATH
                # 1. Convert current count to Par Units (e.g., slices divided by 16 = trays)
                merged_df["Current Stock (Converted Units)"] = merged_df["Current Count"] / merged_df["Conversion Rate (Slices/Tray)"]
                
                # 2. Filter for items that fall below or equal to the trigger level
                order_needed = merged_df[merged_df["Current Stock (Converted Units)"] <= merged_df["Trigger Level (Trays)"]].copy()
                
                # 3. Calculate how much to order to get back to Par
                order_needed["Order Quantity (Trays)"] = order_needed["Par Quantity (Trays)"] - order_needed["Current Stock (Converted Units)"]
                
                # Display Results
                st.success("🎯 Order List Generated Successfully!")
                
                if order_needed.empty:
                    st.balloons()
                    st.info("Everything is fully stocked! No items need to be ordered right now.")
                else:
                    # Clean up table for display
                    display_df = order_needed[["Item Name", "Current Count", "Current Stock (Converted Units)", "Par Quantity (Trays)", "Order Quantity (Trays)"]]
                    display_df.columns = ["Item Name", "Current Count (Slices)", "Current Stock (Trays)", "Target Par (Trays)", "Amount To Order (Trays)"]
                    
                    st.dataframe(display_df.style.format({
                        "Current Stock (Trays)": "{:.2f}",
                        "Amount To Order (Trays)": "{:.2f}"
                    }), use_container_width=True)
                    
            except Exception as e:
                st.error(f"Format Error: Could not parse the pasted text. Make sure you included the column headers from R365. Error details: {e}")

# ---------------------------------------------------------
# PAGE 2: MANAGER DASHBOARD (Backend Settings)
# ---------------------------------------------------------
elif page == "⚙️ Manager Dashboard":
    st.title("⚙️ Manager Backend Settings")
    
    # Simple password protection
    password = st.text_input("Enter Manager Password to edit settings:", type="password")
    
    if password == "shopmanager123": # Change this to whatever password you want
        st.success("Access Granted")
        
        st.subheader("Current Master Item Rules")
        st.write("Adjust pars, triggers, and conversion rates directly in the table below:")
        
        # Make the dataframe editable!
        edited_df = st.data_editor(st.session_state.items_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Save Settings", type="primary"):
            st.session_state.items_df = edited_df
            st.toast("Settings saved successfully!")
            
    elif password:
        st.error("Incorrect Password.")
