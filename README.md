
# app.py
# ------------------------------------------------------------
# Streamlit Image Loader & Annotator with Optional GitHub Push
# ------------------------------------------------------------
# Features:
# - Multi-image upload and preview
# - Metadata extraction (format, width, height) + optional EXIF
# - Per-image tags and notes
# - Local persistence to data/annotations.csv
# - Optional: Save uploaded images locally (data/uploads) or push to GitHub
# - Filter & export annotations (CSV/JSON)
# ------------------------------------------------------------

import os
import io
import base64
from datetime import datetime
from typing import Dict, Optional

import streamlit as st
import pandas as pd
from PIL import Image

# -------------- App Config --------------
st.set_page_config(page_title="Image Loader & Annotator", layout="wide")
st.title("🖼️ Image Loader & Annotator")
st.caption("Upload images, view metadata, tag/annotate, and persist locally or to GitHub.")

# -------------- Paths --------------
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
ANNOTATIONS_PATH = os.path.join(DATA_DIR, "annotations.csv")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------- Sidebar Controls --------------
st.sidebar.header("Controls")

persist_files_local = st.sidebar.checkbox("Save uploaded files to disk", value=True)
enable_exif = st.sidebar.checkbox("Extract EXIF (if available)", value=False)

default_tags = st.sidebar.text_input("Default tags (comma-separated)", "")
default_notes = st.sidebar.text_area("Default notes", "")

st.sidebar.divider()
st.sidebar.subheader("GitHub (optional)")
st.sidebar.caption("Fill these to push uploads + annotations to GitHub.")
gh_owner = st.sidebar.text_input("Owner/org", value=st.secrets.get("github_owner", ""))
gh_repo = st.sidebar.text_input("Repository", value=st.secrets.get("github_repo", ""))
gh_branch = st.sidebar.text_input("Branch", value=st.secrets.get("github_branch", "main"))
gh_target_dir = st.sidebar.text_input("Repo path for uploads", value=st.secrets.get("github_upload_dir", "data/uploads"))
gh_token = st.secrets.get("github_token", "")

push_to_github = st.sidebar.checkbox("Push uploads & annotations to GitHub", value=bool(gh_token and gh_owner and gh_repo))

st.sidebar.divider()
st.sidebar.caption("Tip: You can batch-upload images and annotate each one.")


# -------------- Helper Functions --------------
def load_annotations() -> pd.DataFrame:
    """Load or initialize annotations dataframe."""
    if os.path.exists(ANNOTATIONS_PATH):
        try:
            df = pd.read_csv(ANNOTATIONS_PATH)
            # make sure required columns exist
            required_cols = ["timestamp", "filename", "stored_path", "format", "width", "height", "tags", "notes"]
            for c in required_cols:
                if c not in df.columns:
                    df[c] = ""
            return df
        except Exception:
            st.warning("Could not read annotations.csv. Starting fresh.")
    return pd.DataFrame(columns=[
        "timestamp", "filename", "stored_path", "format", "width", "height", "tags", "notes"
    ])


def save_annotations(df: pd.DataFrame) -> None:
    """Persist annotations to CSV locally."""
    df.to_csv(ANNOTATIONS_PATH, index=False)


def pil_metadata(img: Image.Image) -> Dict:
    """Return basic PIL metadata."""
    return {
        "format": img.format if getattr(img, "format", None) else "Unknown",
        "width": img.width,
        "height": img.height,
    }


def extract_exif_safe(img: Image.Image) -> Dict:
    """Extract a few useful EXIF fields if available."""
    result = {}
    try:
        exif = img.getexif()
        # Common EXIF fields: 271=Make, 272=Model, 306=DateTime
        result["camera_make"] = exif.get(271, "")
        result["camera_model"] = exif.get(272, "")
        result["datetime"] = exif.get(306, "")
    except Exception:
        pass
    return result


