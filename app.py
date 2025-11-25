import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
from fpdf import FPDF
import base64

st.set_page_config(page_title="Zboruri Ieftine 2025 - Cel mai ieftin weekend", page_icon="✈️", layout="wide")

# === COMPANII LOW-COST ===
LOW_COST_AIRLINES = {"W6", "FR", "U2", "VY", "HV", "EW", "VO", "LS", "TO", "RK"}

# === AEROPORTURI ===
AIRPORTS = {
    "Europa": {
        "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași"},
        "Grecia (Insule)": {"JTR": "Santorini", "JMK": "Mykonos", "HER": "Creta Heraklion", "RHO": "Rhodos", "CFU": "Corfu", "ZTH": "Zakynthos"},
        "Spania": {"BCN": "Barcelona", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma", "IBZ": "Ibiza"},
        "Italia": {"FCO": "Roma", "MXP": "Milano", "NAP": "Napoli", "CTA": "Catania"},
        "Alte": {"LON": "London", "PAR": "Paris", "BER": "Berlin", "VIE": "Viena", "AMS": "Amsterdam"}
    }
}

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

@st.cache_data(ttl=1800)
def search_weekend(origin, dest, friday_date):
    token = get_token()
    if not token: return None
    sunday = friday_date + timedelta(days=2)
    if sunday.month != friday_date.month:
        sunday = friday_date + timedelta(days=3)  # sâmbătă-luni
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin, "destinationLocationCode": dest,
        "departureDate": friday_date.strftime("%Y-%m-%d"),
        "returnDate": sunday.strftime("%Y-%m-%d"),
        "adults": 1, "travelClass": "ECONOMY", "currencyCode": "EUR", "max": 10
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=25)
        if r.status_code == 200 and r.json().get("data"):
            price = float(r.json()["data"][0]["price"]["grandTotal"])
            carrier = r.json()["data"][0]["itineraries"][0]["segments"][0]["carrierCode"]
            if carrier in LOW_COST_AIRLINES:
                return price
        return None
    except:
        return None

def create_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.set_fill_color(0, 102, 204)
    pdf.cell(0, 15, "Cel mai ieftin weekend al anului 2025", ln=1, align="C", fill=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Ruta: {df.iloc[0]['Origine']} - {df.iloc[0]['Destinație']}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(60, 12, "Luna", 1, 0, "C", True)
    pdf.cell(60, 12, "Weekend", 1, 0, "C", True)
    pdf.cell(60, 12, "Preț (EUR)", 1, 1, "C", True)
    
    pdf.set_font("Arial", size=11)
    for _, row in df.iterrows():
        fill = (row.name == 0)
        pdf.cell(60, 10, row["Luna"], 1, 0, "C", fill)
        pdf.cell(60, 10, row["Weekend"], 1, 0, "C", fill)
        pdf.cell(60, 10, f"{row['Preț']:.0f} EUR", 1, 1, "C", fill)
    
    return pdf.output(dest="S").encode("latin-1")

# === UI ===
st.title("Cel mai ieftin weekend al anului 2025")
st.markdown("**Găsește automat cel mai ieftin weekend din fiecare lună – doar low-cost (Wizz, Ryanair, EasyJet)**")

col1, col2 = st.columns(2)
with col1:
    origin = st.selectbox("Plecare din România", ["OTP", "CLJ", "TSR", "IAS"],
                          format_func=lambda x: AIRPORTS["Europa"]["România"][x])
with col2:
    destination = st.selectbox("Destinație preferată", list(AIRPORTS["Europa"]["Grecia (Insule)"].keys()) + 
                               list(AIRPORTS["Europa"]["Spania"].keys()),
                               format_func=lambda x: AIRPORTS["Europa"]["Grecia (Insule)"].get(x, AIRPORTS["Europa"]["Spania"].get(x, x)))

if st.button("Găsește cel mai ieftin weekend din fiecare lună!", type="primary", use_container_width=True):
    with st.spinner("Caut în toate weekend-urile anului 2025... (poate dura 2-4 minute)"):
        results = []
        today = datetime(2025, 1, 1)
        progress = st.progress(0)
        
        for month in range(1, 13):
            progress.progress(month / 12)
            current = datetime(2025, month, 1)
            # Găsim prima vineri a lunii
            first_friday = current + timedelta(days=(4 - current.weekday()) % 7)
            price = None
            weekend_str = ""
            
            for offset in [0, 7, 14, 21]:
                friday = first_friday + timedelta(days=offset)
                if friday.year != 2025 or friday.month != month: 
                    continue
                p = search_weekend(origin, destination, friday)
                if p and (price is None or p < price):
                    price = p
                    sunday = friday + timedelta(days=2 if (friday + timedelta(days=2)).month == month else 3)
                    weekend_str = f"{friday.day} - {sunday.day} {friday.strftime('%B')}"
            
            if price:
                results.append({
                    "Luna": current.strftime("%B %Y"),
                    "Weekend": weekend_str,
                    "Preț": price,
                    "Origine": AIRPORTS["Europa"]["România"][origin],
                    "Destinație": AIRPORTS["Europa"]["Grecia (Insule)"].get(destination, AIRPORTS["Europa"]["Spania"].get(destination, destination))
                })
        
        if results:
            df = pd.DataFrame(results).sort_values("Preț")
            best = df.iloc[0]
            
            st.balloons()
            st.success(f"CEL MAI IEFTIN WEEKEND DIN 2025:")
            st.markdown(f"### {best['Weekend']} → doar **{best['Preț']:.0f} EUR** cu low-cost!")
            st.markdown(f"**Ruta:** {best['Origine']} → {best['Destinație']}")
            
            st.dataframe(df.style.highlight_min("Preț", "gold"), use_container_width=True, height=500)
            
            # Export PDF
            pdf_data = create_pdf(df)
            st.download_button(
                "Descarcă raport PDF - Cel mai ieftin weekend 2025",
                pdf_data,
                f"zboruri_ieftine_{origin}_{destination}_2025.pdf",
                "application/pdf"
            )
        else:
            st.error("Nu am găsit zboruri low-cost în 2025 pentru această rută.")

st.markdown("---")
st.caption("Aplicație creată pentru românii care vor vacanțe ieftine în 2025 – Santorini, Mykonos, Creta, Spania la prețuri de Wizz/Ryanair")
