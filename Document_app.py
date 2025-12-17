
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
def excel_engine_from_name(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return "xlrd" if ext == ".xls" else "openpyxl"


def get_sheet_names(uploaded_file) -> list:
    if uploaded_file is None:
        return []
    name = getattr(uploaded_file, "name", "uploaded.xlsx")
    engine = excel_engine_from_name(name)

    try:
        xls = pd.ExcelFile(uploaded_file, engine=engine)
        return xls.sheet_names
    except Exception as e:
        # common: xlrd not installed for .xls
        raise RuntimeError(str(e))


def load_excel(uploaded_file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()

    name = getattr(uploaded_file, "name", "uploaded.xlsx")
    engine = excel_engine_from_name(name)

    try:
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


def clean_mapping(mapping: Dict[str, str]) -> Dict[str, Optional[str]]:
    cleaned: Dict[str, Optional[str]] = {}
    for k, v in mapping.items():
        cleaned[k] = None if (v is None or v == "(None)") else v
    return cleaned


def load_image(img_ref: str, base_dir: Optional[str] = None) -> Optional[Image.Image]:
    """
    Supports:
    - URL (http/https)
    - Absolute local path
    - Relative path resolved against base_dir (optional)
    """
    if img_ref is None:
        return None

    img_ref = str(img_ref).strip()
    if img_ref == "" or img_ref.lower() == "nan":
        return None

    try:
        # URL
        if img_ref.lower().startswith(("http://", "https://")):
            if not REQUESTS_AVAILABLE:
                return None
            r = requests.get(img_ref, timeout=10)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content)).convert("RGB")

        # Local path (absolute or relative)
        candidate = img_ref
        if not os.path.isabs(candidate) and base_dir:
            candidate = os.path.join(base_dir, candidate)

        if os.path.exists(candidate):
            return Image.open(candidate).convert("RGB")

    except Exception:
        return None

    return None


def chain_select(df: pd.DataFrame, mapping: Dict[str, Optional[str]]):
    """
    Cascading dropdowns: Module -> SubCategory -> Segment -> ProductName
    Returns filtered dataframe and selection dict.
    """
    sel: Dict[str, str] = {}

    def options_for(col: str):
        vals = df[col].dropna().astype(str).unique().tolist()
        vals = sorted(vals)
        return ["(All)"] + vals

    # Module
    if mapping.get("Module") and mapping["Module"] in df.columns:
        col = mapping["Module"]
        sel["Module"] = st.selectbox("Module", options_for(col), index=0)
        if sel["Module"] != "(All)":
            df = df[df[col].astype(str) == sel["Module"]]

    # SubCategory
    if mapping.get("SubCategory") and mapping["SubCategory"] in df.columns:
        col = mapping["SubCategory"]
        sel["SubCategory"] = st.selectbox("Sub-Category", options_for(col), index=0)
        if sel["SubCategory"] != "(All)":
            df = df[df[col].astype(str) == sel["SubCategory"]]

    # Segment
    if mapping.get("Segment") and mapping["Segment"] in df.columns:
        col = mapping["Segment"]
        sel["Segment"] = st.selectbox("Segment", options_for(col), index=0)
        if sel["Segment"] != "(All)":
            df = df[df[col].astype(str) == sel["Segment"]]

    # ProductName
    if mapping.get("ProductName") and mapping["ProductName"] in df.columns:
        col = mapping["ProductName"]
        sel["ProductName"] = st.selectbox("Product", options_for(col), index=0)
        if sel["ProductName"] != "(All)":
            df = df[df[col].astype(str) == sel["ProductName"]]

    return df, sel


def show_product_card(row: pd.Series, mapping: Dict[str, Optional[str]], base_dir: Optional[str] = None):
    prod_col = mapping.get("ProductName")
    def_col = mapping.get("Definition")
    img_col = mapping.get("Image")

    product = str(row.get(prod_col, "")) if prod_col else ""
    definition = str(row.get(def_col, "")) if def_col else ""
    img_ref = str(row.get(img_col, "")) if img_col else ""

    c1, c2 = st.columns([1, 2])

    with c1:
        img = load_image(img_ref, base_dir=base_dir)
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

# Optional: base directory for relative image paths (useful if you deploy with an /images folder)
base_dir = st.text_input("Base folder for relative image paths (optional)", value="")

# ---------- UI: Sheet Selection ----------
try:
    sheets = get_sheet_names(uploaded_file)
except Exception as e:
    msg = str(e)
    if "xlrd" in msg.lower():
        st.error("This looks like a .xls file. Please install xlrd (pip install xlrd) or upload .xlsx instead.")
    else:
        st.error(f"Could not read Excel: {e}")
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

# ---------- UI: Column Mapping ----------
st.subheader("🧩 Map Columns")
auto_map = suggest_mapping(df.columns)

mapping_raw: Dict[str, str] = {}
cols = st.columns(3)

for i, role in enumerate(ROLES):
    with cols[i % 3]:
        suggested = auto_map.get(role)
        index = 0
        if suggested in df.columns:
            index = list(df.columns).index(suggested) + 1  # +1 because "(None)" at index 0

        mapping_raw[role] = st.selectbox(
            f"{role} column",
            options=["(None)"] + list(df.columns),
            index=index
        )

mapping = clean_mapping(mapping_raw)

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

# ---------- Export (SAFE: no extra st.button needed) ----------
st.markdown("### ⬇️ Export Filtered Data")

csv_bytes = fdf.to_csv(index=False).encode("utf-8")

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    fdf.to_excel(writer, index=False, sheet_name="Filtered")
excel_buffer.seek(0)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="filtered_results.csv",
        mime="text/csv",
        use_container_width=True
    )
with c2:
    st.download_button(
        label="Download Excel",
        data=excel_buffer,
        file_name="filtered_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ---------- Product Viewer ----------
st.markdown("---")
st.markdown("## 🧾 Product Details")

if fdf.empty:
    st.info("No rows match the current filters.")
else:
    if selection.get("ProductName") and selection["ProductName"] != "(All)":
        for _, row in fdf.iterrows():
            show_product_card(row, mapping, base_dir=base_dir or None)
    else:
        st.info("Showing preview (top 5). Select a specific Product to view one item.")
        for _, row in fdf.head(5).iterrows():
            show_product_card(row, mapping, base_dir=base
