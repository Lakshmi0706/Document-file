
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

