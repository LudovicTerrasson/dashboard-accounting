import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date
from urllib.parse import quote_plus

# 🔐 Connexion BDD
DB_TYPE = st.secrets["DB_TYPE"]
DB_USER = st.secrets["DB_USER"]
DB_PASS = quote_plus(st.secrets["DB_PASS"])
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_NAME = st.secrets["DB_NAME"]

engine = create_engine(f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def nettoyer_nom_campagne(nom_campagne, vertical_name):
    if pd.notnull(vertical_name) and pd.notnull(nom_campagne):
        prefix = vertical_name.strip() + " - "
        if nom_campagne.strip().lower().startswith(prefix.lower()):
            return nom_campagne[len(prefix):]
    return nom_campagne


# 🧠 Chargement des valeurs pour les filtres
@st.cache_data(ttl=3600)
def charger_options():
    with engine.connect() as conn:
        clients_df = pd.read_sql("SELECT id, name FROM client", conn)
        clients_mapping = dict(zip(clients_df["name"], clients_df["id"]))
        clients_names = list(clients_mapping.keys())
        campaigns = pd.read_sql("""
    SELECT DISTINCT c.id, c.name, v.name AS vertical_name
    FROM lead l
    LEFT JOIN campaign c ON l.campaign_id = c.id
    LEFT JOIN vertical v ON c.vertical_id = v.id
    WHERE c.id IS NOT NULL
""", conn)
        verticals = pd.read_sql("SELECT DISTINCT name FROM vertical", conn)["name"].dropna().tolist()
        countries = pd.read_sql("SELECT DISTINCT zipcode FROM registration", conn)["zipcode"].dropna().tolist()
        ads = pd.read_sql("SELECT DISTINCT aff_id FROM stat", conn)["aff_id"].dropna().tolist()

        campaigns["clean_name"] = campaigns.apply(
        lambda row: nettoyer_nom_campagne(row["name"], row["vertical_name"]),
        axis=1
)
    return clients_mapping, campaigns, verticals, countries, ads

clients_mapping, campaigns, verticals, countries, ads = charger_options()

# 🔁 Mapping des campagnes : nom → ID
campaign_mapping = dict(zip(campaigns["name"], campaigns["id"]))
campaign_names = list(campaign_mapping.keys())

client_names = list(clients_mapping.keys())

# === SIDEBAR FILTRES ===
st.sidebar.title("🔍 Filtres")

selected_client_names = st.sidebar.multiselect("Clients", client_names)
selected_clients = [clients_mapping[name] for name in selected_client_names]
selected_campaign_names = st.sidebar.multiselect("Campagnes", campaign_names)
selected_campaigns = [campaign_mapping[name] for name in selected_campaign_names]
selected_verticals = st.sidebar.multiselect("Vertical", verticals)
selected_countries = st.sidebar.multiselect("Code postal", countries)
selected_ads = st.sidebar.multiselect("Ad ID (aff_id)", ads)
date_debut = st.sidebar.date_input("Date de début", date(2024, 1, 1))
date_fin = st.sidebar.date_input("Date de fin", date(2024, 12, 31))

# === CONSTRUCTION REQUÊTE SQL DYNAMIQUE ===
clauses = ["1=1"]
params = {}

if selected_clients:
    clauses.append("s.client IN :clients")
    params["clients"] = tuple(selected_clients)

if selected_campaigns:
    clauses.append("c.id IN :campaigns")
    params["campaigns"] = tuple(selected_campaigns)

if selected_verticals:
    clauses.append("v.name IN :verticals")
    params["verticals"] = tuple(selected_verticals)

if selected_countries:
    clauses.append("r.zipcode IN :countries")
    params["countries"] = tuple(selected_countries)

if selected_ads:
    clauses.append("s.aff_id IN :ads")
    params["ads"] = tuple(selected_ads)

clauses.append("s.lead_created_at BETWEEN :start_date AND :end_date")
params["start_date"] = date_debut
params["end_date"] = date_fin

where_clause = " AND ".join(clauses)

# === REQUÊTE GLOBALE JOINTURE ===
query = text(f"""
SELECT
    s.id AS stat_id,
    cl.name AS client_name,
    s.price_eur,
    s.currency,
    v.name AS vertical_name,
    c.name AS campaign_name,
    l.id AS lead_id,
    l.email AS lead_email,
    r.created_at AS registration_created_at,
    s.lead_created_at,
    r.firstname,
    r.lastname,
    r.zipcode,
    r.city,
    s.aff_id,
    r.others::json->>'source' AS affiliate_name,
    r.others::json->>'aff_sub' AS aff_sub,
    r.others::json->>'aff_sub2' AS aff_sub2,
    r.others::json->>'aff_sub3' AS aff_sub3,
    r.others::json->>'aff_sub4' AS aff_sub4,
    r.others::json->>'aff_sub5' AS aff_sub5,
    r.others::json->>'publisher_id' AS publisher_id,
    r.others::json->>'country' AS country,
    lcls.status AS last_client_status
FROM stat s
JOIN registration r ON r.id = s.registration
LEFT JOIN lead l ON l.registration_id = r.id
LEFT JOIN campaign c ON c.id = l.campaign_id
LEFT JOIN vertical v ON c.vertical_id = v.id
LEFT JOIN client cl ON cl.id = s.client
LEFT JOIN (
    SELECT DISTINCT ON (lead_id) lead_id, status
    FROM lead_client_lead_status
    ORDER BY lead_id, created_at DESC
) lcls ON lcls.lead_id = l.id
WHERE {where_clause}
LIMIT 1000
""")


# === EXÉCUTION REQUÊTE ===
with engine.connect() as conn:
    df = pd.read_sql(query, conn, params=params)

# === AFFICHAGE ===

# Calcul de la chaleur du lead en minutes
df["lead_heat_minutes"] = (
    pd.to_datetime(df["lead_created_at"]) - pd.to_datetime(df["registration_created_at"])
)

df["campaign_name"] = df.apply(
    lambda row: nettoyer_nom_campagne(row["campaign_name"], row["vertical_name"]),
    axis=1
)


def formater_duree(td):
    jours = td.days
    heures, reste = divmod(td.seconds, 3600)
    minutes, _ = divmod(reste, 60)
    return f"{jours}j {heures}h {minutes}m"

df["lead_heat"] = df["lead_heat_minutes"].apply(formater_duree)
df.drop(columns=["lead_heat_minutes"], inplace=True)



# Suppression des colonnes inutiles
colonnes_a_supprimer = ["stat_id", "currency", "firstname", "lastname", "city", "registration_created_at"]
df_clean = df.drop(columns=colonnes_a_supprimer, errors="ignore")

# Affichage
st.title("📊 Résultats filtrés")
st.dataframe(df_clean, use_container_width=True)

# Export
st.download_button(
    "📥 Télécharger CSV",
    df_clean.to_csv(index=False).encode("utf-8"),
    file_name="résultats_filtrés.csv"
)
