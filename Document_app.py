
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
st.caption("Upload an Excel file, map columns, then select Module → Sub-Category → Segment → Product to view image and definition.")

# ---------- Constants ----------
ROLES = ["Module", "SubCategory", "Segment", "ProductName", "Definition", "Image"]

# ---------- Helpers ----------
def load_excel(uploaded_file, sheet_name=None) -> pd.DataFrame:
    """
    Load Excel (.xlsx) using openpyxl.
    If sheet_name is provided, read that sheet; else first sheet.
    """
    if uploaded_file is None:
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
        sheets = xls.sheet_names
        if sheet_name is None or sheet_name not in sheets:
            sheet_name = sheets[0]  # default to first sheet
        df = pd.read_excel(xls, sheet_name=sheet_name, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()


def suggest_mapping(df_cols):
    """
    Lightweight auto-suggest for column mapping based on column names.
    """
    lower = {c.lower(): c for c in df_cols}

    def pick(*cands):
        for c in cands:
            if c in lower:
                return lower[c]
        return None

    return {
        "Module":      pick("module", "category", "division"),
        "SubCategory": pick("subcategory", "sub_category", "sub cat", "subcat"),
        "Segment":     pick("segment", "subsegment", "sub_segment"),
        "ProductName": pick("productname", "product_name", "name", "item", "sku"),
        "Definition":  pick("definition", "description", "details", "spec", "narration"),
        "Image":       pick("image", "imagepath", "image_path", "imageurl", "image_url", "picture", "img"),
    }


def validate_mapping(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> bool:
    """
    Ensure all roles are mapped to existing columns.
    """
    missing = [role for role, col in mapping.items() if (col is None or col not in df.columns)]
    if missing:
        st.error(f"Missing mapped columns: {', '.join(missing)}")
        return False
    return True


def read_image(ref: str) -> Optional[Image.Image]:
    """
    Load image from a local path or a URL.
    Returns a PIL Image or None if it fails.

    Correct try/except blocks are used to avoid SyntaxError.
    """
    if not ref:
        return None

    ref = str(ref).strip()

    # --- Case 1: URL image ---
    if ref.lower().startswith(("http://", "https://")):
        if not REQUESTS_AVAILABLE:
            st.warning("Install `requests` (add to requirements.txt) to load images from URLs.")
            return None
        try:
            r = requests.get(ref, timeout=10)
            r.raise_for_status()  # raise if not 200
            return Image.open(io.BytesIO(r.content))
        except Exception as e:
            st.warning(f"Failed to fetch image URL: {ref}\nReason: {e}")
            return None

    # --- Case 2: Local file image ---
    try:
        # Resolve relative to app working directory
        if not os.path.isabs(ref):
            ref = os.path.join(os.getcwd(), ref)
        if not os.path.exists(ref):
            st.warning(f"Image path not found: {ref}")
            return None
        return Image.open(ref)
    except Exception as e:
        st.warning(f"Failed to open local image: {ref}\nReason: {e}")
        return None


def product_card(row: pd.Series, mapping: Dict[str, str]) -> None:
    """
    Render a product card with image + definition + source fields.
    """
    prod = str(row.get(mapping["ProductName"], "") or "")
    definition = str(row.get(mapping["Definition"], "") or "")
    image_ref = str(row.get(mapping["Image"], "") or "")

    with st.container(border=True):
        left, right = st.columns([1, 2])
        with left:
            img = read_image(image_ref)
            if img:
                st.image(img, use_column_width=True)
            else:
                st.info("No image / failed to load.")

        with right:
            st.subheader(prod if prod else "Unnamed product")
            if definition:
                st.markdown(f"**Definition:** {definition}")
            else:
                st.markdown("_No definition provided_")

            with st.expander("Source fields"):
                st.code(f"Image: {image_ref}")
                st.code(f"Module: {row.get(mapping['Module'], '')}")
                st.code(f"Sub-Category: {row.get(mapping['SubCategory'], '')}")
                st.code(f"Segment: {row.get(mapping['Segment'], '')}")


# ---------- Sidebar: Upload & sheet selection ----------
st.sidebar.header("1) Upload Excel")
uploaded_xlsx = st.sidebar.file_uploader("Choose .xlsx file", type=["xlsx"])

sheet_name = None
if uploaded_xlsx is not None:
    try:
        xls = pd.ExcelFile(uploaded_xlsx, engine="openpyxl")
        sheet_name = st.sidebar.selectbox("Sheet", options=xls.sheet_names, index=0)
        # reset file pointer after reading sheet names
        uploaded_xlsx.seek(0)
    except Exception as e:
        st.sidebar.warning(f"Could not list sheets: {e}")

df = load_excel(uploaded_xlsx, sheet_name=sheet_name)

if df.empty:
    st.info("Upload your Excel from the sidebar to begin.")
    st.stop()

st.success(f"Excel loaded. Rows: {len(df)}")
with st.expander("🔎 Preview (first 50 rows)"):
    st.dataframe(df.head(50), use_container_width=True)

# ---------- Column mapping ----------
st.sidebar.header("2) Map Columns")
suggested = suggest_mapping(df.columns.tolist())

mapping: Dict[str, Optional[str]] = {}
for role in ROLES:
    mapping[role] = st.sidebar.selectbox(
        f"{role} column",
        options=["(none)"] + df.columns.tolist(),
        index=(df.columns.tolist().index(suggested.get(role)) + 1) if suggested.get(role) in df.columns.tolist() else 0,
        help=f"Select which column represents '{role}'"
    )
    if mapping[role] == "(none)":
        mapping[role] = None

if not validate_mapping(df, mapping):
    st.stop()

# ---------- Main: Cascading filters ----------
st.header("3) Select filters")

mod_col = mapping["Module"]
sub_col = mapping["SubCategory"]
seg_col = mapping["Segment"]
prod_col = mapping["ProductName"]

# Module
modules = sorted(df[mod_col].dropna().unique().tolist())
sel_module = st.selectbox("Module", ["(All)"] + modules)

df_mod = df if sel_module == "(All)" else df[df[mod_col] == sel_module]

# Sub-Category
subcats = sorted(df_mod[sub_col].dropna().unique().tolist())
sel_subcat = st.selectbox("Sub-Category", ["(All)"] + subcats)

df_sub = df_mod if sel_subcat == "(All)" else df_mod[df_mod[sub_col] == sel_subcat]

# Segment
segments = sorted(df_sub[seg_col].dropna().unique().tolist())
sel_segment = st.selectbox("Segment", ["(All)"] + segments)

df_seg = df_sub if sel_segment == "(All)" else df_sub[df_sub[seg_col] == sel_segment]

# Product
products = sorted(df_seg[prod_col].dropna().unique().tolist())
sel_product = st.selectbox("Product", ["(All)"] + products)

# Final filtered set
filtered = df_seg if sel_product == "(All)" else df_seg[df_seg[prod_col] == sel_product]

st.header("4) Results")
st.caption(f"{len(filtered)} item(s)")

if len(filtered) == 0:
    st.warning("No products match the current filter.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(filtered.iterrows()):
        with cols[i % 3]:
            product_card(row, mapping)

# ---------- Export buttons ----------
with st.expander("⬇️ Export filtered data"):
    st.download_button(
        label="Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_products.csv",
        mime="text/csv"
    )

    # Export to Excel in-memory
    from pandas import ExcelWriter
    bio = io.BytesIO()
    with ExcelWriter(bio, engine="openpyxl") as writer:
        filtered.to_excel(writer, sheet_name="Filtered", index=False)
    st.download_button(
        label="Download Excel",
        data=bio.getvalue(),
        file_name="filtered_products.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spread        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
