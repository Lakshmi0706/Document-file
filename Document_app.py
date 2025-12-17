
# app.py
# -----------------------------------------------------------
# Upload Excel -> Map columns -> Select Module/Sub-Category/
# Segment/Product -> Show image & definition from Excel.
# Supports local paths or URL images. Exports filtered results.
# -----------------------------------------------------------

import os
import io
from typing import Optional, Dict

import streamlit as st
import pandas as pd
from PIL import Image

# Optional: support image URLs
try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

# ---------- App Config ----------
st.set_page_config(page_title="Product Catalog Viewer", layout="wide")
st.title("📘 Product Catalog Viewer")
st.caption(
    "Upload an Excel file, map columns, then select Module → Sub-Category → Segment → Product to view image and definition."
)

# ---------- Constants ----------
ROLES = ["Module", "SubCategory", "Segment", "ProductName", "Definition", "Image"]

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_excel(uploaded_file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Load Excel using openpyxl for .xlsx and xlrd for .xls when available.
    If sheet_name is provided, read that sheet; else first sheet.
    """
    if uploaded_file is None:
        return pd.DataFrame()

    try:
        file_name = getattr(uploaded_file, "name", "")
        ext = os.path.splitext(file_name)[1].lower()

        # Choose engine by extension
        if ext == ".xls":
            # xlrd is required for .xls (older Excel). If not installed, show a friendly error.
            try:
                xls = pd.ExcelFile(uploaded_file, engine="xlrd")
            except Exception as e:
                raise RuntimeError("Reading .xls requires xlrd. Please install xlrd or upload a .xlsx file.") from e
        else:
            xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

        sheets = xls.sheet_names
        if not sheets:
            return pd.DataFrame()

        if sheet_name is None or sheet_name not in sheets:
            sheet_name = sheets[0]  # default to first sheet

        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()


def suggest_mapping(df_cols):
    """
    Lightweight auto-suggest for column mapping based on column names.
    """
    lower = {str(c).lower(): str(c) for c in df_cols}

    def pick(*cands):
        for c in cands:
            if c in lower:
                return lower[c]
        return None

    return {
        "Module":      pick("module", "category", "division"),
        "SubCategory": pick("subcategory", "sub-category", "sub category", "subcat"),
        "Segment":     pick("segment", "subsegment", "sub-segment"),
        "ProductName": pick("productname", "product name", "product", "name"),
        "Definition":  pick("definition", "desc", "description"),
        "Image":       pick("image", "imageurl", "image url", "img", "photo", "picture", "image_path"),
    }


@st.cache_data(show_spinner=False)
def load_image(img_ref: str) -> Optional[Image.Image]:
    """
    Load an image from a local path or URL.
    Returns PIL Image or None if fails.
    """
    if not img_ref:
        return None

    img_ref = str(img_ref).strip()
    try:
        # URL case
        if img_ref.lower().startswith(("http://", "https://")) and REQUESTS_AVAILABLE:
            resp = requests.get(img_ref, timeout=10)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGB")

        # Local file case
        if os.path.exists(img_ref):
            return Image.open(img_ref).convert("RGB")

    except Exception:
        return None
    return None


def chain_select(df: pd.DataFrame, mapping: Dict[str, str]):
    """
    Render cascaded selectors: Module -> SubCategory -> Segment -> ProductName
    Returns filtered dataframe and the current selection dict.
    """
    sel: Dict[str, str] = {}

    mod_col = mapping.get("Module")
    sub_col = mapping.get("SubCategory")
    seg_col = mapping.get("Segment")
    prod_col = mapping.get("ProductName")

    # Module
    if mod_col and mod_col in df.columns:
        modules = sorted([str(x) for x in df[mod_col].dropna().unique()])
        sel["Module"] = st.selectbox("Module", options=["(All)"] + modules, index=0)
        df = df if sel["Module"] == "(All)" else df[df[mod_col].astype(str) == sel["Module"]]

    # SubCategory
    if sub_col and sub_col in df.columns:
        subs = sorted([str(x) for x in df[sub_col].dropna().unique()])
        sel["SubCategory"] = st.selectbox("Sub-Category", options=["(All)"] + subs, index=0)
        df = df if sel["SubCategory"] == "(All)" else df[df[sub_col].astype(str) == sel["SubCategory"]]

    # Segment
    if seg_col and seg_col in df.columns:
        segs = sorted([str(x) for x in df[seg_col].dropna().unique()])
        sel["Segment"] = st.selectbox("Segment", options=["(All)"] + segs, index=0)
        df = df if sel["Segment"] == "(All)" else df[df[seg_col].astype(str) == sel["Segment"]]

    # ProductName
    if prod_col and prod_col in df.columns:
        prods = sorted([str(x) for x in df[prod_col].dropna().unique()])
        sel["ProductName"] = st.selectbox("Product", options=["(All)"] + prods, index=0)
        df = df if sel["ProductName"] == "(All)" else df[df[prod_col].astype(str) == sel["ProductName"]]

    return df, sel


def show_product_card(row: pd.Series, mapping: Dict[str, str]):
    """
    Show image (if available) and definition for a single product row.
    """
    img_col = mapping.get("Image")
    def_col = mapping.get("Definition")
    prod_col = mapping.get("ProductName")

    product_name = str(row.get(prod_col, "")) if prod_col else ""
    definition = str(row.get(def_col, "")) if def_col else ""
    img_ref = str(row.get(img_col, "")) if img_col else ""

    c1, c2 = st.columns([1, 2])
    with c1:
        img = load_image(img_ref)
        if img:
            st.image(img, caption=product_name or "Image", use_column_width=True)
        else:
            st.info("No image or failed to load image for this item.")

    with c2:
        st.subheader(product_name or "Unnamed Product")
        st.markdown(definition or "_No definition provided._")


# ---------- UI: Upload ----------
uploaded_file = st.file_uploader(
    "Upload Excel file (.xlsx or .xls)",
    type=["xlsx", "xls"],
    accept_multiple_files=False,
    help="Supported: Excel .xlsx (openpyxl) and .xls (xlrd)."
)

if uploaded_file is None:
    st.warning("Please upload an Excel file to begin.")
    st.stop()

# ---------- UI: Sheet Selection ----------
try:
    # Use the same engine logic as load_excel for listing sheets
    file_name = getattr(uploaded_file, "name", "")
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".xls":
        try:
            xls = pd.ExcelFile(uploaded_file, engine="xlrd")
        except Exception as e:
            st.error("Reading .xls requires xlrd. Please install xlrd or upload a .xlsx file.")
            st.stop()
    else:
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

    sheets = xls.sheet_names
    if not sheets:
        st.error("No sheets found in the uploaded file.")
        st.stop()

    sheet_choice = st.selectbox("Select sheet", options=sheets, index=0)
    df = pd.read_excel(xls, sheet_name=sheet_choice)
    df.columns = [str(c).strip() for c in df.columns]
except Exception as e:
    st.error(f"Unable to read Excel sheets: {e}")
    st.stop()

if df.empty:
    st.error("Selected sheet is empty or failed to load.")
    st.stop()

# ---------- UI: Column Mapping ----------
st.subheader("Map Columns")
auto_map = suggest_mapping(df.columns)
mapping: Dict[str, str] = {}

cols = st.columns(3)
for i, role in enumerate(ROLES):
    with cols[i % 3]:
        # Preselect suggested column if available
        suggested = auto_map.get(role)
        index = 0
        if suggested in df.columns:
            index = list(df.columns).index(suggested) + 1  # +1 because "(None)" at index 0

        mapping[role] = st.selectbox(
            f"{role} column",
            options=["(None)"] + list(df.columns),
            index=index
        )

# Validate minimum mapping
required = ["Module", "SubCategory", "Segment", "ProductName"]
missing = [r for r in required if not mapping.get(r) or mapping.get(r) == "(None)"]
if missing:
    st.error(f"Please map required columns: {', '.join(missing)}")
    st.stop()

# ---------- UI: Filtering ----------
st.subheader("Filter & View")
fdf, selection = chain_select(df, mapping)

# ---------- Results Table ----------
st.markdown("### Filtered Results")
st.dataframe(fdf, use_container_width=True)

# ---------- Export ----------
c_exp1, c_exp2 = st.columns([1, 1])
with c_exp1:
    if st.button("Export filtered to CSV"):
        csv_bytes = fdf.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="filtered_results.csv",
            mime="text/csv",
        )
with c_exp2:
    if st.button("Export filtered to Excel"):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            fdf.to_excel(writer, index=False, sheet_name="Filtered")
        buffer.seek(0)
        st.download        st.download_button(
            "Download Excel",
            data=buffer,
            file_name="filtered_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ---------- Product Viewer ----------
if not fdf.empty:
    st.markdown("---")
    st.markdown("### Product Details")
    # Show either the single selected product or a preview
    prod_col = mapping.get("ProductName")
    if selection.get("ProductName") and selection["ProductName"] != "(All)":
        # Show the single selected product(s)
        for _, row in fdf.iterrows():
            show_product_card(row, mapping)
    else:
        # Show top 5 items to preview
        for _, row in fdf.head(5).iterrows():
            show_product_card(row, mapping)
else:
