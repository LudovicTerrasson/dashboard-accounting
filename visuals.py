import streamlit as st
import pandas as pd
import plotly.express as px
from utils import formater_duree, download_excel_button

# === Chart: Volume de leads par jour ===
def show_leads_volume_chart(df):
    df["jour"] = pd.to_datetime(df["lead_created_at"]).dt.date
    evol_data = df.groupby("jour").agg(
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

# === Table: Volume par jour et source ===
def show_source_by_day_pivot(df):
    st.header("📊 Analyse quotidienne par source (Volume-Ventilation)")

    if df.empty:
        st.info("Aucune donnée disponible pour les filtres sélectionnés.")
        return

    df["jour"] = pd.to_datetime(df["lead_created_at"]).dt.date
    df["source"] = df["affiliate_name"].fillna("unknown")

    grouped = df.groupby(["jour", "source"]).size().reset_index(name="volume")
    totals = grouped.groupby("jour")["volume"].transform("sum")
    grouped["ventilation"] = (grouped["volume"] / totals * 100).round(0).astype(int)
    grouped["cell"] = grouped["volume"].astype(str) + " – " + grouped["ventilation"].astype(str) + "%"

    pivot = grouped.pivot(index="source", columns="jour", values="cell").fillna("0 – 0%").sort_index()

    st.dataframe(pivot, use_container_width=True)
    download_excel_button(
        df=pivot.reset_index(),
        filename="source_jour_filtrées.xlsx",
        label="📥 Télécharger le tableau (Excel)"
    )

# === Table: Fraîcheur des leads ===
def show_lead_freshness_pivot(df):
    st.header("📊 Ventilation des leads par fraîcheur (Volume-Ventilation)")

    if df.empty:
        st.info("Aucune donnée disponible pour les filtres sélectionnés.")
        return

    df["delai"] = pd.to_datetime(df["lead_created_at"]) - pd.to_datetime(df["registration_created_at"])

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

    df["catégorie"] = df["delai"].apply(catégoriser_délai)
    df["jour"] = pd.to_datetime(df["lead_created_at"]).dt.date

    grouped = df.groupby(["jour", "catégorie"]).size().reset_index(name="volume")
    totals = grouped.groupby("jour")["volume"].transform("sum")
    grouped["ventilation"] = (grouped["volume"] / totals * 100).round(0).astype(int)

    grouped["cell"] = grouped["volume"].astype(str) + " (" + grouped["ventilation"].astype(str) + "%)"
    pivot = grouped.pivot(index="catégorie", columns="jour", values="cell").fillna("0 (0%)")

    st.dataframe(pivot, use_container_width=True)
    download_excel_button(
        df=pivot.reset_index(),
        filename="ventilation_fraicheur_leads.xlsx",
        label="📥 Télécharger tableau fraîcheur (Excel)"
    )

# === Table: Statuts par source ===
def show_status_by_source_pivot(df):
    st.header("📊 Détail des statuts par source")

    if df.empty:
        st.info("Aucune donnée disponible pour les filtres sélectionnés.")
        return

    df["source"] = df["affiliate_name"].fillna("unknown")
    df["statut"] = df["last_client_status"].fillna("no_status")

    grouped = df.groupby(["source", "statut"]).size().reset_index(name="volume")
    totals = grouped.groupby("source")["volume"].transform("sum")
    grouped["ventilation"] = (grouped["volume"] / totals * 100).round(0).astype(int)

    grouped["cell"] = grouped["volume"].astype(str) + " (" + grouped["ventilation"].astype(str) + "%)"
    pivot = grouped.pivot(index="source", columns="statut", values="cell").fillna("0 (0%)")

    st.dataframe(pivot, use_container_width=True)
    download_excel_button(
        df=pivot.reset_index(),
        filename="statuts_par_source.xlsx",
        label="📥 Télécharger le tableau des statuts (Excel)"
    )
