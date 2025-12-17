import streamlit as st
import pandas as pd

# Page setup
st.set_page_config(page_title="Product Selector", layout="centered")

# Custom CSS for full dropdown text, smaller image, and beauty
st.markdown("""
<style>
    .big-font {
        font-size: 50px !important;
        font-weight: bold;
        color: #2E86C1;
        text-align: center;
        margin-bottom: 40px;
    }
    .select-label {
        font-size: 18px !important;
        font-weight: bold;
        color: #1B4F72;
        margin-bottom: 5px;
        text-align: center;
    }
    /* Force dropdowns to show full long text */
    .stSelectbox > div > div > div {
        width: 100% !important;
    }
    select {
        width: 100% !important;
    }
    .product-info {
        font-size: 20px;
        line-height: 1.6;
        margin: 20px 0;
        text-align: center;
        font-weight: bold;
    }
    .definition-text {
        font-size: 18px;
        margin: 20px 0;
        text-align: center;
        font-style: italic;
        color: #34495E;
    }
    .default-values {
        font-size: 16px;
        margin: 15px 0;
        text-align: center;
        color: #27AE60;
    }
</style>
""", unsafe_allow_html=True)

# Title
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

    # Horizontal dropdowns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown('<p class="select-label">Department</p>', unsafe_allow_html=True)
        departments = sorted(df['Department'].unique())
        selected_dept = st.selectbox("", departments, key="dept", label_visibility="collapsed")

    with col2:
        st.markdown('<p class="select-label">Super Category</p>', unsafe_allow_html=True)
        super_cats = sorted(df[df['Department'] == selected_dept]['Super category'].unique())
        selected_super = st.selectbox("", super_cats, key="super", label_visibility="collapsed")

    with col3:
        st.markdown('<p class="select-label">Category</p>', unsafe_allow_html=True)
        categories = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super)]['Category'].unique())
        selected_cat = st.selectbox("", categories, key="cat", label_visibility="collapsed")

    with col4:
        st.markdown('<p class="select-label">Subcategory</p>', unsafe_allow_html=True)
        subcats = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super) & (df['Category'] == selected_cat)]['Subcategory'].unique())
        selected_subcat = st.selectbox("", subcats, key="subcat", label_visibility="collapsed")

    with col5:
        st.markdown('<p class="select-label">Segment</p>', unsafe_allow_html=True)
        segments = sorted(df[(df['Department'] == selected_dept) & (df['Super category'] == selected_super) & (df['Category'] == selected_cat) & (df['Subcategory'] == selected_subcat)]['Segment'].unique())
        selected_segment = st.selectbox("", segments, key="seg", label_visibility="collapsed")

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

        # Definition first
        definition = row.get('Definition', None)
        if pd.notna(definition) and str(definition).strip():
            st.markdown('<div class="definition-text">', unsafe_allow_html=True)
            st.write(definition)
            st.markdown('</div>', unsafe_allow_html=True)

        # Default values (now shown!)
        default_sub = row.get('Default values subcategory', None)
        default_seg = row.get('Default values segment', None)
        if pd.notna(default_sub) or pd.notna(default_seg):
            st.markdown('<div class="default-values">', unsafe_allow_html=True)
            st.markdown("*Default Values:*")
            if pd.notna(default_sub):
                st.write(f"• Subcategory: {default_sub}")
            if pd.notna(default_seg):
                st.write(f"• Segment: {default_seg}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Smaller centered image (450px - fits perfectly without scrolling)
        image_url = row['Image']
        if pd.notna(image_url):
            image_url = str(image_url).strip()
            if image_url.startswith('http'):
                st.markdown("<div style='text-align: center; margin: 20px 0;'>", unsafe_allow_html=True)
                st.image(image_url, width=450)
                st.markdown("</div>", unsafe_allow_html=True)

        # Link at the bottom
        link = row['Link']
        if pd.notna(link):
            link = str(link).strip()
            if link:
                st.markdown('<div class="product-info">', unsafe_allow_html=True)
                st.markdown(f"*Product Link:* [{link}]({link})")
                st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
