import streamlit as st
import pandas as pd

st.title("Product Selector")

EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE)
    df = df.dropna(how='all')
    
    required_columns = [
        'Department', 'Super category', 'Category', 'Subcategory', 'Segment',
        'Image', 'Link'
    ]
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"The Excel file is missing these required columns: {', '.join(missing_cols)}")
        st.stop()
    
    df = df.dropna(subset=['Department', 'Super category', 'Category', 'Subcategory', 'Segment'])

    # Dropdowns
    departments = sorted(df['Department'].unique())
    selected_dept = st.selectbox("Select Department", departments)

    super_cats = sorted(df[df['Department'] == selected_dept]['Super category'].unique())
    selected_super = st.selectbox("Select Super Category", super_cats)

    categories = sorted(df[(df['Department'] == selected_dept) & 
                           (df['Super category'] == selected_super)]['Category'].unique())
    selected_cat = st.selectbox("Select Category", categories)

    subcats = sorted(df[(df['Department'] == selected_dept) & 
                        (df['Super category'] == selected_super) & 
                        (df['Category'] == selected_cat)]['Subcategory'].unique())
    selected_subcat = st.selectbox("Select Subcategory", subcats)

    segments = sorted(df[(df['Department'] == selected_dept) & 
                         (df['Super category'] == selected_super) & 
                         (df['Category'] == selected_cat) & 
                         (df['Subcategory'] == selected_subcat)]['Segment'].unique())
    selected_segment = st.selectbox("Select Segment", segments)

    # Find product
    result = df[(df['Department'] == selected_dept) &
                (df['Super category'] == selected_super) &
                (df['Category'] == selected_cat) &
                (df['Subcategory'] == selected_subcat) &
                (df['Segment'] == selected_segment)]

    if result.empty:
        st.warning("No product found for this combination.")
    else:
        row = result.iloc[0]

        # Improved Image Display
        image_url = row['Image']
        if pd.notna(image_url):
            image_url = str(image_url).strip()
            if image_url:
                try:
                    st.image(image_url, caption="Product Image", use_column_width=True)
                except Exception:
                    st.error("Image could not be loaded (invalid or inaccessible URL).")
            else:
                st.info("No image URL provided.")
        else:
            st.info("No image available.")

        # Link
        link = row['Link']
        if pd.notna(link):
            link = str(link).strip()
            if link:
                st.markdown(f"*Product Link:* [{link}]({link})")

        # Definition
        definition = row.get('Definition', None)
        if pd.notna(definition) and str(definition).strip():
            st.markdown("*Definition:*")
            st.write(definition)

        # Default values
        default_sub = row.get('Default values subcategory', None)
        default_seg = row.get('Default values segment', None)
        if pd.notna(default_sub) or pd.notna(default_seg):
            st.markdown("*Default Values:*")
            if pd.notna(default_sub):
                st.write(f"- Subcategory: {default_sub}")
            if pd.notna(default_seg):
                st.write(f"- Segment: {default_seg}")

except FileNotFoundError:
    st.error(f"File '{EXCEL_FILE}' not found.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
