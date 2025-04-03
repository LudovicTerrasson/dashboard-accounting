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
    JOIN campaign c ON c.id = l.campaign_id
    LEFT JOIN vertical v ON c.vertical_id = v.id
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

# === AJOUT FILTRE PAR VILLE ===

# 🌍 Liste de villes à détecter automatiquement dans les campagnes
villes_connues = [
    "Abidjan", "Dakar", "Paris", "Casablanca", "Tunis",
    "Lyon", "Yaoundé", "Alger", "Bruxelles", "Marseille"
]

# 🧰 Mapping villes -> campagnes contenant le nom de la ville
def extraire_groupes_villes(campaign_names, villes):
    mapping = {}
    for ville in villes:
        correspondantes = [c for c in campaign_names if ville.lower() in c.lower()]
        if correspondantes:
            mapping[ville] = correspondantes
    return mapping

ville_mapping = extraire_groupes_villes(campaign_names, villes_connues)
villes_detectees = list(ville_mapping.keys())

# === SIDEBAR FILTRES ===
st.sidebar.title("🔍 Filtres")

# === Clients ===
selected_client_names = st.sidebar.multiselect("Clients", client_names)
selected_clients = [clients_mapping[name] for name in selected_client_names]

# === Campagnes ===
selected_campaign_names = st.sidebar.multiselect("Campagnes", campaign_names)

# 🌍 Localisation (groupes de campagnes détectés par nom de ville)
villes_connues = [
    "Abidjan", "Dakar", "Paris", "Casablanca", "Tunis",
    "Lyon", "Yaoundé", "Alger", "Bruxelles", "Marseille"
]

def extraire_groupes_villes(campaign_names, villes):
    mapping = {}
    for ville in villes:
        correspondantes = [c for c in campaign_names if ville.lower() in c.lower()]
        if correspondantes:
            mapping[ville] = correspondantes
    return mapping

ville_mapping = extraire_groupes_villes(campaign_names, villes_connues)
villes_detectees = list(ville_mapping.keys())
selected_villes = st.sidebar.multiselect("📍 Localisation (par ville détectée)", villes_detectees)

# Ajout des campagnes correspondant aux villes sélectionnées
campagnes_villes = []
for ville in selected_villes:
    campagnes_villes.extend(ville_mapping[ville])

# Fusion des campagnes sélectionnées manuellement et par localisation
selected_campaign_names = list(set(selected_campaign_names + campagnes_villes))
selected_campaigns = [campaign_mapping[name] for name in selected_campaign_names if name in campaign_mapping]

# === Verticales ===
selected_verticals = st.sidebar.multiselect("Verticales", verticals)

# === Code postal ===
selected_countries = st.sidebar.multiselect("Code postal", countries)

# === Ads (aff_id) ===
selected_ads = st.sidebar.multiselect("Ad ID (aff_id)", ads)

# === Dates ===
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

# === KPIs ===
st.subheader("📌 Indicateurs clés")

# Durée brute avant formatage
df["lead_heat_minutes"] = (
    pd.to_datetime(df["lead_created_at"]) - pd.to_datetime(df["registration_created_at"])
)

# Moyenne en timedelta
mean_heat_timedelta = df["lead_heat_minutes"].mean()

# Fonction pour formatage lisible
def formater_duree(td):
    if pd.isnull(td):
        return "–"
    jours = td.days
    heures, reste = divmod(td.seconds, 3600)
    minutes, _ = divmod(reste, 60)
    return f"{jours}j {heures}h {minutes}m"

# Application du format lisible à la colonne
df["lead_heat"] = df["lead_heat_minutes"].apply(formater_duree)
df.drop(columns=["lead_heat_minutes"], inplace=True)

# Calcul KPIs
kpi_total_leads = len(df)
kpi_revenu_total = df["price_eur"].sum()
kpi_prix_moyen = df["price_eur"].mean()
kpi_nb_sources = df["affiliate_name"].nunique()
kpi_duree_moyenne = formater_duree(mean_heat_timedelta)

# Affichage
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🧾 Total leads", f"{kpi_total_leads:,}")
col2.metric("💰 Revenu total (€)", f"{kpi_revenu_total:,.2f}")
col3.metric("💸 Prix moyen / lead", f"{kpi_prix_moyen:,.2f}")
col4.metric("📡 Sources uniques", kpi_nb_sources)
col5.metric("🔥 Durée moyenne", kpi_duree_moyenne)


import plotly.express as px

# Préparation des données d'évolution
df_evolution = df_clean.copy()
df_evolution["jour"] = pd.to_datetime(df_evolution["lead_created_at"]).dt.date

evol_data = df_evolution.groupby("jour").agg(
    volume=("lead_id", "count"),
    revenu=("price_eur", "sum")
).reset_index()

fig = px.bar(
    evol_data,
    x="jour",
    y="volume",
    title="📊 Volume de leads par jour",
    labels={"jour": "Date", "volume": "Nombre de leads"},
    height=300
)

st.plotly_chart(fig, use_container_width=True)


