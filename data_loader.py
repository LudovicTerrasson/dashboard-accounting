import pandas as pd
import streamlit as st
from config import get_engine
from utils import nettoyer_nom_campagne

engine = get_engine()

@st.cache_data(ttl=3600)
def load_filter_data():
    with engine.connect() as conn:
        clients_df = pd.read_sql("SELECT id, name FROM client", conn)
        clients_mapping = dict(zip(clients_df["name"], clients_df["id"]))

        campaigns = pd.read_sql("""
            SELECT DISTINCT c.id, c.name, v.name AS vertical_name
            FROM lead l
            JOIN campaign c ON c.id = l.campaign_id
            LEFT JOIN vertical v ON c.vertical_id = v.id
        """, conn)

        campaigns["clean_name"] = campaigns.apply(
            lambda row: nettoyer_nom_campagne(row["name"], row["vertical_name"]),
            axis=1
        )

        return {
            "clients": clients_mapping,
            "campaigns": campaigns,
            "verticals": pd.read_sql("SELECT DISTINCT name FROM vertical", conn)["name"].dropna().tolist(),
            "countries": pd.read_sql("SELECT DISTINCT zipcode FROM registration", conn)["zipcode"].dropna().tolist(),
            "ads": pd.read_sql("SELECT DISTINCT aff_id FROM stat", conn)["aff_id"].dropna().tolist()
        }

def load_main_dataframe(query, params):
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)
