import streamlit as st
import plotly.graph_objects as go
from utils import download_excel_button
import plotly.express as px
import pandas as pd
from datetime import datetime
from sqlalchemy.sql import text
from config import get_engine
from page_config import set_dashboard_page_config
from kpis import compute_kpis
from utils import formater_duree
from visuals import (
    show_leads_volume_chart,
    show_status_by_source_pivot
)

set_dashboard_page_config()

# Connexion BDD
engine = get_engine()

# === Filtres dans la sidebar ===
st.sidebar.title("🎯 Filtres Campagne")

today = datetime.today()
start_date = st.sidebar.date_input("Date de début", today.replace(day=1))
end_date = st.sidebar.date_input("Date de fin", today)

# Afficher le Top 10 des campagnes par revenu total
with engine.connect() as conn:
    top_query = text("""
        SELECT 
            c.name AS campaign_name, 
            COUNT(DISTINCT s.id) AS total_leads, 
            SUM(s.price_eur) AS total_revenue, 
            ROUND(AVG(s.price_eur)::numeric, 2) AS avg_price
        FROM stat s
        JOIN registration r ON r.id = s.registration
        LEFT JOIN lead l ON l.registration_id = r.id
        LEFT JOIN campaign c ON c.id = l.campaign_id
        WHERE s.lead_created_at BETWEEN :start_date AND :end_date
        GROUP BY c.name
        ORDER BY total_revenue DESC
        LIMIT 10

    """)
    top_df = pd.read_sql(top_query, conn, params={"start_date": start_date, "end_date": end_date})
    default_campaign = top_df["campaign_name"].iloc[0] if not top_df.empty else None


status_options = ['enabled', 'paused', 'disabled', 'NULL']
selected_statuses = st.sidebar.multiselect(
    "Statuts de campagnes",
    options=status_options,
    default=['enabled']
)



# Campagne à analyser
with engine.connect() as conn:
    if selected_statuses:
        placeholders = ",".join(f"'{s}'" for s in selected_statuses if s != 'NULL')
        null_clause = "OR status IS NULL" if 'NULL' in selected_statuses else ""
        query_str = f"""
            SELECT DISTINCT name FROM campaign
            WHERE name IS NOT NULL
            AND (status IN ({placeholders}) {null_clause})
            ORDER BY name
        """
    else:
        query_str = """
            SELECT DISTINCT name FROM campaign
            WHERE name IS NOT NULL
            ORDER BY name
        """
    campagnes = pd.read_sql(query_str, conn)["name"].tolist()

selected_campagne = st.sidebar.selectbox(
    "Campagne à analyser",
    campagnes,
    index=campagnes.index(default_campaign) if default_campaign in campagnes else 0
)

# Chargement données
query = text("""
    SELECT
        s.id AS stat_id,
        cl.name AS client_name,
        s.price_eur,
        s.number_of_sales,
        r.sold_to_exclusive,
        s.currency,
        v.name AS vertical_name,
        c.name AS campaign_name,
        c.daily_cap,
        c.monthly_cap,
        r.id AS registration_id,
        l.id AS lead_id,
        r.created_at AS registration_created_at,
        s.lead_created_at,
        r.firstname,
        r.lastname,
        r.zipcode,
        r.city,
        s.aff_id,
        r.others::json->>'source' AS affiliate_name,
        r.others::json->>'aff_sub' AS aff_sub,
        l.last_lead_client_status AS last_client_status
    FROM stat s
    JOIN registration r ON r.id = s.registration
    LEFT JOIN lead l ON l.registration_id = r.id
    LEFT JOIN campaign c ON c.id = l.campaign_id
    LEFT JOIN vertical v ON c.vertical_id = v.id
    LEFT JOIN client cl ON cl.id = s.client
    WHERE c.name = :campagne AND s.lead_created_at BETWEEN :start_date AND :end_date
""")

params = {"campagne": selected_campagne, "start_date": start_date, "end_date": end_date}
with engine.connect() as conn:
    df = pd.read_sql(query, conn, params=params)

