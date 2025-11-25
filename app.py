import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache

st.set_page_config(page_title="Zboruri Ieftine PRO - Dus-Întors", page_icon="✈️", layout="wide")

# === LISTA AEROPORTURI COMPLETĂ (cu toate insulele grecești) ===
AIRPORTS = {
    "Europa": {
        "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"},
        "Grecia (Continent + Insule)": {
            "ATH": "Atena", "SKG": "Salonic", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos",
            "JTR": "Santorini", "JMK": "Mykonos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia",
            "KGS": "Kos", "SMI": "Samos", "AOK": "Karpathos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros", "KLX": "Kalamata"
        },
        "Spania & Insule": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "TFS": "Tenerife Sud"},
        "Italia": {"FCO": "Roma Fiumicino", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli", "CTA": "Catania", "BRI": "Bari"},
        "Marea Britanie": {"LHR": "London Heathrow", "LGW": "London Gatwick", "STN": "London Stansted", "MAN": "Manchester"},
        "Franța": {"CDG": "Paris CDG", "ORY": "Paris Orly", "NCE": "Nisa"},
        "Germania": {"FRA": "Frankfurt", "MUC": "München", "BER": "Berlin"},
        "Alte Europa": {"AMS": "Amsterdam", "VIE": "Viena", "ZRH": "Zürich", "LIS": "Lisabona", "PRG": "Praga", "BUD": "Budapesta", "WAW": "Varșovia"}
    },
    "Asia": {"DXB": "Dubai", "IST": "Istanbul", "DOH": "Doha", "BKK": "Bangkok"},
    "America": {"JFK": "New York JFK", "MIA": "Miami", "YYZ": "Toronto", "LAX": "Los Angeles"}
}

# Cache token
token_cache = TTLCache(maxsize=1, ttl=1700)

def get_token():
    if "token" in token_cache:
        return token_cache["token"]
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": st.secrets["AMADEUS_API_KEY"],
        "client_secret": st.secrets["AMADEUS_API_SECRET"]
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        token = r.json()["access_token"]
        token_cache["token"] = token
        return token
    except:
        st.error("Eroare conectare Amadeus")
        return None

@st.cache_data(ttl=600)
def search_roundtrip(origin, dest, dep_date, ret_date, adults=1, non_stop=False):
    token = get_token()
    if not token: return None

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": dest,
        "departureDate": dep_date,
        "returnDate": ret_date,
        "adults": adults,
        "travelClass": "ECONOMY",
        "nonStop": "true" if non_stop else "false",
        "currencyCode": "EUR",
        "max": 30
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"Eroare API: {r.status_code}")
            return None
    except Exception as e:
        st.error("Eroare conexiune")
        return None

# === UI ===
st.title("Zboruri Ieftine PRO – Dus-Întors + Monitorizare")
st.markdown("Cea mai bună aplicație de zboruri din România")

tab1, tab2 = st.tabs(["Căutare Dus-Întors", "Rute Monitorizate"])

