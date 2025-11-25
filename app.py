import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache

st.set_page_config(page_title="Zboruri Ieftine", page_icon="✈️", layout="wide")

# === COMPANII LOW-COST (cele mai importante) ===
LOW_COST_AIRLINES = {
    "W6": "Wizz Air",
    "FR": "Ryanair",
    "U2": "EasyJet",
    "VY": "Vueling",
    "W9": "Wizz Air UK",
    "HV": "Transavia",
    "EW": "Eurowings",
    "VO": "Volotea",
    "BZ": "Blue Air (dacă mai zboară)",
    "RK": "Ryanair UK",
    "LS": "Jet2",
    "TO": "Transavia France"
}

# === LISTA AEROPORTURI COMPLETĂ ===
AIRPORTS = {
    "Europa": {
        "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"},
        "Grecia (Toate insulele)": {
            "ATH": "Atena", "SKG": "Salonic", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos",
            "JTR": "Santorini", "JMK": "Mykonos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia",
            "KGS": "Kos", "SMI": "Samos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros", "KLX": "Kalamata"
        },
        "Spania & Insule": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "TFS": "Tenerife Sud"},
        "Italia": {"FCO": "Roma", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli", "CTA": "Catania", "BRI": "Bari"},
        "Marea Britanie": {"LHR": "London Heathrow", "LGW": "London Gatwick", "STN": "London Stansted", "MAN": "Manchester"},
        "Franța": {"CDG": "Paris CDG", "ORY": "Paris Orly", "NCE": "Nisa"},
        "Alte Europa": {"AMS": "Amsterdam", "VIE": "Viena", "ZRH": "Zürich", "LIS": "Lisabona", "PRG": "Praga", "BUD": "Budapesta"}
    },
    "Asia": {"DXB": "Dubai", "IST": "Istanbul"},
    "America": {"JFK": "New York JFK", "MIA": "Miami"}
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
def search_roundtrip(origin, dest, dep_date, ret_date, adults=1, non_stop=False, only_lowcost=False):
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
        "max": 40
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"Eroare API: {r.status_code}")
            return None
    except:
        return None

# === UI ===
st.title("Zboruri Ieftine")
st.markdown("Găsește cele mai ieftine bilete dus-întors")

tab1, tab2 = st.tabs(["Căutare Low-Cost", "Rute Monitorizate"])

with tab1:
    st.header("Caută bilete dus-întors low-cost")

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
        depart_date = st.date_input("Data plecare", datetime.today() + timedelta(days=14))
    with col4:
        return_date = st.date_input("Data întoarcere", datetime.today() + timedelta(days=21))

    col5, col6 = st.columns(2)
    with col5:
        adults = st.number_input("Număr adulți", min_value=1, max_value=9, value=1)
    with col6:
        only_lowcost = st.checkbox("Doar companii low-cost (Wizz Air, Ryanair, EasyJet etc.)", value=True)

    non_stop = st.checkbox("Doar zboruri directe (dus și întors)", value=False)

    if st.button("Caută cele mai ieftine bilete low-cost", type="primary", use_container_width=True):
        if depart_date >= return_date:
            st.error("Data întoarsă trebuie să fie după data plecării!")
        else:
            with st.spinner("Caut cele mai ieftine oferte low-cost..."):
                data = search_roundtrip(origin, destination,
                                        depart_date.strftime("%Y-%m-%d"),
                                        return_date.strftime("%Y-%m-%d"),
                                        adults, non_stop, only_lowcost)

                if data and data.get("data"):
                    flights = []
                    for offer in data["data"]:
                        try:
                            price = float(offer["price"]["grandTotal"])
                            currency = offer["price"]["currency"]

                            # Verificăm dacă e low-cost
                            carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                            is_lowcost = carrier in LOW_COST_AIRLINES

                            if only_lowcost and not is_lowcost:
                                continue  # sărim peste companiile scumpe

                            out = offer["itineraries"][0]
                            dur_out = out["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            stops_out = len(out["segments"]) - 1

                            ret = offer["itineraries"][1]
                            dur_ret = ret["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            stops_ret = len(ret["segments"]) - 1

                            airline_name = LOW_COST_AIRLINES.get(carrier, carrier)

                            flights.append({
                                "Preț Total": f"{price:,.2f} {currency}",
                                "Preț/adult": f"{price/adults:,.2f} {currency}",
                                "Companie": f"{airline_name}",
                                "Durata Dus": dur_out,
                                "Durata Întors": dur_ret,
                                "Escală Dus": "Direct" if stops_out == 0 else f"{stops_out} escală",
                                "Escală Întors": "Direct" if stops_ret == 0 else f"{stops_ret} escală"
                            })
                        except:
                            continue

                    if flights:
                        df = pd.DataFrame(flights)
                        df = df.sort_values(by="Preț Total", key=lambda x: x.str.replace("[^0-9.]", "", regex=True).astype(float))

                        st.success(f"Am găsit {len(df)} oferte low-cost!")
                        st.dataframe(df.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True, height=600)

                        # Descărcare CSV
                        csv = df.to_csv(index=False).encode()
                        st.download_button("Descarcă rezultatele", csv,
                                           f"lowcost_{origin}_{destination}_{depart_date.strftime('%Y%m%d')}.csv", "text/csv")

                        # Monitorizare
                        current_price = float(df.iloc[0]["Preț Total"].split()[0].replace(",", ""))
                        target = st.number_input("Notifică-mă dacă scade sub (€)", value=int(current_price - 15), step=5)
                        if st.button("Adaugă la monitorizare"):
                            st.session_state.setdefault("watchlist", []).append({
                                "origin": origin, "dest": destination,
                                "depart": depart_date.strftime("%Y-%m-%d"),
                                "return": return_date.strftime("%Y-%m-%d"),
                                "adults": adults, "non_stop": non_stop,
                                "only_lowcost": only_lowcost,
                                "target": target, "last_price": current_price
                            })
                            st.success("Rută low-cost adăugată la monitorizare!")
                            st.balloons()
                    else:
                        st.warning("Nu am găsit zboruri low-cost pentru această rută.")
                else:
                    st.error("Nu am primit răspuns de la Amadeus.")

# Tab Monitorizare
with tab2:
    st.header("Rute low-cost monitorizate")
    if "watchlist" in st.session_state and st.session_state.watchlist:
        for i, r in enumerate(st.session_state.watchlist):
            with st.expander(f"{r['origin']} → {r['dest']} → {r['origin']} | {r['depart']} ⇄ {r['return']} | Țintă: {r['target']}€"):
                st.write(f"Adulți: {r['adults']} | {'Doar low-cost' if r.get('only_lowcost') else 'Toate companiile'}")
                if st.button("Verifică acum", key=f"check{i}"):
                    data = search_roundtrip(r["origin"], r["dest"], r["depart"], r["return"], r["adults"], r.get("non_stop", False), r.get("only_lowcost", False))
                    if data and data.get("data"):
                        new_price = float(data["data"][0]["price"]["grandTotal"])
                        if new_price < r["last_price"]:
                            st.balloons()
                            st.success(f"PREȚ SCĂZUT! {r['last_price']:.0f}€ → {new_price:.0f}€")
                        else:
                            st.info(f"Preț curent: {new_price:.0f}€")
                        r["last_price"] = new_price
                    st.rerun()
    else:
        st.info("Nicio rută monitorizată încă.")

# Auto-refresh
if "watchlist" in st.session_state and len(st.session_state.watchlist) > 0:
    time.sleep(180)
    st.rerun()
