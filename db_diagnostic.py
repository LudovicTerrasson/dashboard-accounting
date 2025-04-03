import streamlit as st
import socket
import psycopg2

st.title("🛠 Diagnostic Connexion PostgreSQL")

host = st.secrets["DB_HOST"]
port = int(st.secrets["DB_PORT"])
user = st.secrets["DB_USER"]
dbname = st.secrets["DB_NAME"]

# 1. DNS
st.subheader("1️⃣ Résolution DNS")
try:
    ip = socket.gethostbyname(host)
    st.success(f"✅ Résolution DNS OK : {host} -> {ip}")
except Exception as e:
    st.error(f"❌ DNS fail: {e}")

# 2. Connexion réseau
st.subheader("2️⃣ Test Connexion réseau")
try:
    with socket.create_connection((host, port), timeout=5):
        st.success(f"✅ Réseau OK vers {host}:{port}")
except Exception as e:
    st.error(f"❌ Connexion réseau échouée : {e}")

# 3. Connexion PostgreSQL (psycopg2)
st.subheader("3️⃣ Connexion PostgreSQL (psycopg2)")
try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=st.secrets["DB_PASS"],
        host=host,
        port=port
    )
    st.success("✅ Connexion PostgreSQL réussie")
    conn.close()
except Exception as e:
    st.error(f"❌ Connexion échouée : {e}")
