from sqlalchemy.sql import text

def build_main_query(where_clause: str):
    return text(f"""
    SELECT
        s.id AS stat_id,
        cl.name AS client_name,
        s.price_eur,
        s.number_of_sales,
        r.sold_to_exclusive,
        r.id AS registration_id,
        s.currency,
        v.name AS vertical_name,
        c.name AS campaign_name,
        c.monthly_cap,
        c.daily_cap,
        l.id AS lead_id,
        l.email AS lead_email,
        r.created_at AS registration_created_at,
        s.lead_created_at,
        r.firstname,
        r.lastname,
        r.zipcode,
        r.city,
        s.aff_id,
        r.others::json->>'source' AS affiliate_name,
        r.others::json->>'aff_sub' AS aff_sub,
        r.others::json->>'publisher_id' AS publisher_id,
        lcls.status AS last_client_status
    FROM stat s
    JOIN registration r ON r.id = s.registration
    LEFT JOIN lead l ON l.registration_id = r.id
    LEFT JOIN campaign c ON c.id = l.campaign_id
    LEFT JOIN vertical v ON c.vertical_id = v.id
    LEFT JOIN client cl ON cl.id = s.client
    LEFT JOIN (
        SELECT DISTINCT ON (lead_id) lead_id, status
        FROM lead_client_lead_status
        ORDER BY lead_id, created_at DESC
    ) lcls ON lcls.lead_id = l.id
    WHERE {where_clause}
    """)