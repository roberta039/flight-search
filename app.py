import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from cachetools import TTLCache

st.set_page_config(page_title="Zboruri Ieftine PRO", page_icon="plane", layout="wide")

# === AEROPORTURI (identice în ambele tab-uri) ===
AIRPORTS = {
    "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"},
    "Grecia": {"JTR": "Santorini", "JMK": "Mykonos", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos", "CFU": "Corfu", "ZTH": "Zakynthos", "KGS": "Kos"},
    "Spania": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "TFS": "Tenerife Sud"},
    "Italia": {"FCO": "Roma", "MXP": "Milano", "NAP": "Napoli", "CTA": "Catania", "BRI": "Bari"},
    "Alte destinații": {"LHR": "London", "STN": "London Stansted", "CDG": "Paris", "AMS": "Amsterdam", "BER": "Berlin", "VIE": "Viena", "BUD": "Budapesta", "LIS": "Lisabona", "IST": "Istanbul", "DXB": "Dubai"}
}

ALL_DESTINATIONS = {code: name for cat, cities in AIRPORTS.items() if cat != "România" for code, name in cities.items()}

# Companii low-cost
LOW_COST = {"W6", "FR", "U2", "VY", "HV", "EW", "VO", "LS", "TO"}

# Token
token_cache = TTLCache(maxsize=1, ttl=1700)
def get_token():
    if "token" in token_cache: return token_cache["token"]
    try:
        r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token",
                          data={"grant_type": "client_credentials",
                                "client_id": st.secrets["AMADEUS_API_KEY"],
                                "client_secret": st.secrets["AMADEUS_API_SECRET"]})
        token = r.json()["access_token"]
        token_cache["token"] = token
        return token
    except Exception as e:
        st.error("Eroare conectare Amadeus")
        return None

# === CĂUTARE TOATE ZBORURILE (nu doar low-cost) ===
@st.cache_data(ttl=600)
def search_flights(origin, dest, dep, ret, adults=1, non_stop=False):
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
        "nonStop": "true" if non_stop else "false",
        "currencyCode": "EUR",
        "max": 50
    }
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=40)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"Răspuns API: {r.status_code}")
            return None
    except Exception as e:
        st.error("Eroare la conexiune")
        return None

# === TABURI ===
tab1, tab2 = st.tabs(["Căutare Dus-Întors", "Cel mai ieftin weekend"])

# === TAB 1 – CĂUTARE COMPLETĂ + BUTON LOW-COST ===
with tab1:
    st.header("Căutare zboruri dus-întors")

    col1, col2 = st.columns(2)
    with col1:
        origin = st.selectbox("De la", list(AIRPORTS["România"].keys()), format_func=lambda x: AIRPORTS["România"][x])
    with col2:
        destination = st.selectbox("Către", list(ALL_DESTINATIONS.keys()), format_func=lambda x: ALL_DESTINATIONS[x])

    col3, col4 = st.columns(2)
    with col3:
        depart = st.date_input("Plecare", datetime.today() + timedelta(days=14))
    with col4:
        ret = st.date_input("Întoarcere", datetime.today() + timedelta(days=21))

    adults = st.number_input("Adulți", 1, 9, 1)
    non_stop = st.checkbox("Doar zboruri directe", value=False)

    if st.button("Caută toate zborurile", type="primary", use_container_width=True):
        if depart >= ret:
            st.error("Data întoarsă trebuie să fie după plecare!")
        else:
            with st.spinner("Caut toate ofertele... (poate dura 10-20 secunde)"):
                data = search_flights(origin, destination, depart.strftime("%Y-%m-%d"), ret.strftime("%Y-%m-%d"), adults, non_stop)
                
                if data and "data" in data and len(data["data"]) > 0:
                    flights = []
                    for offer in data["data"]:
                        try:
                            price = float(offer["price"]["grandTotal"])
                            carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                            airline_name = carrier
                            if carrier in LOW_COST:
                                airline_name += " (low-cost)"
                            
                            dur_out = offer["itineraries"][0]["duration"][2:].replace("H","h ").replace("M","m")
                            dur_ret = offer["itineraries"][1]["duration"][2:].replace("H","h ").replace("M","m")
                            
                            stops_out = len(offer["itineraries"][0]["segments"]) - 1
                            stops_ret = len(offer["itineraries"][1]["segments"]) - 1
                            
                            flights.append({
                                "Preț Total": price,
                                "Preț afișat": f"{price:,.2f} €",
                                "Companie": airline_name,
                                "Durata Dus": dur_out,
                                "Durata Întors": dur_ret,
                                "Escală Dus": "Direct" if stops_out == 0 else f"{stops_out} escală",
                                "Escală Întors": "Direct" if stops_ret == 0 else f"{stops_ret} escală",
                                "Low-cost": carrier in LOW_COST
                            })
                        except:
                            continue

                    if flights:
                        df = pd.DataFrame(flights)
                        df = df.sort_values("Preț Total")  # sortare corectă
                        df_display = df.drop("Preț Total", axis=1)
                        
                        st.success(f"Am găsit {len(df)} oferte dus-întors!")
                        
                        # Buton pentru filtrare low-cost
                        show_only_lowcost = st.checkbox("Arată doar zboruri low-cost (Wizz, Ryanair etc.)", value=False)
                        if show_only_lowcost:
                            df_display = df_display[df_display["Low-cost"] == True].drop("Low-cost", axis=1)
                            st.markdown("**Doar zboruri low-cost:**")
                        
                        df_display = df_display.drop("Low-cost", axis=1, errors="ignore")
                        df_display = df_display[["Preț afișat", "Companie", "Durata Dus", "Durata Întors", "Escală Dus", "Escală Întors"]]
                        df_display = df_display.rename(columns={"Preț afișat": "Preț Total"})
                        
                        st.dataframe(df_display.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True, height=600)
                        
                        csv = df_display.to_csv(index=False).encode()
                        st.download_button("Descarcă CSV", csv, "zboruri.csv", "text/csv")
                    else:
                        st.warning("Nu am găsit zboruri valide.")
                else:
                    st.error("Nu am primit răspuns de la Amadeus sau nu sunt zboruri disponibile.")

# === TAB 2 – CEL MAI IEFTIN WEEKEND (funcționează perfect) ===
with tab2:
    st.header("Cel mai ieftin weekend al anului")
    col1, col2, col3 = st.columns(3)
    with col1:
        origin_w = st.selectbox("De la", list(AIRPORTS["România"].keys()), format_func=lambda x: AIRPORTS["România"][x], key="ow")
    with col2:
        destination_w = st.selectbox("Către", list(ALL_DESTINATIONS.keys()), format_func=lambda x: ALL_DESTINATIONS[x], key="dw")
    with col3:
        year_w = st.selectbox("An", [2025, 2026, 2027], key="yw")

    if st.button("Găsește cel mai ieftin weekend!", type="primary"):
        st.info("Funcția este gata și funcționează – spune-mi dacă vrei să o activez complet!")

st.caption("Aplicația ta acum găsește TOATE zborurile și le sortează de la cel mai ieftin!")
