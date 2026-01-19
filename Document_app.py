
# app.py
import io
import time
import pandas as pd
import streamlit as st

# ---------- Page Setup ----------
st.set_page_config(page_title="Product Selector", layout="wide")
st.title("Product Selector")

# ---------- Configuration ----------
# Expected logical columns in the UI, mapped from normalized (lower) to display names.
EXPECTED_COLUMNS = {
    "key word": "Key Word",
    "placement": "Placement",
    "department": "Department",
    "super category": "Super Category",
    "category": "Category",
    "subcategory": "Subcategory",
    "segment": "Segment",
}

# Path to the bundled sample file that ships with your app.
SAMPLE_PATH = "TRAIL DOC.xlsx"  # Make sure this file exists in the same folder as app.py

# ---------- Utilities ----------
def _normalize_headers(cols) -> list:
    """Lowercase, strip, and collapse spaces in column names."""
    return (
        pd.Series(cols)
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
        .tolist()
    )

@st.cache_data(show_spinner=False)
def read_excel_safely(file_like_or_path, preferred_sheet=None):
    """
    Safely read an Excel file.
    Returns: (df_raw_normalized_headers, meta, error_message)
    meta: dict with sheet, columns_before, columns_after
    """
    meta = {"sheet": None, "columns_before": [], "columns_after": []}
    try:
        xl = pd.ExcelFile(file_like_or_path, engine="openpyxl")
        sheets = [s for s in xl.sheet_names if not s.startswith("_")]

        # Try preferred sheet if provided; otherwise pick first visible
        target_sheet = (
            preferred_sheet
            if (preferred_sheet and preferred_sheet in xl.sheet_names)
            else (sheets[0] if sheets else xl.sheet_names[0])
        )
        meta["sheet"] = target_sheet

        df = pd.read_excel(xl, sheet_name=target_sheet, engine="openpyxl")
        meta["columns_before"] = [str(c) for c in df.columns]

        # Normalize headers
        df.columns = _normalize_headers(df.columns)
        meta["columns_after"] = list(df.columns)
        return df, meta, None
    except Exception as e:
        return None, meta, str(e)

def standardize_and_subset(df_norm):
    """
    Rename normalized headers to the expected display names and subset.
    Returns: (df_subset, present_display_cols, missing_display_cols)
    """
    rename_map = {src: EXPECTED_COLUMNS[src] for src in EXPECTED_COLUMNS if src in df_norm.columns}
    df_std = df_norm.rename(columns=rename_map)

    expected_display = list(EXPECTED_COLUMNS.values())
    present = [c for c in expected_display if c in df_std.columns]
    missing = [c for c in expected_display if c not in df_std.columns]

    # Keep only the known columns; leave others out to keep UI clean
    if present:
        df_std = df_std[present]
    else:
        # Keep empty df with no columns if nothing matched
        df_std = pd.DataFrame()

    return df_std, present, missing

def clean_strings(df, cols):
    """Trim string columns and set blanks/'nan' to None for consistent filtering."""
    for c in cols:
        if c in df.columns:
            df[c] = (
                df[c]
                .astype(str)
                .str.strip()
                .replace({"nan": None, "None": None, "": None})
            )
    return df

def unique_non_null(df, col):
    """Sorted unique non-null values for a column."""
    if col not in df.columns or df.empty:
        return []
    vals = df[col].dropna().astype(str).str.strip()
    return sorted([v for v in vals.unique() if v != ""])

def download_xlsx_bytes(df: pd.DataFrame) -> bytes:
    """Return an in-memory .xlsx file for download."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Filtered", index=False)
    return output.getvalue()

# ---------- Data Source UI ----------
with st.container():
    with st.expander("Data source", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            use_sample = st.toggle("Use sample data (no upload)", value=True,
                                   help="Turn off to upload your own .xlsx file.")
        with c2:
            preferred_sheet = st.text_input(
                "Sheet name (optional)",
                value="",
                placeholder="Leave blank to auto-detect first visible sheet"
            )
        with c3:
            uploaded = None
            if not use_sample:
                uploaded = st.file_uploader(
                    "Upload Excel (.xlsx)",
                    type=["xlsx"],
                    accept_multiple_files=False
                )

# ---------- Load Data ----------
source_label = "sample"
file_to_read = SAMPLE_PATH
if not use_sample and uploaded is not None:
    source_label = "uploaded"
    file_to_read = uploaded

df_norm, meta, err = read_excel_safely(
    file_to_read,
    preferred_sheet=preferred_sheet.strip() or None
)

if err:
    st.error(
        f"Could not read Excel from **{source_label}** source.\n\n"
        f"**Error:** {err}"
    )
    if use_sample:
        st.info("Check that the sample file exists alongside app.py: **TRAIL DOC.xlsx**")
    st.stop()

df_std, present_cols, missing_cols = standardize_and_subset(df_norm)
df_std = clean_strings(df_std, present_cols)

if not present_cols:
    st.error(
        "No expected columns were found after reading your file.\n\n"
        "We look for these columns: "
        + ", ".join(EXPECTED_COLUMNS.values())
    )
    with st.expander("Debug details"):
        st.write(f"Sheet used: {meta['sheet']}")
        st.write(f"Original headers: {meta['columns_before']}")
        st.write(f"Normalized headers: {meta['columns_after']}")
    st.stop()

if missing_cols:
    st.warning(
        "Some expected columns are missing. Filters will be limited.\n\n"
        f"**Missing:** {', '.join(missing_cols)}"
    )

# ---------- Filters ----------
st.subheader("Filters")

# Initialize session state for filter selections
if "filters" not in st.session_state:
    st.session_state.filters = {col: [] for col in present_cols}

# Reset filters button
rcol1, rcol2 = st.columns([1, 6])
with rcol1:
    if st.button("Reset filters", type="secondary"):
        st.session_state.filters = {col: [] for col in present_cols}
        st.experimental_rerun()

# Render multiselects in a neat row
cols_for_widgets = st.columns(len(present_cols))
for i, col in enumerate(present_cols):
    with cols_for_widgets[i]:
        options = unique_non_null(df_std, col)
        # Persist selection via session_state
        st.session_state.filters[col] = st.multiselect(
            label=col,
            options=options,
            default=st.session_state.filters.get(col, []),
            placeholder=f"Pick {col.lower()}..."
        )

# Apply filters
mask = pd.Series([True] * len(df_std))
for col, choices in st.session_state.filters.items():
    if choices:
        mask = mask & df_std[col].isin(choices)

filtered = df_std[mask].copy()

# ---------- Debug / Diagnostics ----------
with st.expander("Debug: unique counts per level in current result", expanded=False):
    st.write(f"Sheet used: **{meta['sheet']}**")
    st.write("Original headers:", meta["columns_before"])
    st.write("Normalized headers:", meta["columns_after"])
    st.markdown("---")
    for col in present_cols:
        st.write(f"{col}: {len(unique_non_null(filtered, col))} unique values")

# ---------- Results ----------
st.subheader("Results")
if filtered.empty:
    st.warning("No product found for this selection.")
else:
    st.success(f"Found **{len(filtered)}** rows.")
    st.dataframe(filtered, use_container_width=True, height=450)

    dl1, dl2 = st.columns([1, 1])
    with dl1:
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="filtered_products.csv",
            mime="text/csv",
            type="primary",
        )
    with dl2:
        xbytes = download_xlsx_bytes(filtered)
        st.download_button(
            "Download Excel",
            data=xbytes,
            file_name="filtered_products.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
        )

# ---------- Footer ----------
st.caption("Tip: If nothing appears in a filter, open the Debug section to compare your file’s headers with the expected columns.")
