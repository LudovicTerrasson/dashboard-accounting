import requests
import pandas as pd

def get_facebook_campaign_insights(ad_account_id: str, access_token: str, date_preset: str = "last_7d") -> pd.DataFrame:
    """
    Récupère les insights des campagnes Facebook via l'API Marketing.
    
    Args:
        ad_account_id (str): ID du compte publicitaire (ex: "act_1234567890")
        access_token (str): Jeton d'accès API Facebook.
        date_preset (str): Plage temporelle à récupérer (ex: "yesterday", "last_7d", "this_month", etc.)
        
    Returns:
        pd.DataFrame: Données des campagnes sous forme de tableau
    """
    url = f"https://graph.facebook.com/v18.0/{ad_account_id}/insights"
    params = {
        "access_token": access_token,
        "fields": "campaign_name,spend,impressions,clicks,ctr,cpm",
        "date_preset": date_preset,
        "limit": 1000
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("data", [])
    
    return pd.DataFrame(data)
