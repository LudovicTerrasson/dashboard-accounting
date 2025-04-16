import streamlit as st
from utils import extraire_groupes_villes

def build_filters(clients_mapping, campaigns_df, verticals, countries, ads):
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.title("🔍 Filtres")

    client_names = list(clients_mapping.keys())
    campaign_names = list(campaigns_df["name"])
    campaign_mapping = dict(zip(campaigns_df["name"], campaigns_df["id"]))

    selected_client_names = st.sidebar.multiselect("Clients", client_names)
    selected_campaign_names = st.sidebar.multiselect("Campagnes", campaign_names)

    villes_connues = ["Abidjan", "Dakar", "Paris", "Casablanca", "Tunis",
                      "Lyon", "Yaoundé", "Alger", "Bruxelles", "Marseille"]
    ville_mapping = extraire_groupes_villes(campaign_names, villes_connues)
    selected_villes = st.sidebar.multiselect("Localisation", list(ville_mapping.keys()))
    campagnes_villes = [camp for ville in selected_villes for camp in ville_mapping[ville]]
    selected_campaign_names = list(set(selected_campaign_names + campagnes_villes))

    selected_verticals = st.sidebar.multiselect("Verticales", verticals)
    selected_countries = st.sidebar.multiselect("Code postal", countries)
    selected_ads = st.sidebar.multiselect("Ad ID (aff_id)", ads)

    return {
        "clients": [clients_mapping[name] for name in selected_client_names],
        "campaigns": [campaign_mapping[name] for name in selected_campaign_names if name in campaign_mapping],
        "verticals": selected_verticals,
        "countries": selected_countries,
        "ads": selected_ads,
        "ville_mapping": ville_mapping,
        "selected_campaign_names": selected_campaign_names
    }
