import streamlit as st
from sqlalchemy import create_engine
from urllib.parse import quote_plus

def get_engine():
    DB_TYPE = st.secrets["DB_TYPE"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASS = quote_plus(st.secrets["DB_PASS"])
    DB_HOST = st.secrets["DB_HOST"]
    DB_PORT = st.secrets["DB_PORT"]
    DB_NAME = st.secrets["DB_NAME"]

    try:
        return create_engine(
            f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            connect_args={"connect_timeout": 5}
        )
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}") from e

