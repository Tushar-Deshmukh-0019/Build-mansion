import streamlit as st
from parser import parse_logic
from codegen import generate_python

st.set_page_config(page_title="Logico", layout="centered")

st.title("🧠 Logico- where logic meets Code")
st.write("Convert natural logic into executable code")

user_input = st.text_area("Enter your logic:")

if st.button("Generate Code"):

    ast = parse_logic(user_input)

    st.subheader("🧠 Parsed AST (Proof)")
    st.json(ast)

    code = generate_python(ast)

    st.subheader("⚙️ Generated Code")
    st.code(code, language="python")

    if "# Unsupported" not in code:
        st.success("✅ Code generated successfully")
    else:
        st.error("❌ Logic not supported yet")