
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
def _excel_engine_from_ext(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return "xlrd" if ext == ".xls" else "openpyxl"


@st.cache_data(show_spinner=False)
def get_sheet_names(uploaded_file) -> list:
    """Return sheet names from uploaded Excel."""
    if uploaded_file is None:
        return []
    name = getattr(uploaded_file, "name", "uploaded.xlsx")
    engine = _excel_engine_from_ext(name)
    xls = pd.ExcelFile(uploaded_file, engine=engine)
    return xls.sheet_names


@st.cache_data(show_spinner=False)
def load_excel(uploaded_file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Load Excel (.xlsx via openpyxl, .xls via xlrd).
    If sheet_name is provided, read that sheet; else first sheet.
    """
    if uploaded_file is None:
        return pd.DataFrame()

    try:
        name = getattr(uploaded_file, "name", "uploaded.xlsx")
        engine = _excel_engine_from_ext(name)

        xls = pd.ExcelFile(uploaded_file, engine=engine)
        sheets = xls.sheet_names
        if not sheets:
            return pd.DataFrame()

        if sheet_name is None or sheet_name not in sheets:
            sheet_name = sheets[0]

        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()


def suggest_mapping(df_cols):
    """
    Auto-suggest column mapping based on common names.
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
    Load image from URL or local path.
    """
    if not img_ref or str(img_ref).strip() == "" or str(img_ref).lower() == "nan":
        return None

    img_ref = str(img_ref).strip()

    try:
        # URL image
        if img_ref.lower().startswith(("http://", "https://")):
            if not REQUESTS_AVAILABLE:
                return None
            r = requests.get(img_ref, timeout=10)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content)).convert("RGB")

        # Local image path
        if os.path.exists(img_ref):
            return Image.open(img_ref).convert("RGB")

    except Exception:
        return None

    return None


def clean_mapping(mapping: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Convert '(None)' to None."""
    cleaned = {}
    for k, v in mapping.items():
        cleaned[k] = None if (v is None or v == "(None)") else v
    return cleaned


def chain_select(df: pd.DataFrame, mapping: Dict[str, Optional[str]]):
    """
    Cascading dropdowns: Module -> SubCategory -> Segment -> ProductName
    Returns filtered df + selection dict.
    """
    sel = {}

    def _options(col):
        vals = df[col].dropna().astype(str).unique().tolist()
        vals = sorted(vals)
        return ["(All)"] + vals

    # Module
    if mapping.get("Module") in df.columns:
        col = mapping["Module"]
        sel["Module"] = st.selectbox("Module", _options(col), index=0)
        if sel["Module"] != "(All)":
            df = df[df[col].astype(str) == sel["Module"]]

    # SubCategory
    if mapping.get("SubCategory") in df.columns:
        col = mapping["SubCategory"]
        sel["SubCategory"] = st.selectbox("Sub-Category", _options(col), index=0)
        if sel["SubCategory"] != "(All)":
            df = df[df[col].astype(str) == sel["SubCategory"]]

    # Segment
    if mapping.get("Segment") in df.columns:
        col = mapping["Segment"]
        sel["Segment"] = st.selectbox("Segment", _options(col), index=0)
        if sel["Segment"] != "(All)":
            df = df[df[col].astype(str) == sel["Segment"]]

    # Product
    if mapping.get("ProductName") in df.columns:
        col = mapping["ProductName"]
        sel["ProductName"] = st.selectbox("Product", _options(col), index=0)
        if sel["ProductName"] != "(All)":
            df = df[df[col].astype(str) == sel["ProductName"]]

    return df, sel


def show_product_card(row: pd.Series, mapping: Dict[str, Optional[str]]):
    """
    Display image + definition.
    """
    prod_col = mapping.get("ProductName")
    def_col = mapping.get("Definition")
    img_col = mapping.get("Image")

    product = str(row.get(prod_col, "")) if prod_col else ""
    definition = str(row.get(def_col, "")) if def_col else ""
    img_ref = str(row.get(img_col, "")) if img_col else ""

    c1, c2 = st.columns([1, 2])
    with c1:
        img = load_image(img_ref)
        if img:
            st.image(img, caption=product or "Image", use_container_width=True)
        else:
            st.info("No image / image failed to load.")

    with c2:
        st.subheader(product or "Unnamed Product")
        st.markdown(definition if definition.strip() else "_No definition provided._")


# ---------- UI: Upload ----------
uploaded_file = st.file_uploader(
    "Upload Excel file (.xlsx or .xls)",
    type=["xlsx", "xls"],
    accept_multiple_files=False
)

if uploaded_file is None:
    st.warning("Please upload an Excel file to begin.")
    st.stop()

# ---------- UI: Sheet selection ----------
try:
    sheets = get_sheet_names(uploaded_file)
except Exception as e:
    st.error(f"Could not read sheet names: {e}")
    st.stop()

if not sheets:
    st.error("No sheets found in this Excel.")
    st.stop()

sheet_choice = st.selectbox("Select sheet", options=sheets, index=0)

df = load_excel(uploaded_file, sheet_choice)
if df.empty:
    st.error("Selected sheet is empty or failed to load.")
    st.stop()

st.success(f"Loaded {df.shape[0]} rows and {df.shape[1]} columns.")

# ---------- UI: Column mapping ----------
st.subheader("🧩 Map Columns")
auto_map = suggest_mapping(df.columns)
mapping = {}

cols = st.columns(3)
for i, role in enumerate(ROLES):
    with cols[i % 3]:
        suggested = auto_map.get(role)
        idx = 0
        if suggested in df.columns:
            idx = list(df.columns).index(suggested) + 1  # +1 because "(None)" at index 0

        mapping[role] = st.selectbox(
            f"{role} column",
            options=["(None)"] + list(df.columns),
            index=idx
        )

mapping = clean_mapping(mapping)

# Validate minimum required mapping
required = ["Module", "SubCategory", "Segment", "ProductName"]
missing = [r for r in required if not mapping.get(r)]
if missing:
    st.error(f"Please map required columns: {', '.join(missing)}")
    st.stop()

# ---------- Filtering ----------
st.subheader("🔎 Filter & View")
fdf, selection = chain_select(df, mapping)

# ---------- Results ----------
st.markdown("### 📄 Filtered Results")
st.dataframe(fdf, use_container_width=True)

# ---------- Export ----------
st.markdown("### ⬇️ Export Filtered Data")

c_exp1, c_exp2 = st.columns([1, 1])

with c_exp1:
    if st.button("Export filtered to CSV"):
        csv_bytes = fdf.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
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
        st.download_button(
            label="Download Excel",
            data=buffer,
            file_name="filtered_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ---------- Product viewer ----------
st.markdown("---")
st.markdown("## 🧾 Product Details")

if fdf.empty:
    st.info("No rows match the current filters.")
else:
    # If a specific product is selected, show all matching rows
    if selection.get("ProductName") and selection["ProductName"] != "(All)":
        for _, row in fdf.iterrows():
            show_product_card(row, mapping)
    else:
        # Otherwise show a preview of first 5
        st.info("Showing preview (top 5). Select a specific Product to view one item.")
        for _,        for _, row in fdf.head(5).iterrows():
