
# app.py
# -----------------------------------------------------------
# Upload Excel -> Select Module/Sub-Category/Segment/Product
# Show product definition and image (path or URL from Excel)
# -----------------------------------------------------------

import os
import io
from typing import Dict, Optional

import streamlit as st
import pandas as pd
from PIL import Image

# Try to support image URLs (optional)
try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

st.set_page_config(page_title="Product Catalog Viewer", layout="wide")
st.title("📘 Product Catalog Viewer")
st.caption("Upload an Excel file, map columns, then select Module → Sub-Category → Segment → Product.")

# ---------- Helpers ----------
REQUIRED_ROLES = ["Module", "SubCategory", "Segment", "ProductName", "Definition", "Image"]

def load_excel(uploaded) -> pd.DataFrame:
    """Load Excel (.xlsx) using openpyxl."""
    if uploaded is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(uploaded, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()

def suggest_mapping(df_cols):
    """Lightweight auto-suggest for column mapping."""
    lower_map = {c.lower(): c for c in df_cols}
    def pick(*cands):
        for c in cands:
            if c in lower_map:
                return lower_map[c]
        return None
    return {
        "Module":      pick("module", "category", "division"),
        "SubCategory": pick("subcategory", "sub_category", "sub cat", "subcat"),
        "Segment":     pick("segment", "subsegment", "sub_segment"),
        "ProductName": pick("productname", "product_name", "name", "item", "sku"),
        "Definition":  pick("definition", "description", "details", "spec"),
        "Image":       pick("image", "imagepath", "image_path", "imageurl", "image_url", "picture", "img"),
    }

def validate_mapping(df, mapping: Dict[str, Optional[str]]) -> bool:
    missing = [role for role, col in mapping.items() if (col is None or col not in df.columns)]
    if missing:
        st.error(f"Missing mapped columns: {', '.join(missing)}")
        return False
    return True

def read_image(ref: str) -> Optional[Image.Image]:
    """Load image from local path or URL."""
    if not ref:
        return None
    ref = str(ref).strip()

    # URL case
    if ref.lower().startswith(("http://", "https://")):
        if not REQUESTS_AVAILABLE:
            st.warning("Install `requests` to load images from URLs.")
            return None
        try:
            r = requests.get(ref, timeout=10)
