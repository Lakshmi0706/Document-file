import streamlit as st
import pandas as pd

# App title
st.title("Product Selector")

# Load the Excel file (update the name to match exactly what you uploaded)
EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    # Read the Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Remove any completely empty rows
    df = df.dropna(how='all')

    # Check if required columns exist
    required_columns = ['Module', 'Subcategory', 'Segment', 'Image_URL', 'Link']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        st.error(f"The Excel file is missing these required columns: {', '.join(missing_cols)}")
        st.stop()

    # Get unique values, removing NaN
    modules = df['Module'].dropna().unique()
    if len(modules) == 0:
        st.warning("No data found in the 'Module' column.")
        st.stop()

    # Select Module
    selected_module = st.selectbox("Select Module", sorted(modules))

    # Filter Subcategory
    subcats = df[df['Module'] == selected_module]['Subcategory'].dropna().unique()
    selected_subcat = st.selectbox("Select Subcategory", sorted(subcats))

    # Filter Segment
    segments = df[(df['Module'] == selected_module) & 
                  (df['Subcategory'] == selected_subcat)]['Segment'].dropna().unique()
    selected_segment = st.selectbox("Select Segment", sorted(segments))

    # Find the matching row
    result = df[(df['Module'] == selected_module) &
                (df['Subcategory'] == selected_subcat) &
                (df['Segment'] == selected_segment)]

    if result.empty:
        st.warning("No product found for this combination.")
    else:
        row = result.iloc[0]

        # Display Product Image
        st.image(row['Image_URL'], caption="Product Image", use_column_width=True)

        # Display Product Link
        link = row['Link']
        if pd.notna(link) and str(link).strip() != "":
            st.markdown(f"*Product Link:* [{link}]({link})")
        else:
            st.info("No link provided for this product.")

except FileNotFoundError:
    st.error(f"File '{EXCEL_FILE}' not found. Make sure the Excel file is uploaded to the repository with the exact name.")
except Exception as e:
    st.error(f"An error occurred while loading the data: {str(e)}")
