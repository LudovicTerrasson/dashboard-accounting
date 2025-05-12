import streamlit as st
import pandas as pd
from facebook_api import get_facebook_campaign_insights
from utils import download_excel_button
from page_config import set_dashboard_page_config

# Config page
set_dashboard_page_config()
st.title("💸 Dépenses publicitaires – Facebook")

# Récupération des credentials depuis secrets.toml
try:
    access_token = st.secrets["facebook"]["access_token"]
    ad_account_id = st.secrets["facebook"]["ad_account_id"]
except KeyError:
    st.error("❌ Veuillez configurer votre fichier secrets.toml avec vos identifiants Facebook API.")
    st.stop()

# Sélection période (Facebook utilise des presets, pas une plage personnalisée ici)
date_presets = {
    "Aujourd'hui": "today",
    "Hier": "yesterday",
    "7 derniers jours": "last_7d",
    "Ce mois-ci": "this_month",
    "Mois dernier": "last_month"
}
selected_preset = st.selectbox("📅 Période", options=list(date_presets.keys()))
preset_key = date_presets[selected_preset]

# Appel API
with st.spinner("🔄 Récupération des données Facebook..."):
    try:
        df_fb = get_facebook_campaign_insights(ad_account_id, access_token, date_preset=preset_key)
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API Facebook : {e}")
        st.stop()

# Affichage
if df_fb.empty:
    st.warning("Aucune donnée trouvée pour la période sélectionnée.")
else:
    st.dataframe(df_fb, use_container_width=True)
    download_excel_button(df_fb, filename="facebook_insights.xlsx", label="📥 Exporter Excel")
