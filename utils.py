import pandas as pd

def nettoyer_nom_campagne(nom_campagne, vertical_name):
    if pd.notnull(vertical_name) and pd.notnull(nom_campagne):
        prefix = vertical_name.strip() + " - "
        if nom_campagne.strip().lower().startswith(prefix.lower()):
            return nom_campagne[len(prefix):]
    return nom_campagne

def extraire_groupes_villes(campaign_names, villes):
    return {
        ville: [c for c in campaign_names if ville.lower() in c.lower()]
        for ville in villes
        if any(ville.lower() in c.lower() for c in campaign_names)
    }

def formater_duree(td):
    if pd.isnull(td):
        return "–"
    jours = td.days
    heures, reste = divmod(td.seconds, 3600)
    minutes, _ = divmod(reste, 60)
    return f"{jours}j {heures}h {minutes}m"

import streamlit as st
import io

def download_excel_button(df: pd.DataFrame, filename: str = "export.xlsx", label: str = "📥 Télécharger Excel"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=filename,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
