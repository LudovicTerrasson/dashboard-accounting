import streamlit as st
from datetime import datetime
from page_config import set_dashboard_page_config
from filters import build_filters
from data_loader import load_filter_data, load_main_dataframe
from queries import build_main_query
from kpis import compute_kpis
from visuals import (
    show_leads_volume_chart,
    show_source_by_day_pivot,
    show_lead_freshness_pivot,
    show_status_by_source_pivot
)
from utils import nettoyer_nom_campagne, formater_duree

# === Config de la page ===
set_dashboard_page_config()

# === Chargement des options de filtre ===
filter_data = load_filter_data()
clients_mapping = filter_data["clients"]
campaigns_df = filter_data["campaigns"]
verticals = filter_data["verticals"]
countries = filter_data["countries"]
ads = filter_data["ads"]

# === Filtres dans la sidebar ===
selections = build_filters(clients_mapping, campaigns_df, verticals, countries, ads)
today = datetime.today()
start_date = st.sidebar.date_input("Date de début", today.replace(day=1))
end_date = st.sidebar.date_input("Date de fin", today)

# === Construction de la requête SQL dynamique ===
clauses = ["1=1"]
params = {}

if selections["clients"]:
    clauses.append("s.client IN :clients")
    params["clients"] = tuple(selections["clients"])

if selections["campaigns"]:
    clauses.append("c.id IN :campaigns")
    params["campaigns"] = tuple(selections["campaigns"])

if selections["verticals"]:
    clauses.append("v.name IN :verticals")
    params["verticals"] = tuple(selections["verticals"])

if selections["countries"]:
    clauses.append("r.zipcode IN :countries")
    params["countries"] = tuple(selections["countries"])

if selections["ads"]:
    clauses.append("s.aff_id IN :ads")
    params["ads"] = tuple(selections["ads"])

clauses.append("s.lead_created_at BETWEEN :start_date AND :end_date")
params["start_date"] = start_date
params["end_date"] = end_date

# === Exécution de la requête ===
query = build_main_query(" AND ".join(clauses))
df = load_main_dataframe(query, params)
df["campaign_name"] = df.apply(lambda row: nettoyer_nom_campagne(row["campaign_name"], row["vertical_name"]), axis=1)
df_display = df.drop(columns=["stat_id", "currency", "firstname", "lastname", "city", "registration_created_at"], errors="ignore")

# === TABS ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Données",
    "📌 Vue d’ensemble",
    "📊 Volume",
    "🧠 Analyse approfondie",
    "🤖 Modèles & outils"
])

# === ONGLET 1 : Données ===
with tab1:
    st.subheader("📋 Résultats filtrés")
    st.dataframe(df_display, use_container_width=True)
    st.download_button(
        "📥 Télécharger CSV",
        df_display.to_csv(index=False).encode("utf-8"),
        file_name="résultats_filtrés.csv"
    )

# === ONGLET 2 : KPIs ===
with tab2:
    st.subheader("📌 Indicateurs clés")
    kpis = compute_kpis(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🧾 Total leads", f"{kpis['total_leads']:,}")
    col2.metric("💰 Revenu total (€)", f"{kpis['total_revenue']:,.2f}")
    col3.metric("💸 Prix moyen / lead", f"{kpis['avg_price']:,.2f}")
    col4.metric("📡 Sources uniques", kpis["unique_sources"])
    col5.metric("🔥 Chaleur moyenne", formater_duree(kpis["avg_heat"]))

# === ONGLET 3 : Graphique volume ===
with tab3:
    st.subheader("📊 Volume de leads par jour")
    show_leads_volume_chart(df_display)

# === ONGLET 4 : Analyse approfondie ===
with tab4:
    show_source_by_day_pivot(df_display)
    show_lead_freshness_pivot(df)
    show_status_by_source_pivot(df_display)

# === ONGLET 5 : Prévu pour ML & autres outils ===
with tab5:
    st.subheader("🤖 Modèles de prédiction & outils exploratoires")
    st.info("Cette section est réservée à l'ajout futur de modèles machine learning, de jauges de progression, ou d'outils de qualité.")

