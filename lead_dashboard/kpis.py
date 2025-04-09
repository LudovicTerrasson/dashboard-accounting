import pandas as pd
from utils import formater_duree

def compute_kpis(df):
    df["lead_heat_minutes"] = pd.to_datetime(df["lead_created_at"]) - pd.to_datetime(df["registration_created_at"])
    mean_heat_timedelta = df["lead_heat_minutes"].mean()
    
    return {
        "total_leads": len(df),
        "total_revenue": df["price_eur"].sum(),
        "avg_price": df["price_eur"].mean(),
        "unique_sources": df["affiliate_name"].nunique(),
        "avg_heat": mean_heat_timedelta
    }