def save_uploaded_file_local(uploaded_file) -> str:
    """Persist the uploaded file to disk and return stored path."""
    filename = uploaded_file.name
    # avoid collision by prefixing timestamp
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename_safe = f"{ts}_{filename}"
    stored_path = os.path.join(UPLOAD_DIR, filename_safe)
    with open(stored_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return stored_path


def github_put_file(owner: str, repo: str, branch: str, path: str, content_bytes: bytes, token: str, message: str) -> Optional[str]:
    """
    Create or update a file in GitHub repo via the REST API.
    Returns the URL of the created file or None if failed.
    """
    import requests  # allowed in Streamlit Cloud; ensure network is available where you deploy

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    # Need SHA if file already exists
    # 1) Get existing file (if any)
    r_get = requests.get(url, headers=headers)
    sha = None
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")

    # 2) Put (create or update)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r_put = requests.put(url, headers=headers, json=payload)
    if r_put.status_code in (200, 201):
        return r_put.json().get("content", {}).get("html_url")
    else:
        st.error(f"GitHub push failed: {r_put.status_code} {r_put.text}")
        return None


def github_push_annotation_csv(owner: str, repo: str, branch: str, token: str, df: pd.DataFrame, repo_path: str = "data/annotations.csv") -> Optional[str]:
    """Push the annotations CSV to GitHub."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    msg = f"Update annotations.csv ({datetime.utcnow().isoformat(timespec='seconds')}Z)"
    return github_put_file(owner, repo, branch, repo_path, csv_bytes, token, msg)


# -------------- Main UI --------------
uploaded_files = st.file_uploader(
    "Upload images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True
)

annotations_df = load_annotations()

if uploaded_files:
    cols = st.columns(3)
    for idx, uf in enumerate(uploaded_files):
        with cols[idx % 3]:
            # Load into PIL
            try:
                img_bytes = uf.read()
                img = Image.open(io.BytesIO(img_bytes))
                uf.seek(0)  # reset pointer for saving later
            except Exception as e:
                st.error(f"Failed to open {uf.name}: {e}")
                continue

            md = pil_metadata(img)
            exif_md = extract_exif_safe(img) if enable_exif else {}

            # Display
            st.image(img, caption=f"{uf.name} ({md['format']}, {md['width']}x{md['height']})", use_column_width=True)
            st.write(f"**Format:** {md['format']} | **Size:** {md['width']}×{md['height']}")
            if enable_exif and any(exif_md.values()):
                with st.expander("EXIF"):
                    st.json(exif_md)

            # Per-image annotation inputs
            tags = st.text_input(f"Tags for {uf.name}", value=default_tags, key=f"tags_{uf.name}")
            notes = st.text_area(f"Notes for {uf.name}", value=default_notes, key=f"notes_{uf.name}")

            # Save button per image
            if st.button(f"Save annotation for {uf.name}", key=f"save_{uf.name}"):
                stored_path = ""
                github_file_url = ""

                # Local save (if enabled)
                if persist_files_local:
                    stored_path = save_uploaded_file_local(uf)
                    st.success(f"Saved locally: {stored_path}")

                # GitHub push (if enabled)
                if push_to_github:
                    # Choose repo path: keep original filename, but timestamp for uniqueness
                    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                    repo_filename = f"{ts}_{uf.name}"
                    repo_path = f"{gh_target_dir.strip('/')}/{repo_filename}"
                    url = github_put_file(
                        owner=gh_owner,
                        repo=gh_repo,
                        branch=gh_branch,
                        path=repo_path,
                        content_bytes=img_bytes,
                        token=gh_token,
                        message=f"Add image {repo_filename}",
                    )
                    if url:
                        github_file_url = url
                        st.success(f"Pushed to GitHub: {url}")

                # Append new row
                new_row = {
                    "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "filename": uf.name,
                    "stored_path": stored_path or github_file_url,
                    "format": md["format"],
                    "width": md["width"],
                    "height": md["height"],
                    "tags": tags,
                    "notes": notes,
                }
                annotations_df = pd.concat([annotations_df, pd.DataFrame([new_row])], ignore_index=True)
                save_annotations(annotations_df)
                st.success(f"Saved annotations for {uf.name}")

                # Push updated CSV to GitHub (optional)
                if push_to_github:
                    url = github_push_annotation_csv(gh_owner, gh_repo, gh_branch, gh_token, annotations_df, repo_path="data/annotations.csv")
                    if url:
                        st.success(f"Updated GitHub annotations CSV: {url}")


# -------------- Data Review --------------
st.markdown("## 📒 Annotations")
if len(annotations_df) > 0:
    st.dataframe(annotations_df, use_container_width=True)
    with st.expander("Filter / Export"):
        filter_tag = st.text_input("Filter by tag (contains)")
        if filter_tag:
            filtered = annotations_df[annotations_df["tags"].fillna("").str.contains(filter_tag, case=False)]
        else:
            filtered = annotations_df

        st.dataframe(filtered, use_container_width=True)

        col_export1, col_export2 = st.columns(2)
        with col_export1:
            st.download_button(
                label="Download annotations (CSV)",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file_name="annotations_filtered.csv",
                mime="text/csv"
            )
        with col_export2:
            st.download_button(
                label="Download annotations (JSON)",
                data=filtered.to_json(orient="records"),
                file_name="annotations_filtered.json",
                mime="application/json"
            )
else:
    st.info("No annotations yet. Upload images above to get started.")


# -------------- Footer Notes --------------
st.caption("""
Storage notes:
- Local files are saved under `data/uploads` and annotations in `data/annotations.csv`.
- GitHub push uses `st.secrets` for `github_token`, and optional defaults for owner/repo/branch/path.
- On Streamlit Cloud, add secrets in Settings → Secrets, e.g.:

``

