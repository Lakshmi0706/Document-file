import streamlit as st
import pandas as pd

# App title
st.title("Product Selector")

# Excel file name (exact match)
EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    # Load the Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Clean data: remove completely empty rows
    df = df.dropna(how='all')

    # Required columns (exact names from your file)
    required_columns = [
        'Department', 'Super category', 'Category', 'Subcategory', 'Segment',
        'Image', 'Link'
    ]

    # Check if all required columns exist
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"The Excel file is missing these required columns: {', '.join(missing_cols)}")
        st.stop()

    # Remove rows with missing key values
    df = df.dropna(subset=['Department', 'Super category', 'Category', 'Subcategory', 'Segment'])

    # === Dropdowns in hierarchical order ===

    # 1. Department
    departments = sorted(df['Department'].unique())
    selected_dept = st.selectbox("Select Department", departments)

    # 2. Super category
    super_cats = sorted(df[df['Department'] == selected_dept]['Super category'].unique())
    selected_super = st.selectbox("Select Super Category", super_cats)

    # 3. Category
    categories = sorted(df[(df['Department'] == selected_dept) & 
                           (df['Super category'] == selected_super)]['Category'].unique())
    selected_cat = st.selectbox("Select Category", categories)

    # 4. Subcategory
    subcats = sorted(df[(df['Department'] == selected_dept) & 
                        (df['Super category'] == selected_super) & 
                        (df['Category'] == selected_cat)]['Subcategory'].unique())
    selected_subcat = st.selectbox("Select Subcategory", subcats)

    # 5. Segment
    segments = sorted(df[(df['Department'] == selected_dept) & 
                         (df['Super category'] == selected_super) & 
                         (df['Category'] == selected_cat) & 
                         (df['Subcategory'] == selected_subcat)]['Segment'].unique())
    selected_segment = st.selectbox("Select Segment", segments)

    # === Find the selected product ===
    result = df[(df['Department'] == selected_dept) &
                (df['Super category'] == selected_super) &
                (df['Category'] == selected_cat) &
                (df['Subcategory'] == selected_subcat) &
                (df['Segment'] == selected_segment)]

    if result.empty:
        st.warning("No product found for this combination.")
    else:
        row = result.iloc[0]

        # Display Image
        image_url = row['Image']
        if pd.notna(image_url) and str(image_url).strip() != "":
            st.image(image_url, caption="Product Image", use_column_width=True)
        else:
            st.info("No image available.")

        # Display Link
        link = row['Link']
        if pd.notna(link) and str(link).strip() != "":
            st.markdown(f"*Product Link:* [{link}]({link})")
        else:
            st.info("No link provided.")

        # Display Definition (if available)
        definition = row.get('Definition', None)
        if pd.notna(definition) and str(definition).strip() != "":
            st.markdown("*Definition:*")
            st.write(definition)

        # Optional: Show default values
        default_sub = row.get('Default values subcategory', None)
        default_seg = row.get('Default values segment', None)
        if pd.notna(default_sub) or pd.notna(default_seg):
            st.markdown("*Default Values:*")
            if pd.notna(default_sub):
                st.write(f"- Subcategory: {default_sub}")
            if pd.notna(default_seg):
                st.write(f"- Segment: {default_seg}")

except FileNotFoundError:
    st.error(f"File '{EXCEL_FILE}' not found. Please ensure it's uploaded correctly.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
