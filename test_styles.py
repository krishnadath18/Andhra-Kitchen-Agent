"""Quick test to verify styles are working"""
import streamlit as st

st.set_page_config(page_title="Style Test", layout="wide")

# Test 1: Simple inline style
st.markdown('<div style="color: red;">This should be RED</div>', unsafe_allow_html=True)

# Test 2: Style tag
st.markdown("""
<style>
.test-class {
    color: blue;
    font-size: 24px;
}
</style>
<div class="test-class">This should be BLUE and LARGE</div>
""", unsafe_allow_html=True)

# Test 3: Check if styles module works
try:
    from ui.styles import get_global_styles
    styles = get_global_styles()
    st.write(f"Styles length: {len(styles)} characters")
    st.write(f"Starts with: {styles[:100]}")
    st.markdown(styles, unsafe_allow_html=True)
    st.success("Styles applied!")
except Exception as e:
    st.error(f"Error: {e}")

st.write("If you see CSS text above, unsafe_allow_html is not working properly")
