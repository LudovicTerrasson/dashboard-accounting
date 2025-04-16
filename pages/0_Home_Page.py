import streamlit as st
from page_config import set_dashboard_page_config

set_dashboard_page_config()

st.title("🏠 Dashboard Performance Leads")

st.markdown("""
Bienvenue dans le dashboard d’analyse des performances de génération de leads.

🔍 **Deux sections sont disponibles** :

### 📊 V0 – Vue globale
- Vue d’ensemble sur toutes les campagnes et clients
- Filtres transverses : client, vertical, ad ID, période...
- KPIs, tableaux de volume, chaleur, statuts…

### 📦 Par campagne
- Analyse détaillée d’une campagne spécifique
- Objectifs, jauges, performances et statuts
- Sans interférence des filtres globaux

---

👉 Utilisez le menu à gauche pour naviguer entre les pages.
""")