with tab1:
    st.header("Caută bilete dus-întors")

    col1, col2 = st.columns(2)
    with col1:
        continent1 = st.selectbox("Continent plecare", list(AIRPORTS.keys()))
        country1 = st.selectbox("Țară plecare", list(AIRPORTS[continent1].keys()))
        origin = st.selectbox("De la", list(AIRPORTS[continent1][country1].keys()),
                              format_func=lambda x: f"{x} – {AIRPORTS[continent1][country1][x]}")

    with col2:
        continent2 = st.selectbox("Continent destinație", list(AIRPORTS.keys()))
        country2 = st.selectbox("Țară destinație", list(AIRPORTS[continent2].keys()))
        destination = st.selectbox("Către", list(AIRPORTS[continent2][country2].keys()),
                                   format_func=lambda x: f"{x} – {AIRPORTS[continent2][country2][x]}")

    col3, col4 = st.columns(2)
    with col3:
        depart_date = st.date_input("Data plecare (dus)", datetime.today() + timedelta(days=14))
    with col4:
        return_date = st.date_input("Data întoarcere", datetime.today() + timedelta(days=21))

    col5, col6 = st.columns(2)
    with col5:
        adults = st.number_input("Număr adulți", min_value=1, max_value=9, value=1, step=1)
    with col6:
        non_stop = st.checkbox("Doar zboruri directe (dus și întors)", value=False)

    if st.button("Caută cele mai ieftine bilete dus-întors", type="primary", use_container_width=True):
        if depart_date >= return_date:
            st.error("Data întoarsă trebuie să fie după data plecării!")
        else:
            with st.spinner("Caut cele mai bune oferte dus-întors... (10-20 sec)"):
                data = search_roundtrip(origin, destination,
                                        depart_date.strftime("%Y-%m-%d"),
                                        return_date.strftime("%Y-%m-%d"),
                                        adults, non_stop)

                if data and data.get("data"):
                    flights = []
                    for offer in data["data"]:
                        try:
                            price = float(offer["price"]["grandTotal"])
                            currency = offer["price"]["currency"]

                            # Dus
                            out = offer["itineraries"][0]
                            dur_out = out["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            stops_out = len(out["segments"]) - 1

                            # Întors
                            ret = offer["itineraries"][1]
                            dur_ret = ret["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            stops_ret = len(ret["segments"]) - 1

                            airline = out["segments"][0]["carrierCode"]

                            flights.append({
                                "Preț Total": f"{price:,.2f} {currency}",
                                "Preț/adult": f"{price/adults:,.2f} {currency}",
                                "Durata Dus": dur_out,
                                "Durata Întors": dur_ret,
                                "Escală Dus": stops_out if stops_out > 0 else "Direct",
                                "Escală Întors": stops_ret if stops_ret > 0 else "Direct",
                                "Companie": airline
                            })
                        except:
                            continue

                    if flights:
                        df = pd.DataFrame(flights)
                        df = df.sort_values(by="Preț Total", key=lambda x: x.str.replace("[^0-9.]", "", regex=True).astype(float))

                        st.success(f"Am găsit {len(df)} oferte dus-întors!")
                        st.dataframe(df.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True, height=600)

                        # Descărcare CSV
                        csv = df.to_csv(index=False).encode()
                        st.download_button("Descarcă rezultatele CSV", csv,
                                           f"zboruri_{origin}_{destination}_{depart_date.strftime('%Y%m%d')}.csv", "text/csv")

                        # Monitorizare
                        current_price = float(df.iloc[0]["Preț Total"].split()[0].replace(",", ""))
                        target = st.number_input("Notifică-mă dacă scade sub (€)", value=int(current_price - 10), step=5)
                        if st.button("Adaugă la monitorizare"):
                            st.session_state.setdefault("watchlist", []).append({
                                "origin": origin, "dest": destination,
                                "depart": depart_date.strftime("%Y-%m-%d"),
                                "return": return_date.strftime("%Y-%m-%d"),
                                "adults": adults, "non_stop": non_stop,
                                "target": target, "last_price": current_price
                            })
                            st.success("Rută adăugată la monitorizare!")
                            st.balloons()
                    else:
                        st.warning("Nu am găsit zboruri valide.")
                else:
                    st.error("Nu am găsit zboruri pentru această rută și date.")

# === Tab Monitorizare ===
with tab2:
    st.header("Rute monitorizate")
    if "watchlist" in st.session_state and st.session_state.watchlist:
        for i, r in enumerate(st.session_state.watchlist):
            with st.expander(f"{r['origin']} → {r['dest']} → {r['origin']} | {r['depart']} ⇄ {r['return']} | Țintă: {r['target']}€"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.write(f"Adulți: {r['adults']} | {'Directe' if r['non_stop'] else 'Cu escală'}")
                with col2:
                    if st.button("Verifică prețul acum", key=f"chk{i}"):
                        data = search_roundtrip(r["origin"], r["dest"], r["depart"], r["return"], r["adults"], r["non_stop"])
                        if data and data.get("data"):
                            new_price = float(data["data"][0]["price"]["grandTotal"])
                            if new_price < r["last_price"]:
                                st.balloons()
                                st.success(f"PREȚ SCĂZUT! {r['last_price']:.0f}€ → {new_price:.0f}€")
                            else:
                                st.info(f"Preț curent: {new_price:.0f}€")
                            r["last_price"] = new_price
                        st.rerun()
                if st.button("Șterge ruta", key=f"del{i}"):
                    st.session_state.watchlist.pop(i)
                    st.rerun()
    else:
        st.info("Nicio rută monitorizată încă.")

# Auto-refresh monitorizare
if "watchlist" in st.session_state and len(st.session_state.watchlist) > 0:
    time.sleep(180)
    st.rerun()
