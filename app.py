import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
from fpdf import FPDF

st.set_page_config(page_title="Cel mai ieftin weekend 2025-2030", page_icon="✈️", layout="wide")

# === TOATE DESTINAȚIILE POPULARE PENTRU ROMÂNI (peste 80!) ===
DESTINATIONS = {
    "Grecia - Insule": {
        "JTR": "Santorini", "JMK": "Mykonos", "HER": "Creta Heraklion", "CHQ": "Creta Chania",
        "RHO": "Rhodos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia", "KGS": "Kos",
        "SMI": "Samos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros", "KLX": "Kalamata"
    },
    "Spania & Insule": {
        "BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "VLC": "Valencia",
        "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "TFS": "Tenerife Sud", "ACE": "Lanzarote", "LPA": "Gran Canaria"
    },
    "Italia": {
        "FCO": "Roma", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli",
        "CTA": "Catania (Sicilia)", "PMO": "Palermo", "BRI": "Bari", "BDS": "Brindisi", "OLB": "Sardinia"
    },
    "Marea Britanie": {
        "LHR": "London Heathrow", "LGW": "London Gatwick", "STN": "London Stansted", "LTN": "London Luton", "MAN": "Manchester"
    },
    "Alte destinații TOP": {
        "CDG": "Paris", "ORY": "Paris Orly", "NCE": "Nisa", "AMS": "Amsterdam", "BER": "Berlin",
        "VIE": "Viena", "PRG": "Praga", "BUD": "Budapesta", "LIS": "Lisabona", "OPO": "Porto",
        "DXB": "Dubai", "IST": "Istanbul", "DOH": "Doha", "BKK": "Bangkok"
    }
}

# Plecări din România
ORIGINS = {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"}

# Low-cost airlines
LOW_COST = {"W6", "FR", "U2", "VY", "HV", "EW", "VO", "LS", "TO"}

# Token cache
token_cache = TTLCache(maxsize=1, ttl=1700)

def get_token():
    if "token" in token_cache: return token_cache["token"]
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {"grant_type": "client_credentials", "client_id": st.secrets["AMADEUS_API_KEY"], "client_secret": st.secrets["AMADEUS_API_SECRET"]}
    try:
        r = requests.post(url, data=payload, timeout=10)
        token = r.json()["access_token"]
        token_cache["token"] = token
        return token
    except:
        st.error("Eroare conectare Amadeus")
        return None

@st.cache_data(ttl=3600)
def search_weekend_price(origin, dest, year, month):
    token = get_token()
    if not token: return None
    first_day = datetime(year, month, 1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    
    best_price = None
    for offset in [0, 7, 14, 21]:
        friday = first_friday + timedelta(days=offset)
        if friday.year != year or friday.month != month: continue
        sunday = friday + timedelta(days=2 if (friday + timedelta(days=2)).month == month else 3)
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": dest,
            "departureDate": friday.strftime("%Y-%m-%d"),
            "returnDate": sunday.strftime("%Y-%m-%d"),
            "adults": 1,
            "travelClass": "ECONOMY",
            "currencyCode": "EUR",
            "max": 5
        }
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=20)
            if r.status_code == 200 and r.json().get("data"):
                for offer in r.json()["data"]:
                    carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                    if carrier in LOW_COST:
                        price = float(offer["price"]["grandTotal"])
                        if best_price is None or price < best_price:
                            best_price = price
                            weekend_str = f"{friday.day}-{sunday.day} {friday.strftime('%b')}"
        except:
            continue
    return best_price, weekend_str if best_price else (None, None)

def create_pdf_report(df, origin_name, year):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.set_fill_color(0, 102, 204)
    pdf.cell(0, 15, f"Cel mai ieftin weekend {year}", ln=1, align="C", fill=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, f"De la: {origin_name}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(220, 230, 255)
    pdf.cell(60, 12, "Luna", 1, 0, "C", True)
    pdf.cell(70, 12, "Weekend", 1, 0, "C", True)
    pdf.cell(50, 12, "Preț (EUR)", 1, 1, "C", True)
    
    pdf.set_font("Arial", size=11)
    for _, row in df.iterrows():
        fill = row.name == 0
        pdf.set_fill_color(255, 215, 0) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(60, 10, row["Luna"], 1, 0, "C", fill)
        pdf.cell(70, 10, row["Weekend"], 1, 0, "C", fill)
        pdf.cell(50, 10, f"{row['Preț']:.0f} EUR", 1, 1, "C", fill)
    
    return pdf.output(dest="S").encode("latin-1")

# === UI ===
st.title("Cel mai ieftin weekend al anului – 2025, 2026, 2027...")
st.markdown("**Alege orice an și orice destinație – îți arăt automat cel mai ieftin weekend low-cost!**")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    origin = st.selectbox("Plecare din", list(ORIGINS.keys()), format_func=lambda x: ORIGINS[x])
with col2:
    # Toate destinațiile într-un singur selectbox mare
    all_dest = {}
    for category, cities in DESTINATIONS.items():
        for code, name in cities.items():
            all_dest[code] = f"{name} ({category.split(' - ')[0]})"
    destination = st.selectbox("Destinație", options=list(all_dest.keys()), format_func=lambda x: all_dest[x])
with col3:
    year = st.selectbox("An", [2025, 2026, 2027, 2028], index=0)

if st.button("Găsește cel mai ieftin weekend din fiecare lună!", type="primary", use_container_width=True):
    with st.spinner(f"Caut în toate weekend-urile lui {year}... (2-4 minute)"):
        results = []
        progress_bar = st.progress(0)
        
        for month in range(1, 13):
            progress_bar.progress(month / 12)
            price, weekend = search_weekend_price(origin, destination, year, month)
            if price:
                results.append({
                    "Luna": datetime(year, month, 1).strftime("%B %Y"),
                    "Weekend": weekend,
                    "Preț": price
                })
        
        progress_bar.empty()
        
        if results:
            df = pd.DataFrame(results).sort_values("Preț")
            best = df.iloc[0]
            
            st.balloons()
            st.success(f"CEL MAI IEFTIN WEEKEND DIN {year}:")
            st.markdown(f"### {best['Weekend']} → **{best['Preț']:.0f} EUR** dus-întors cu Wizz/Ryanair!")
            st.markdown(f"**Ruta:** {ORIGINS[origin]} → {all_dest[destination]}")
            
            st.dataframe(df.style.highlight_min("Preț", "gold"), use_container_width=True, height=500)
            
            # Export PDF
            pdf = create_pdf_report(df, ORIGINS[origin], year)
            st.download_button(
                label="Descarcă raport PDF complet",
                data=pdf,
                file_name=f"zboruri_ieftine_{origin}_{destination}_{year}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Nu am găsit zboruri low-cost în acest an pentru ruta aleasă.")

st.markdown("---")
st.caption("Aplicație creată special pentru românii care vor vacanțe ieftine în Santorini, Mykonos, Creta, Spania, Italia – cu Wizz Air și Ryanair")
