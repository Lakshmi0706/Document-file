import streamlit as st
import pandas as pd

st.set_page_config(page_title="Product Selector", layout="centered")

# Compact modern styling
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
    .placeholder {
        font-size: 16px;
        text-align: center;
        color: #95a5a6;
        font-style: italic;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">Product Selector</p>', unsafe_allow_html=True)

EXCEL_FILE = "TRAIL DOC.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE)
    df = df.dropna(how='all')

    # Exact column names - change only if yours are different
    dept_col = "Department"
    super_col = "Super category"
    cat_col = "Category"
    subcat_col = "Subcategory"
    seg_col = "Segment"
    image_col = "Image"
    link_col = "Link"
    def_col = "Definition"
    default_sub_col = "Default values subcategory"
    default_seg_col = "Default values segment"

    required = [dept_col, super_col, cat_col, subcat_col, seg_col, image_col, link_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    df = df.dropna(subset=required)

    # Compact horizontal dropdowns
    cols = st.columns(5)
    labels = ["Department", "Super Category", "Category", "Subcategory", "Segment"]
    col_names = [dept_col, super_col, cat_col, subcat_col, seg_col]

    selections = []
    filtered_df = df.copy()

    for i, (label, col_name) in enumerate(zip(labels, col_names)):
        with cols[i]:
            st.markdown(f'<p class="label-style">{label}</p>', unsafe_allow_html=True)
            options = sorted(filtered_df[col_name].dropna().unique().tolist())
            if options:  # Fixed: check if list is not empty
                selected = st.selectbox("", options, key=f"select_{i}", label_visibility="collapsed")
            else:
                selected = None
                st.selectbox("", ["No options"], disabled=True, key=f"select_{i}", label_visibility="collapsed")
            selections.append(selected)
            if selected is not None:
                filtered_df = filtered_df[filtered_df[col_name] == selected]

    if filtered_df.empty:
        st.info("No product found for this selection.")
    else:
        row = filtered_df.iloc[0]

        # Always show Definition
        definition = row.get(def_col)
        if pd.notna(definition) and str(definition).strip():
            st.markdown(f'<div class="definition">{definition}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="placeholder">No definition provided.</div>', unsafe_allow_html=True)

        # Always show Default Values
        default_sub = row.get(default_sub_col)
        default_seg = row.get(default_seg_col)
        st.markdown('<div class="default-values">', unsafe_allow_html=True)
        st.markdown("*Default Values:*")
        sub_text = default_sub if pd.notna(default_sub) and str(default_sub).strip() else "Not specified"
        seg_text = default_seg if pd.notna(default_seg) and str(default_seg).strip() else "Not specified"
        st.write(f"• Subcategory: {sub_text}")
        st.write(f"• Segment: {seg_text}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Image
        image_url = row.get(image_col)
        if pd.notna(image_url) and str(image_url).strip().startswith('http'):
            st.markdown("<div style='text-align: center; margin: 25px 0;'>", unsafe_allow_html=True)
            st.image(str(image_url).strip(), width=500)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="placeholder">No image available.</div>', unsafe_allow_html=True)

        # Link
        link = row.get(link_col)
        if pd.notna(link) and str(link).strip():
            link_str = str(link).strip()
            st.markdown(f"<div style='text-align: center; font-size: 18px; margin: 20px 0;'><strong>Product Link:</strong> <a href='{link_str}' target='_blank'>{link_str}</a></div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="placeholder">No product link provided.</div>', unsafe_allow_html=True)

except FileNotFoundError:
    st.error(f"File '{EXCEL_FILE}' not found in the repository.")
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
