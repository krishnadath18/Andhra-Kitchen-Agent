"""Minimal test to isolate the CSS rendering issue"""
import streamlit as st

st.set_page_config(page_title="CSS Test", layout="wide")

# Test if unsafe_allow_html works at all
st.markdown('<h1 style="color: red;">This should be RED</h1>', unsafe_allow_html=True)

# Test style tag
css = """
<style>
.test {
    color: blue;
    font-size: 30px;
}
</style>
<div class="test">This should be BLUE and BIG</div>
"""

st.markdown(css, unsafe_allow_html=True)

st.write("---")
st.write("If you see CSS code as text above, there's a Streamlit configuration issue")
