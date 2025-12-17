import streamlit as st
import pandas as pd

# Load the Excel file
# Assume the Excel file is named 'data.xlsx' and is in the same directory
# Columns: 'Module', 'Subcategory', 'Segment', 'Image_URL', 'Link'
df = pd.read_excel('data.xlsx')

# Get unique modules
modules = df['Module'].unique()

# Streamlit app
st.title('Product Selector')

# Select Module
selected_module = st.selectbox('Select Module', modules)

# Filter subcategories based on selected module
subcats = df[df['Module'] == selected_module]['Subcategory'].unique()
selected_subcat = st.selectbox('Select Subcategory', subcats)

# Filter segments based on selected module and subcat
segments = df[(df['Module'] == selected_module) & (df['Subcategory'] == selected_subcat)]['Segment'].unique()
selected_segment = st.selectbox('Select Segment', segments)

# Get the row for the selected combination
selected_row = df[(df['Module'] == selected_module) & 
                  (df['Subcategory'] == selected_subcat) & 
                  (df['Segment'] == selected_segment)].iloc[0]

# Display image and link
st.image(selected_row['Image_URL'], caption='Product Image')
st.write('Link:', selected_row['Link'])
