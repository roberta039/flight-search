import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache

st.set_page_config(page_title="Zboruri Ieftine PRO - Dus-Întors", page_icon="✈️", layout="wide")

# === LISTA COMPLETĂ AEROPORTURI (cu toate insulele grecești) ===
AIRPORTS = {
    "Europa": {
        "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu"},
        "Grecia (Continent + Insule)": {
            "ATH": "Atena", "SKG": "Salonic", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos",
            "JTR": "Santorini", "JMK": "Mykonos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia",
            "KGS": "Kos", "SMI": "Samos", "AOK": "Karpathos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros"
        },
        "Spania": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza"},
        "Italia": {"FCO": "Roma", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli", "CTA": "Catania", "BRI": "Bari"},
        "Marea Britanie": {"LHR": "London Heathrow", "LGW": "London Gatwick", "STN": "London Stansted", "MAN": "Manchester"},
        "Franța": {"CDG": "Paris CDG", "ORY": "Paris Orly", "NCE": "Nisa"},
        "Germania": {"FRA": "Frankfurt", "MUC": "München", "BER": "Berlin"},
        "Alte Europa": {"AMS": "Amsterdam", "VIE": "Viena", "ZRH": "Zürich", "LIS": "Lisabona", "PRG": "Praga", "BUD": "Budapesta"}
    },
    "Asia & Orient": {"DXB": "Dubai", "IST": "Istanbul", "DOH": "Doha", "BKK": "Bangkok"},
    "America": {"JFK": "New York JFK", "MIA": "Miami", "YYZ": "Toronto"}
}

# Cache token Amadeus
token_cache = TTLCache(maxsize=1, ttl=1700)

def get_token():
    if "token" in token_cache:
        return token_cache["token"]
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

@st.cache_data(ttl=600)
def search_roundtrip(origin, destination, depart_date, return_date, adults=1):
    token = get_token()
    if not token: return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": depart_date,
        "returnDate": return_date,
        "adults": adults,
        "travelClass": "ECONOMY",
        "nonStop": "false",
        "currencyCode": "EUR",
        "max": 25
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"Răspuns API: {r.status_code}")
            return None
    except:
        return None

# === UI ===
st.title("Zboruri Ieftine PRO - Dus-Întors + Monitorizare Prețuri")

tab1, tab2 = st.tabs(["Căutare Dus-Întors", "Rute Monitorizate"])

with tab1:
    st.header("Caută bilete dus-întors")

    col1, col2 = st.columns(2)
    with col1:
        continent1 = st.selectbox("Continent plecare", list(AIRPORTS.keys()), key="c1")
        country1 = st.selectbox("Țară plecare", list(AIRPORTS[continent1].keys()), key="co1")
        origin = st.selectbox("Aeroport plecare", list(AIRPORTS[continent1][country1].keys()),
                              format_func=lambda x: f"{x} - {AIRPORTS[continent1][country1][x]}", key="o")

    with col2:
        continent2 = st.selectbox("Continent destinație", list(AIRPORTS.keys()), key="c2")
        country2 = st.selectbox("Țară destinație", list(AIRPORTS[continent2].keys()), key="co2")
        destination = st.selectbox("Aeroport destinație", list(AIRPORTS[continent2][country2].keys()),
                                   format_func=lambda x: f"{x} - {AIRPORTS[continent2][country2][x]}", key="d")

    col3, col4 = st.columns(2)
    with col3:
        depart_date = st.date_input("Data dus", datetime.today() + timedelta(days=14))
    with col4:
        return_date = st.date_input("Data întors", datetime.today() + timedelta(days=21))

    adults = st.slider("Număr adulți", 1, 6, 1)

    if st.button("Caută cele mai ieftine bilete dus-întors", type="primary"):
        if depart_date >= return_date:
            st.error("Data întoarsă trebuie să fie după data dus!")
        else:
            with st.spinner("Caut cele mai bune oferte dus-întors..."):
                data = search_roundtrip(origin, destination, depart_date.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d"), adults)
                
                if data and data.get("data"):
                    flights = []
                    for offer in data["data"]:
                        price = float(offer["price"]["grandTotal"])
                        currency = offer["price"]["currency"]
                        
                        # Dus
                        outbound = offer["itineraries"][0]
                        dur_out = outbound["duration"].replace("PT","").replace("H","h ").replace("M","m")
                        stops_out = len(outbound["segments"]) - 1
                        
                        # Întors
                        inbound = offer["itineraries"][1]
                        dur_in = inbound["duration"].replace("PT","").replace("H","h ").replace("M","m")
                        stops_in = len(inbound["segments"]) - 1
                        
                        flights.append({
                            "Preț Total": f"{price:,.2f} {currency}",
                            "Preț/persoană": f"{price/adults:,.2f} {currency}",
                            "Durata Dus": dur_out,
                            "Durata Întors": dur_in,
                            "Escală Dus": stops_out,
                            "Escală Întors": stops_in,
                            "Companie": outbound["segments"][0]["carrierCode"]
                        })
                    
                    df = pd.DataFrame(flights).sort_values(by="Preț Total", key=lambda x: x.str.replace("[^0-9.]","", regex=True).astype(float))
                    
                    st.success(f"Am găsit {len(df)} oferte dus-întors!")
                    st.dataframe(df.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True, height=600)
                    
                    # Descărcare
                    csv = df.to_csv(index=False).encode()
                    st.download_button("Descarcă CSV", csv, f"zboruri_{origin}_{destination}_{depart_date.strftime('%Y%m%d')}.csv", "text/csv")
                    
                    # Monitorizare
                    target = st.number_input("Notifică-mă dacă scade sub (€)", value=int(price-10))
                    if st.button("Monitorizează această rută dus-întors"):
                        st.session_state.setdefault("watchlist", []).append({
                            "origin": origin, "dest": destination,
                            "depart": depart_date.strftime("%Y-%m-%d"),
                            "return": return_date.strftime("%Y-%m-%d"),
                            "adults": adults, "target": target, "last_price": price
                        })
                        st.success("Rută adăugată la monitorizare!")
                        st.balloons()
                else:
                    st.warning("Nu am găsit zboruri dus-întors pentru aceste date.")

# Tab Monitorizare
with tab2:
    st.header("Rute monitorizate (dus-întors)")
    if "watchlist" in st.session_state and st.session_state.watchlist:
        for i, r in enumerate(st.session_state.watchlist):
            st.write(f"**{r['origin']} → {r['dest']} → {r['origin']}** | {r['depart']} ⇄ {r['return']} | Țintă: {r['target']}€")
            if st.button("Verifică acum", key=f"check{i}"):
                data = search_roundtrip(r["origin"], r["dest"], r["depart"], r["return"], r["adults"])
                if data and data.get("data"):
                    new_price = float(data["data"][0]["price"]["grandTotal"])
                    if new_price < r["last_price"]:
                        st.balloons()
                        st.success(f"PREȚ SCĂZUT! De la {r['last_price']:.0f}€ → {new_price:.0f}€")
                    else:
                        st.info(f"Preț curent: {new_price:.0f}€")
                    r["last_price"] = new_price
    else:
        st.info("Nicio rută monitorizată încă.")

# Auto-refresh monitorizare
if "watchlist" in st.session_state and st.session_state.watchlist:
    time.sleep(180)
    st.rerun()