# Affichage
st.title("📊 Résultats filtrés")
st.dataframe(df_clean, use_container_width=True)

# Export
st.download_button(
    "📥 Télécharger CSV",
    df_clean.to_csv(index=False).encode("utf-8"),
    file_name="résultats_filtrés.csv"
)


# === TABLEAU PAR SOURCE ET JOUR POUR UNE CAMPAGNE ===

st.header("📊 Analyse quotidienne par source")

df_campagne = df_clean.copy()

# --- Préparation des champs ---
df_campagne["jour"] = pd.to_datetime(df_campagne["lead_created_at"]).dt.date
df_campagne["source"] = df_campagne["affiliate_name"].fillna("unknown")

if df_campagne.empty:
    st.info("Aucune donnée disponible pour les filtres sélectionnés.")
else:
    # --- Agrégation Volume + Ventilation ---
    grouped = df_campagne.groupby(["jour", "source"]).size().reset_index(name="volume")
    totals = grouped.groupby("jour")["volume"].transform("sum")
    grouped["ventilation"] = (grouped["volume"] / totals * 100).round(0).astype(int)

    # --- Format Volume – Ventilation% ---
    grouped["cell"] = grouped["volume"].astype(str) + " – " + grouped["ventilation"].astype(str) + "%"

    # --- Pivot du tableau ---
    pivot = grouped.pivot(index="source", columns="jour", values="cell").fillna("0 – 0%").sort_index()

    if pivot.empty:
        st.info("Aucune donnée à afficher pour les jours disponibles dans cette période.")
    else:
        # --- Affichage du tableau ---
        st.subheader("🧾 Détail par source pour les campagnes filtrées")
        st.dataframe(pivot, use_container_width=True)

        # --- Export CSV du tableau ---
        csv_export = pivot.reset_index().to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger le tableau (CSV)",
            data=csv_export,
            file_name="source_jour_filtrées.csv",
            mime="text/csv"
        )

# === TABLEAU FRAÎCHEUR DES LEADS ===

st.header("📊 Ventilation des leads par fraîcheur")

df_fraicheur = df.copy()  # On repart du df d’origine car on a besoin de registration_created_at

# Calcul du délai en minutes
df_fraicheur["delai"] = pd.to_datetime(df_fraicheur["lead_created_at"]) - pd.to_datetime(df_fraicheur["registration_created_at"])

# Catégorisation des délais
def catégoriser_délai(td):
    minutes = td.total_seconds() / 60
    if minutes < 5:
        return "moins 5min"
    elif minutes < 60:
        return "entre 5min à 1h"
    elif minutes < 600:
        return "entre 1h à 10h"
    elif minutes < 1440:
        return "Leads de la veille"
    else:
        return "Leads de 2j"

df_fraicheur["catégorie"] = df_fraicheur["delai"].apply(catégoriser_délai)
df_fraicheur["jour"] = pd.to_datetime(df_fraicheur["lead_created_at"]).dt.date

# Agrégation volume + ventilation
grouped = df_fraicheur.groupby(["jour", "catégorie"]).size().reset_index(name="volume")
totaux = grouped.groupby("jour")["volume"].transform("sum")
grouped["ventilation"] = (grouped["volume"] / totaux * 100).round(0).astype(int)

# Création du tableau combiné volume + ventilation
grouped["cell"] = grouped["volume"].astype(str) + " (" + grouped["ventilation"].astype(str) + "%)"
pivot_fraicheur = grouped.pivot(index="catégorie", columns="jour", values="cell").fillna("0 (0%)")

# Affichage dans Streamlit
st.dataframe(pivot_fraicheur, use_container_width=True)

# Export CSV
csv_export_fraicheur = pivot_fraicheur.reset_index().to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Télécharger tableau fraîcheur (CSV)",
    data=csv_export_fraicheur,
    file_name="ventilation_fraicheur_leads.csv",
    mime="text/csv"
)

# === TABLEAU PAR STATUT ET SOURCE ===

st.header("📊 Détail des statuts par source")

df_status = df_clean.copy()

# Remplissage des valeurs manquantes
df_status["source"] = df_status["affiliate_name"].fillna("unknown")
df_status["statut"] = df_status["last_client_status"].fillna("no_status")

# Agrégation volume par source et statut
grouped = df_status.groupby(["source", "statut"]).size().reset_index(name="volume")
totaux = grouped.groupby("source")["volume"].transform("sum")
grouped["ventilation"] = (grouped["volume"] / totaux * 100).round(0).astype(int)

# Format combiné
grouped["cell"] = grouped["volume"].astype(str) + " (" + grouped["ventilation"].astype(str) + "%)"

# Tableau croisé dynamique
pivot_status = grouped.pivot(index="source", columns="statut", values="cell").fillna("0 (0%)")

# Affichage
st.dataframe(pivot_status, use_container_width=True)

# Export
csv_export_status = pivot_status.reset_index().to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Télécharger le tableau des statuts (CSV)",
    data=csv_export_status,
    file_name="statuts_par_source.csv",
    mime="text/csv"
)
