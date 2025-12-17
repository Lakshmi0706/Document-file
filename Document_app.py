import streamlit as st
import pandas as pd

# Page config for better look
st.set_page_config(page_title="Product Selector", layout="centered")

# Custom CSS for beautiful fonts, spacing, and image sizing
st.markdown("""
<style>
    .big-font {
        font-size: 50px !important;
        font-weight: bold;
        color: #2E86C1;
        text-align: center;
        margin-bottom: 30px;
    }
    .select-label {
        font-size: 20px !important;
        font-weight: bold;
        color: #1B4F72;
    }
    .product-info {
        font-size: 18px;
        line-height: 1.6;
        margin-top: 20px;
    }
    .stSelectbox > div > div {
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Title with custom style
st.markdown('<p class="big-font">Product Selector</p>', unsafe_allow_html=True)

EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE)
    df = df.dropna(how='all')
    
    required_columns = ['Department', 'Super category', 'Category', 'Subcategory', 'Segment', 'Image', 'Link']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {', '.join(missing_cols)}")
        st.stop()
    
    df = df.dropna(subset=['Department', 'Super category', 'Category', 'Subcategory', 'Segment'])

    # Dropdowns with custom labels
    st.markdown('<p class="select-label">Select Department</p>', unsafe_allow_html=True)
    departments = sorted(df['Department'].unique())
    selected_dept = st.selectbox("", departments, label_visibility="collapsed")

    st.markdown('<p class="select-label">Select Super Category</p>', unsafe_allow_html=True)
    super_cats = sorted(df[df['Department'] == selected_dept]['Super category'].unique())
    selected_super = st.selectbox("", super_cats, label_visibility="collapsed")

    st.markdown('<p class="select-label">Select Category</p>', unsafe_allow_html=True)
    categories = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super)]['Category'].unique())
    selected_cat = st.selectbox("", categories, label_visibility="collapsed")

    st.markdown('<p class="select-label">Select Subcategory</p>', unsafe_allow_html=True)
    subcats = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super) & (df['Category'] == selected_cat)]['Subcategory'].unique())
    selected_subcat = st.selectbox("", subcats, label_visibility="collapsed")

    st.markdown('<p class="select-label">Select Segment</p>', unsafe_allow_html=True)
    segments = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super) & (df['Category'] == selected_cat) & (df['Subcategory'] == selected_subcat)]['Segment'].unique())
    selected_segment = st.selectbox("", segments, label_visibility="collapsed")

    # Result
    result = df[(df['Department'] == selected_dept) &
                (df['Super category'] == selected_super) &
                (df['Category'] == selected_cat) &
                (df['Subcategory'] == selected_subcat) &
                (df['Segment'] == selected_segment)]

    if result.empty:
        st.warning("No product found for this selection.")
    else:
        row = result.iloc[0]

        # Centered and resized image (max 600px height to fit screen better)
        image_url = row['Image']
        if pd.notna(image_url):
            image_url = str(image_url).strip()
            if image_url.startswith('http'):
                st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
                st.image(image_url, caption="Product Image", width=500)  # Adjust width as needed (400-600 looks great)
                st.markdown("</div>", unsafe_allow_html=True)

        # Product info with nice formatting
        st.markdown('<div class="product-info">', unsafe_allow_html=True)

        link = row['Link']
        if pd.notna(link):
            link = str(link).strip()
            if link:
                st.markdown(f"*Product Link:* [{link}]({link})")

        definition = row.get('Definition', None)
        if pd.notna(definition) and str(definition).strip():
            st.markdown("*Definition:*")
            st.write(definition)

        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
