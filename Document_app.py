
import streamlit as st
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(page_title="Product Selector", layout="centered")

# ------------------------------------------------------------
# Styling (make sure this triple-quoted string is CLOSED)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Data loader (upload OR fallback to file in repo root)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_excel(file_like_or_path):
    """Read Excel into DataFrame."""
    return pd.read_excel(file_like_or_path)

# Optional uploader (you can remove this block if you want only local file)
uploaded = st.file_uploader(
    "Upload Excel (optional). If not uploaded, app will use 'TRAIL DOC.xlsx' from the repo.",
    type=["xlsx"]
)

try:
    if uploaded is not None:
        df = load_excel(uploaded)
        st.caption("📄 Data source: Uploaded file")
    else:
        BASE_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
        EXCEL_FILE = BASE_DIR / "TRAIL DOC.xlsx"
        df = load_excel(EXCEL_FILE)
        st.caption(f"📄 Data source: {EXCEL_FILE.name}")

    # --------------------------------------------------------
    # Clean/normalize data
    # --------------------------------------------------------
    # Drop fully empty rows
    df = df.dropna(how="all")

    # Normalize headers (strip spaces)
    df.columns = df.columns.astype(str).str.strip()

    # Header alias mapping (tolerates minor header variations)
    header_alias = {
        "Key Word": "Key Word",
        "Keyword": "Key Word",
        "KeyWord": "Key Word",

        "Placement": "Placement",

        "Department": "Department",
        "Dept": "Department",

        "Super category": "Super category",
        "Super Category": "Super category",
        "Super cat": "Super category",
        "Supercat": "Super category",

        "Category": "Category",
        "Cat": "Category",

        "Subcategory": "Subcategory",
        "Sub Category": "Subcategory",
        "Sub cat": "Subcategory",
        "Subcat": "Subcategory",

        "Segment": "Segment",

        "Image": "Image",
        "Link": "Link",
        "Definition": "Definition",
        "Default values subcategory": "Default values subcategory",
        "Default values segment": "Default values segment",
    }

    # Apply alias mapping (case-insensitive)
    renamed = {}
    lc_map = {k.lower(): v for k, v in header_alias.items()}
    for col in list(df.columns):
        key = col.strip()
        if key in header_alias:
            renamed[col] = header_alias[key]
        elif key.lower() in lc_map:
            renamed[col] = lc_map[key.lower()]
    if renamed:
        df = df.rename(columns=renamed)

    # Canonical column names
    keyword_col = "Key Word"
    placement_col = "Placement"
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

    # Validate only the hierarchy columns (do NOT require Image/Link)
    required_hierarchy = [
        keyword_col, placement_col, dept_col, super_col,
        cat_col, subcat_col, seg_col
    ]
    missing = [c for c in required_hierarchy if c not in df.columns]
    if missing:
        st.error(f"Missing required columns in Excel: {missing}")
        st.stop()

    # Drop rows missing any hierarchy column (these cannot filter properly)
    df = df.dropna(subset=required_hierarchy, how="any")

    # Trim whitespace inside the hierarchy columns
    for c in required_hierarchy:
        df[c] = df[c].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # --------------------------------------------------------
    # UI: Multi-select + searchable dropdowns (cascading)
    # --------------------------------------------------------
    labels = [
        "Key Word",
        "Placement",
        "Department",
        "Super Category",
        "Category",
        "Subcategory",
        "Segment"
    ]
    col_names = [
        keyword_col,
        placement_col,
        dept_col,
        super_col,
        cat_col,
        subcat_col,
        seg_col
    ]

    cols = st.columns(len(labels))
    filtered_df = df.copy()
    selections = []

    for i, (label, col_name) in enumerate(zip(labels, col_names)):
        with cols[i]:
            st.markdown(f"<p class='label-style'>{label}</p>", unsafe_allow_html=True)

            # Options from current filtered_df to keep cascading behavior
            options = sorted(
                filtered_df[col_name].dropna().astype(str).str.strip().unique().tolist()
            )

            if options:
                selected = st.multiselect(
                    label="",
                    options=options,
                    default=[],
                    key=f"select_{i}",
                    placeholder="Type to search…",
                    label_visibility="collapsed"
                )
            else:
                selected = []
                st.multiselect(
                    label="", options=["No options"], default=["No options"],
                    key=f"select_{i}_disabled", disabled=True,
                    label_visibility="collapsed"
                )

            selections.append(selected)

            # Apply filter only if user selected something at this level
            if selected:
                filtered_df = filtered_df[
                    filtered_df[col_name].astype(str).str.strip().isin(selected)
                ]

    # Small debug panel to help diagnose data issues
    with st.expander("🔎 Debug: unique counts per level in current result"):
        for lbl, coln in zip(labels, col_names):
            st.write(f"{lbl}: {filtered_df[coln].dropna().astype(str).str.strip().nunique()} unique values")

    # --------------------------------------------------------
    # Result panel (first matching record)
    # --------------------------------------------------------
    total_matches = len(filtered_df)
    if total_matches == 0:
        st.info("No product found for this selection.")
    else:
        st.caption(f"🔎 Matches found: {total_matches}")

        row = filtered_df.iloc[0]

        # Definition
        definition = row.get(def_col)
        if pd.notna(definition) and str(definition).strip():
            st.markdown(f"<div class='definition'>{definition}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='placeholder'>No definition provided.</div>", unsafe_allow_html=True)

        # Default values
        default_sub = row.get(default_sub_col)
        default_seg = row.get(default_seg_col)
        st.markdown("<div class='default-values'>", unsafe_allow_html=True)
        st.markdown("**Default Values:**")
        sub_text = default_sub if pd.notna(default_sub) and str(default_sub).strip() else "Not specified"
        seg_text = default_seg if pd.notna(default_seg) and str(default_seg).strip() else "Not specified"
        st.write(f"• Subcategory: {sub_text}")
        st.write(f"• Segment: {seg_text}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Image (supports http/https; optionally show local file if path exists)
        image_url = row.get(image_col)
        if pd.notna(image_url):
            image_str = str(image_url).strip()
            if image_str.startswith(("http://", "https://")):
                st.markdown("<div style='text-align: center; margin: 25px 0;'>", unsafe_allow_html=True)
                st.image(image_str, width=500)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # if it's a local path relative to repo
                local_path = Path(image_str)
                if local_path.exists():
                    st.markdown("<div style='text-align: center; margin: 25px 0;'>", unsafe_allow_html=True)
                    st.image(str(local_path), width=500)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='placeholder'>No image available.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='placeholder'>No image available.</div>", unsafe_allow_html=True)

        # Link
        link = row.get(link_col)
        if pd.notna(link) and str(link).strip():
            link_str = str(link).strip()
            st.markdown(
                f"<div style='text-align: center; font-size: 18px; margin: 20px 0;'>"
                f"<strong>Product Link:</strong> "
                f"{link_str}{link_str}</a>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div class='placeholder'>No product link provided.</div>", unsafe_allow_html=True)

except FileNotFoundError:
    st.error("File 'TRAIL DOC.xlsx' not found next to the script. Upload it via the widget above or commit it to the repository root.")
except Exception as e:
    st.error(f"Error loading data: {e}")
