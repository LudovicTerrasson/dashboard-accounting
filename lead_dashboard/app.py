import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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

    with st.expander("ℹ️ À propos des KPIs"):
        st.markdown("""
        Cette section présente un résumé des performances des leads sur la période filtrée :
        - **Total leads** : Nombre de leads générés.
        - **Revenu total (€)** : Somme des revenus générés (`stat.price_eur`).
        - **Prix moyen / lead** : Revenu total divisé par le nombre de leads.
        - **Sources uniques** : Nombre d’affiliés / sources différentes.
        - **Chaleur moyenne** : Temps moyen entre l'inscription (`registration.created_at`) et le lead (`stat.lead_created_at`).
        """)

    kpis = compute_kpis(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🧾 Total leads", f"{kpis['total_leads']:,}")
    col2.metric("💰 Revenu total (€)", f"{kpis['total_revenue']:,.2f}")
    col3.metric("💸 Prix moyen / lead", f"{kpis['avg_price']:,.2f}")
    col4.metric("📡 Sources uniques", kpis["unique_sources"])
    col5.metric("🔥 Chaleur moyenne", formater_duree(kpis["avg_heat"]))

    import plotly.graph_objects as go

    monthly_cap = 5000
    leads_this_month = kpis['total_leads']
    progress = leads_this_month / monthly_cap * 100

    with st.expander("ℹ️ Objectif mensuel"):
        st.markdown(f"""
        - Objectif mensuel fixé à **{monthly_cap:,} leads**
        - Leads atteints sur la période : **{leads_this_month:,}**
        - Progression actuelle : **{progress:.1f}%**
        """)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=progress,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Progression vers l'objectif mensuel (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "#FFDDDD"},
                {'range': [50, 80], 'color': "#FFF3B0"},
                {'range': [80, 100], 'color': "#D2F6C5"},
            ],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("ℹ️ Statuts des leads"):
        st.markdown("""
        Ce diagramme montre la répartition des statuts finaux des leads.
        Ces statuts viennent de `lead_client_lead_status.status`, et représentent la décision finale du client sur chaque lead (validé, refusé, etc.).
        """)

    status_counts = df["last_client_status"].fillna("no_status").value_counts()
    fig_status = px.pie(
        names=status_counts.index,
        values=status_counts.values,
        title="Répartition des statuts des leads"
    )
    st.plotly_chart(fig_status, use_container_width=True)

    with st.expander("ℹ️ Vendu vs invendu"):
        st.markdown("""
        Cette visualisation montre la part de leads ayant généré au moins une vente (`stat.number_of_sales > 0`) versus ceux restés invendus.
        """)

    df["is_sold"] = df["number_of_sales"].fillna(0).astype(int) > 0
    vendu = df["is_sold"].sum()
    invendu = (~df["is_sold"]).sum()

    fig_sold = px.pie(
        names=["Vendus", "Invendus"],
        values=[vendu, invendu],
        title="Leads vendus vs invendus"
    )
    st.plotly_chart(fig_sold, use_container_width=True)

    with st.expander("ℹ️ Exclusivité des leads"):
        st.markdown("""
        Les leads exclusifs (`lead.sold_to_exclusive = true`) sont vendus à un seul client.
        Ce graphique permet de suivre la qualité de diffusion et la promesse d’exclusivité si applicable.
        """)

    exclusive = df["sold_to_exclusive"].sum()
    not_exclusive = (~df["sold_to_exclusive"]).sum()

    fig_exclu = px.pie(
        names=["Exclusifs", "Mutualisés"],
        values=[exclusive, not_exclusive],
        title="Exclusivité des leads"
    )
    st.plotly_chart(fig_exclu, use_container_width=True)

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

