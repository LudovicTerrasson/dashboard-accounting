import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import date, timedelta

import streamlit as st

DB_TYPE = 'postgresql+psycopg2'
DB_USER = st.secrets["DB_USER"]
DB_PASS = st.secrets["DB_PASS"]
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_NAME = st.secrets["DB_NAME"]


engine = create_engine(f'{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

st.set_page_config(page_title="Dashboard Accounting", layout="wide")

st.title("📊 Dashboard Accounting (Version Table Unique)")

# Filtrage global
st.sidebar.header("Filtres globaux")

date_debut = st.sidebar.date_input("📅 Date de début", date(2020, 1, 1))
date_fin = st.sidebar.date_input("📅 Date de fin", date(2020, 12, 31))

query = f"""
SELECT * FROM accounting
WHERE date BETWEEN '{date_debut}' AND '{date_fin}'
"""

df = pd.read_sql(query, engine)

# Onglets
onglet = st.tabs(["👤 Par Client", "🎯 Par Campagne", "🌍 Par Pays"])

# Onglet Client
with onglet[0]:
    st.subheader("👤 Vue par client")
    clients = df["client_id"].unique()
    client_filtre = st.multiselect("Sélectionner un ou plusieurs clients", clients, default=clients)

    df_client = df[df["client_id"].isin(client_filtre)]
    df_grouped = df_client.groupby("client_id").agg({
        "leads": "sum",
        "cancelation": "sum",
        "net_leads": "sum",
        "total": "sum",
        "validated": "sum",
        "invoiced": "sum"
    }).reset_index()

    st.dataframe(df_grouped)

    st.download_button("📥 Télécharger CSV - Clients", df_grouped.to_csv(index=False).encode('utf-8'),
                       file_name="rapport_par_client.csv", mime="text/csv")

# Onglet Campagne
with onglet[1]:
    st.subheader("🎯 Vue par campagne")
    campagnes = df["campaign_id"].unique()
    campagne_filtre = st.multiselect("Sélectionner une ou plusieurs campagnes", campagnes, default=campagnes)

    df_campagne = df[df["campaign_id"].isin(campagne_filtre)]
    df_grouped = df_campagne.groupby("campaign_id").agg({
        "leads": "sum",
        "cancelation": "sum",
        "net_leads": "sum",
        "total": "sum",
        "validated": "sum",
        "invoiced": "sum"
    }).reset_index()

    st.dataframe(df_grouped)

    st.download_button("📥 Télécharger CSV - Campagnes", df_grouped.to_csv(index=False).encode('utf-8'),
                       file_name="rapport_par_campagne.csv", mime="text/csv")

# Onglet Pays
with onglet[2]:
    st.subheader("🌍 Vue par pays")
    pays = df["country_id"].unique()
    pays_filtre = st.multiselect("Sélectionner un ou plusieurs pays", pays, default=pays)

    df_pays = df[df["country_id"].isin(pays_filtre)]
    df_grouped = df_pays.groupby("country_id").agg({
        "leads": "sum",
        "cancelation": "sum",
        "net_leads": "sum",
        "total": "sum",
        "validated": "sum",
        "invoiced": "sum"
    }).reset_index()

    st.dataframe(df_grouped)

    st.download_button("📥 Télécharger CSV - Pays", df_grouped.to_csv(index=False).encode('utf-8'),
                       file_name="rapport_par_pays.csv", mime="text/csv")
