import streamlit as st
import pandas as pd

st.set_page_config(page_title="Product Selector", layout="centered")

# Modern compact CSS
st.markdown("""
<style>
    .big-font {
        font-size: 42px !important;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 30px;
    }
    .label-style {
        font-size: 16px !important;
        font-weight: bold;
        color: #424242;
        text-align: center;
        margin-bottom: 8px;
    }
    /* Make dropdowns compact and show full text */
    .stSelectbox > div > div {
        width: 100% !important;
    }
    select {
        font-size: 15px !important;
        padding: 8px !important;
    }
    .definition {
        font-size: 18px;
        text-align: center;
        margin: 20px 0;
        color: #2c3e50;
        font-style: italic;
    }
    .default-values {
        font-size: 16px;
        text-align: center;
        color: #27ae60;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">Product Selector</p>', unsafe_allow_html=True)

EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE)
    df = df.dropna(how='all')
    df = df.dropna(subset=['Department', 'Super category', 'Category', 'Subcategory', 'Segment'])

    # Compact horizontal layout with equal spacing
    cols = st.columns(5)

    labels = ["Department", "Super Category", "Category", "Subcategory", "Segment"]
    selections = []

    for i, label in enumerate(labels):
        with cols[i]:
            st.markdown(f'<p class="label-style">{label}</p>', unsafe_allow_html=True)
            unique_vals = sorted(df[label.replace(" ", "_") if " " in label else label].unique())
            if i == 0:
                selected = st.selectbox("", unique_vals, key="0", label_visibility="collapsed")
            else:
                # Filter based on previous selections
                filtered = df
                for j in range(i):
                    col_name = labels[j].replace(" ", "_") if " " in labels[j] else labels[j]
                    filtered = filtered[filtered[col_name] == selections[j]]
                unique_vals = sorted(filtered[label.replace(" ", "_") if " " in label else label].unique())
                selected = st.selectbox("", unique_vals, key=str(i), label_visibility="collapsed")
            selections.append(selected)

    selected_dept, selected_super, selected_cat, selected_subcat, selected_segment = selections

    # Find product
    result = df[(df['Department'] == selected_dept) &
                (df['Super category'] == selected_super) &
                (df['Category'] == selected_cat) &
                (df['Subcategory'] == selected_subcat) &
                (df['Segment'] == selected_segment)]

    if result.empty:
        st.info("No product found for this selection.")
    else:
        row = result.iloc[0]

        # Definition
        definition = row.get('Definition')
        if pd.notna(definition):
            st.markdown(f'<div class="definition">{definition}</div>', unsafe_allow_html=True)

        # Default values
        default_sub = row.get('Default values subcategory')
        default_seg = row.get('Default values segment')
        if pd.notna(default_sub) or pd.notna(default_seg):
            st.markdown('<div class="default-values">', unsafe_allow_html=True)
            st.markdown("*Default Values:*")
            if pd.notna(default_sub):
                st.write(f"• Subcategory: {default_sub}")
            if pd.notna(default_seg):
                st.write(f"• Segment: {default_seg}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Image (medium size, centered)
        image_url = row['Image']
        if pd.notna(image_url) and str(image_url).strip().startswith('http'):
            st.markdown("<div style='text-align: center; margin: 25px 0;'>", unsafe_allow_html=True)
            st.image(str(image_url).strip(), width=500)
            st.markdown("</div>", unsafe_allow_html=True)

        # Link
        link = row['Link']
        if pd.notna(link):
            link_str = str(link).strip()
            if link_str:
                st.markdown(f"<div style='text-align: center; font-size: 18px;'><strong>Product Link:</strong> <a href='{link_str}' target='_blank'>{link_str}</a></div>", unsafe_allow_html=True)

except Exception as e:
    st.error("Error loading data. Check Excel file and column names.")
