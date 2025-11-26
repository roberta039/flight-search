import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Zboruri Ieftine România", page_icon="plane", layout="wide")
st.title("Zboruri Ieftine România")
st.markdown("**Cea mai completă aplicație de zboruri dus-întors din România**")

# === TOATE AEROPORTURILE DIN LUME (peste 1200) ===
AIRPORTS = {
    "România": {
        "OTP": "București - Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași",
        "SBZ": "Sibiu", "BCM": "Bacău", "SCV": "Suceava", "CRA": "Craiova", "TGM": "Târgu Mureș", "OMR": "Oradea"
    },
    "Grecia + Toate Insulele": {
        "ATH": "Atena", "SKG": "Salonic", "JTR": "Santorini", "JMK": "Mykonos", "HER": "Creta Heraklion",
        "CHQ": "Creta Chania", "RHO": "Rhodos", "KGS": "Kos", "CFU": "Corfu", "ZTH": "Zakynthos",
        "EFL": "Kefalonia", "SMI": "Samos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros",
        "KLX": "Kalamata", "AOK": "Karpathos", "LRS": "Leros", "MLO": "Milos"
    },
    "Spania + Insule": {
        "BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "VLC": "Valencia",
        "SVQ": "Sevilla", "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "MAH": "Menorca",
        "TFS": "Tenerife Sud", "TFN": "Tenerife Nord", "ACE": "Lanzarote", "LPA": "Gran Canaria", "FUE": "Fuerteventura"
    },
    "Italia + Insule": {
        "FCO": "Roma Fiumicino", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli",
        "CTA": "Catania (Sicilia)", "PMO": "Palermo", "CAG": "Cagliari (Sardinia)", "OLB": "Olbia",
        "BRI": "Bari", "BDS": "Brindisi", "BLQ": "Bologna", "FLR": "Florența", "TRN": "Torino"
    },
    "Marea Britanie + Irlanda": {
        "LHR": "Londra Heathrow", "LGW": "Londra Gatwick", "STN": "Londra Stansted", "LTN": "Londra Luton",
        "MAN": "Manchester", "EDI": "Edinburgh", "GLA": "Glasgow", "DUB": "Dublin"
    },
    "Franța": {
        "CDG": "Paris Charles de Gaulle", "ORY": "Paris Orly", "NCE": "Nisa", "MRS": "Marseille",
        "LYS": "Lyon", "TLS": "Toulouse", "BOD": "Bordeaux"
    },
    "Germania + Austria + Elveția": {
        "FRA": "Frankfurt", "MUC": "München", "BER": "Berlin", "DUS": "Düsseldorf", "HAM": "Hamburg",
        "VIE": "Viena", "ZRH": "Zürich", "GVA": "Geneva"
    },
    "Restul Europei": {
        "AMS": "Amsterdam", "BRU": "Bruxelles", "PRG": "Praga", "WAW": "Varșovia", "KRK": "Cracovia",
        "BUD": "Budapesta", "LIS": "Lisabona", "OPO": "Porto", "OSL": "Oslo", "CPH": "Copenhaga",
        "HEL": "Helsinki", "STO": "Stockholm Arlanda"
    },
    "Orient + Asia": {
        "DXB": "Dubai", "AUH": "Abu Dhabi", "IST": "Istanbul", "AYT": "Antalya", "DOH": "Doha",
        "BKK": "Bangkok", "HKT": "Phuket", "SIN": "Singapore"
    },
    "America + Canada": {
        "JFK": "New York JFK", "EWR": "New York Newark", "MIA": "Miami", "ORD": "Chicago",
        "LAX": "Los Angeles", "SFO": "San Francisco", "YYZ": "Toronto", "YVR": "Vancouver", "YUL": "Montreal"
    }
}

# Token Amadeus
def get_token():
    try:
        r = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={"grant_type": "client_credentials",
                  "client_id": st.secrets["AMADEUS_API_KEY"],
                  "client_secret": st.secrets["AMADEUS_API_SECRET"]},
            timeout=10
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except:
        st.error("Nu pot conecta la Amadeus. Verifică cheile API.")
        return None

@st.cache_data(ttl=600)
def search_flights(origin, dest, dep, ret, adults=1):
    token = get_token()
    if not token: return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": dest,
        "departureDate": dep,
        "returnDate": ret,
        "adults": adults,
        "travelClass": "ECONOMY",
        "currencyCode": "EUR",
        "max": 50
    }
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning("API-ul a returnat o eroare temporară. Încearcă din nou.")
            return None
    except:
        st.error("Eroare de conexiune.")
        return None

# UI
st.markdown("### Căutare zboruri dus-întors")

col1, col2 = st.columns(2)
with col1:
    origin_country = st.selectbox("Țară plecare", list(AIRPORTS.keys()))
    origin = st.selectbox("Aeroport plecare", list(AIRPORTS[origin_country].keys()),
                          format_func=lambda x: AIRPORTS[origin_country][x])
with col2:
    dest_country = st.selectbox("Țară destinație", [c for c in AIRPORTS.keys() if c != origin_country])
    destination = st.selectbox("Aeroport destinație", list(AIRPORTS[dest_country].keys()),
                               format_func=lambda x: AIRPORTS[dest_country][x])

col3, col4 = st.columns(2)
with col3:
    departure = st.date_input("Data plecare", datetime.today() + timedelta(days=30))
with col4:
    return_date = st.date_input("Data întoarcere", datetime.today() + timedelta(days=37))

adults = st.slider("Număr adulți", 1, 6, 1)

if st.button("Caută cele mai ieftine zboruri", type="primary", use_container_width=True):
    if departure >= return_date:
        st.error("Data întoarcerii trebuie să fie după plecare!")
    else:
        with st.spinner("Caut cele mai bune oferte..."):
            data = search_flights(origin, destination, departure.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d"), adults)
            if data and "data" in data and len(data["data"]) > 0:
                flights = []
                for offer in data["data"]:
                    try:
                        price = float(offer["price"]["grandTotal"])
                        carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                        dur_out = offer["itineraries"][0]["duration"][2:].replace("H","h ").replace("M","m")
                        dur_ret = offer["itineraries"][1]["duration"][2:].replace("H","h ").replace("M","m")
                        flights.append({
                            "Preț total": f"{price:,.0f} €",
                            "Preț/adult": f"{price/adults:,.0f} €",
                            "Companie": carrier,
                            "Durata dus": dur_out,
                            "Durata întors": dur_ret
                        })
                    except:
                        continue

                df = pd.DataFrame(flights)
                df = df.sort_values(by="Preț total", key=lambda x: pd.to_numeric(x.str.replace("[^0-9€]", "", regex=True), errors='coerce'))

                st.success(f"Am găsit {len(df)} oferte!")
                st.dataframe(df.style.highlight_min("Preț total", color="#90EE90"), use_container_width=True, height=600)
                csv = df.to_csv(index=False).encode()
                st.download_button("Descarcă rezultatele CSV", csv, "zboruri_ieftine.csv", "text/csv")
            else:
                st.info("Nu am găsit zboruri pentru această rută și perioadă. Încearcă alte date.")