kpis = compute_kpis(df)
df["jour"] = pd.to_datetime(df["lead_created_at"]).dt.date
cap_par_jour = df.groupby("jour")["daily_cap"].max().fillna(0).astype(int)
real_daily_cap_total = cap_par_jour.sum()
monthly_cap_vals = df["monthly_cap"].dropna().astype(int).unique()
monthly_cap_total = int(monthly_cap_vals[0]) if len(monthly_cap_vals) > 0 else 0
monthly_cap_adjusted = int(monthly_cap_total * ((end_date - start_date).days + 1) / 30)
leads_this_period = kpis["total_leads"]

values = {
    "Leads générés": leads_this_period,
    "Cap réel (daily_cap jour/jour)": real_daily_cap_total,
    "Cap indicatif (monthly_cap)": monthly_cap_adjusted,
}
fig_bar = go.Figure(go.Bar(
    x=list(values.values()),
    y=list(values.keys()),
    orientation='h',
    text=[f"{v:,}" for v in values.values()],
    textposition="auto",
    marker=dict(color=["#1f77b4", "#2ca02c", "#ff7f0e"])
))
fig_bar.update_layout(
    title="Comparaison des volumes et caps sur la période sélectionnée",
    xaxis_title="Nombre de leads",
    yaxis=dict(autorange="reversed"),
    height=320
)

status_counts = df["last_client_status"].fillna("no_status").value_counts()
fig_status = px.pie(
    names=status_counts.index,
    values=status_counts.values,
    title="Répartition des statuts des leads"
)

df["statut_simplifié"] = df["last_client_status"].fillna("no_status").apply(
    lambda x: "Vente" if x.lower() == "sale" else "Non vendu"
)
transfo_counts = df["statut_simplifié"].value_counts()
fig_transfo = px.pie(
    names=transfo_counts.index,
    values=transfo_counts.values,
    title="Part des leads transformés (Sale) vs non transformés"
)

fig_line = px.line(
    cap_par_jour.reset_index(),
    x="jour",
    y="daily_cap",
    title="Cap réel journalier (daily_cap par jour)",
    markers=True
)

# === TABS ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 Vue d’ensemble",
    "📊 Volume",
    "🧠 Analyse approfondie",
    "🤖 Modèles & outils",
    "📋 Données"
])

with tab1:
    st.subheader("🏆 Top 10 campagnes par revenu total (€)")
    st.dataframe(top_df, use_container_width=True)
    download_excel_button(top_df, filename="top10.xlsx", label="⬇️ Exporter les données en Excel")
    st.subheader("📌 Indicateurs clés")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🧾 Total leads", f"{kpis['total_leads']:,}")
    col2.metric("💰 Revenu total (€)", f"{kpis['total_revenue']:,.2f}")
    col3.metric("💸 Prix moyen / lead", f"{kpis['avg_price']:,.2f}")
    col4.metric("📡 Sources uniques", kpis["unique_sources"])
    col5.metric("🔥 Chaleur moyenne", formater_duree(kpis["avg_heat"]))

    st.subheader("📊 Comparatif : Leads vs Cap réel et indicatif")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("""
    - 🟦 Leads générés sur la période
    - 🟩 Cap réel : somme des `daily_cap` jour par jour (variation possible)
    - 🟧 Cap indicatif basé sur `monthly_cap` unique de la campagne
    """)

    st.subheader("📊 Répartition des statuts et taux de transformation")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_status, use_container_width=True)
    with col2:
        st.plotly_chart(fig_transfo, use_container_width=True)


with tab2:
    st.subheader("📊 Volume journalier")
    show_leads_volume_chart(df)

    st.subheader("📈 Évolution du cap journalier réel")
    st.plotly_chart(fig_line, use_container_width=True)


with tab3:
    st.subheader("📊 Statuts des leads")
    show_status_by_source_pivot(df)

with tab4:
    st.subheader("🤖 Modèles de prédiction & outils exploratoires")
    st.info("Section prévue pour ajouter des outils ou modèles à l’avenir.")

with tab5:
    st.subheader("📋 Données filtrées")
    st.dataframe(df, use_container_width=True)
    download_excel_button(df, filename="leads_filtrés.xlsx", label="⬇️ Exporter les données en Excel")

