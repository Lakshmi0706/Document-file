
# app.py
# --------------------------------------------------------------------
# Product Catalog Viewer for Excel (Module → Sub-Category → Segment)
# Shows product image + definition based on selections.
import os# Supports: local image paths or URLs in Excel.
import io
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd
from PIL import Image

# Optional: fetch images from URLs (if Image column contains URLs)
try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

# ---------------------- App Config ----------------------
st.set_page_config(page_title="Product Catalog (Excel → Streamlit)", layout="wide")
st.title("📘 Product Catalog Viewer")
st.caption("Select Module → Sub-Category → Segment to see product image and definition. Upload your Excel or use the default.")

# ---------------------- Paths --------------------------
DATA_DIR = "data"
DEFAULT_XLSX_PATH = os.path.join(DATA_DIR, "products.xlsx")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------- Helpers ------------------------
REQUIRED_ROLES = ["Module", "SubCategory", "Segment", "ProductName", "Definition", "Image"]

def load_excel(source) -> pd.DataFrame:
    """
    Load Excel file from uploader or local default path.
    Ensures we use openpyxl engine for .xlsx.
    """
    try:
        if source is None and os.path.exists(DEFAULT_XLSX_PATH):
            df = pd.read_excel(DEFAULT_XLSX_PATH, engine="openpyxl")
        elif source is not None:
            df = pd.read_excel(source, engine="openpyxl")
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load Excel: {e}")
        return pd.DataFrame()

    # Normalize column names (strip, unify spaces)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def suggest_mapping(df_cols: List[str]) -> Dict[str, Optional[str]]:
    """
    Suggest column mapping by simple keyword matching.
    You can override in the UI.
    """
    lower_cols = {c.lower(): c for c in df_cols}
    def pick(*candidates):
        for cand in candidates:
            if cand in lower_cols:
                return lower_cols[cand]
        return None

    return {
        "Module":       pick("module", "category", "division"),
        "SubCategory":  pick("subcategory", "sub_category", "sub cat", "subcat"),
        "Segment":      pick("segment", "subsegment", "sub_segment"),
        "ProductName":  pick("productname", "product_name", "name", "item", "sku"),
        "Definition":   pick("definition", "description", "details", "spec"),
        "Image":        pick("image", "imagepath", "image_path", "picture", "imageurl", "image_url", "img"),
    }


def read_image(path_or_url: str) -> Optional[Image.Image]:
    """
    Read image from local path or remote URL.
    Returns a PIL Image or None if fails.
    """
    if not path_or_url:
        return None

    path_or_url = str(path_or_url).strip()

    # URL case
    if path_or_url.lower().startswith(("http://", "https://")):
        if not REQUESTS_AVAILABLE:
            st.warning("requests not available; cannot fetch URL images. Add `requests` to requirements.")
            return None
        try:
            resp = requests.get(path_or_url, timeout=10)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content))
        except Exception:
            return None
    else:
        # Local file case (relative to app root)
        if not os.path.isabs(path_or_url):
            path_or_url = os.path.join(os.getcwd(), path_or_url)
        if not os.path.exists(path_or_url):
            return None
        try:
            return Image.open(path_or_url)
        except Exception:
            return None


def validate_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> bool:
    missing = [role for role, col in mapping.items() if not col or col not in df.columns]
    if missing:
        st.error(f"Missing mapped columns for: {', '.join(missing)}")
        return False
    return True


def cascade_unique(df: pd.DataFrame, mapping: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Return unique values for each level to populate dropdowns.
    """
    mod_col = mapping["Module"]
    sub_col = mapping["SubCategory"]
    seg_col = mapping["Segment"]

    return {
        "modules": sorted([x for x in df[mod_col].dropna().unique()]),
        "subcats": sorted([x for x in df[sub_col].dropna().unique()]),
        "segments": sorted([x for x in df[seg_col].dropna().unique()]),
    }


def render_product_card(row, mapping: Dict[str, str]):
    """
    Render one product card with image + definition.
    """
    prod = str(row.get(mapping["ProductName"], ""))
    definition = str(row.get(mapping["Definition"], ""))
    image_ref = str(row.get(mapping["Image"], ""))

    with st.container(border=True):
        cols = st.columns([1, 2])
        with cols[0]:
            img = read_image(image_ref)
            if img:
                st.image(img, use_column_width=True)
            else:
                st.info("No image / failed to load")
        with cols[1]:
            st.subheader(prod if prod else "Unnamed product")
            st.markdown(f"**Definition:** {definition}" if definition else "_No definition provided_")

            # Show raw refs if needed
            with st.expander("Source fields"):
                st.code(f"Image: {image_ref}")

# --------------------------------------------------------------------

