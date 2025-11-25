import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import json
import os
from cachetools import TTLCache

st.set_page_config(page_title="Zboruri Ieftine PRO", page_icon="✈️", layout="wide")

# --- Lista aeroporturi complete (peste 300 cele mai importante) ---
# === LISTA COMPLETĂ AEROPORTURI 2025 – TOATE INSULELE GRECEȘTI + TOP DESTINAȚII ===
AIRPORTS = {
    "Europa": {
        "România": {
            "OTP": "București - Henri Coandă (Otopeni)",
            "CLJ": "Cluj-Napoca",
            "TSR": "Timișoara",
            "IAS": "Iași",
            "SBZ": "Sibiu",
            "CRA": "Craiova",
            "BCM": "Bacău",
            "SCV": "Suceava",
            "TGM": "Târgu Mureș"
        },
        "Grecia (Continent + Insule)": {
            "ATH": "Atena - Eleftherios Venizelos",
            "SKG": "Salonic",
            "HER": "Creta - Heraklion (Iraklio)",
            "CHQ": "Creta - Chania",
            "RHO": "Rhodos",
            "JTR": "Santorini (Thira)",
            "JMK": "Mykonos",
            "CFU": "Corfu (Kerkyra)",
            "ZTH": "Zakynthos",
            "EFL": "Kefalonia",
            "KLX": "Kalamata",
            "KGS": "Kos",
            "SMI": "Samos",
            "AOK": "Karpathos",
            "JSH": "Sitia (Creta)",
            "PVK": "Preveza / Lefkada",
            "LRS": "Leros",
            "JIK": "Ikaria",
            "MLO": "Milos",
            "PAS": "Paros",
            "JSI": "Skiathos",
            "JTY": "Astypalaia",
            "AXD": "Alexandroupoli"
        },
        "Spania (inclusiv insule)": {
            "BCN": "Barcelona",
            "MAD": "Madrid",
            "AGP": "Malaga",
            "ALC": "Alicante",
            "PMI": "Palma de Mallorca",
            "IBZ": "Ibiza",
            "TFN": "Tenerife Nord",
            "TFS": "Tenerife Sud",
            "LPA": "Gran Canaria",
            "ACE": "Lanzarote",
            "VLC": "Valencia",
            "SVQ": "Sevilla",
            "BIO": "Bilbao"
        },
        "Italia": {
            "FCO": "Roma Fiumicino",
            "MXP": "Milano Malpensa",
            "VCE": "Veneția Marco Polo",
            "NAP": "Napoli",
            "CTA": "Catania (Sicilia)",
            "PMO": "Palermo (Sicilia)",
            "OLB": "Olbia (Sardinia)",
            "CAG": "Cagliari (Sardinia)",
            "BLQ": "Bologna",
            "FLR": "Florența",
            "TRN": "Torino",
            "BRI": "Bari",
            "BDS": "Brindisi"
        },
        "Marea Britanie": {
            "LHR": "London Heathrow",
            "LGW": "London Gatwick",
            "STN": "London Stansted",
            "LTN": "London Luton",
            "MAN": "Manchester",
            "EDI": "Edinburgh",
            "GLA": "Glasgow"
        },
        "Franța": {
            "CDG": "Paris Charles de Gaulle",
            "ORY": "Paris Orly",
            "NCE": "Nisa",
            "MRS": "Marseille",
            "LYS": "Lyon",
            "TLS": "Toulouse",
            "BOD": "Bordeaux"
        },
        "Germania": {
            "FRA": "Frankfurt",
            "MUC": "München",
            "BER": "Berlin Brandenburg",
            "DUS": "Düsseldorf",
            "HAM": "Hamburg",
            "CGN": "Köln Bonn",
            "STR": "Stuttgart"
        },
        "Alte țări Europa": {
            "AMS": "Amsterdam (Olanda)",
            "BRU": "Bruxelles (Belgia)",
            "VIE": "Viena (Austria)",
            "ZRH": "Zürich (Elveția)",
            "GVA": "Geneva (Elveția)",
            "PRG": "Praga (Cehia)",
            "WAW": "Varșovia (Polonia)",
            "KRK": "Cracovia (Polonia)",
            "BUD": "Budapesta (Ungaria)",
            "LIS": "Lisabona (Portugalia)",
            "OPO": "Porto (Portugalia)",
            "DUB": "Dublin (Irlanda)",
            "OSL": "Oslo (Norvegia)",
            "CPH": "Copenhaga (Danemarca)",
            "STO": "Stockholm Arlanda (Suedia)",
            "HEL": "Helsinki (Finlanda)"
        }
    },
    "Asia": {
        "Turcia": {"IST": "Istanbul", "AYT": "Antalya", "ADB": "Izmir"},
        "Emiratele Arabe": {"DXB": "Dubai", "AUH": "Abu Dhabi"},
        "Qatar": {"DOH": "Doha"},
        "Thailanda": {"BKK": "Bangkok Suvarnabhumi", "HKT": "Phuket", "CNX": "Chiang Mai"},
        "Altele": {
            "DEL": "Delhi (India)",
            "BOM": "Mumbai (India)",
            "SIN": "Singapore",
            "HKG": "Hong Kong",
            "ICN": "Seoul Incheon (Coreea)",
            "NRT": "Tokyo Narita (Japonia)",
            "KIX": "Osaka Kansai (Japonia)"
        }
    },
    "America": {
        "SUA": {
            "JFK": "New York JFK",
            "EWR": "New York Newark",
            "LAX": "Los Angeles",
            "MIA": "Miami",
            "ORD": "Chicago O'Hare",
            "SFO": "San Francisco",
            "LAS": "Las Vegas",
            "MCO": "Orlando",
            "ATL": "Atlanta",
            "BOS": "Boston"
        },
        "Canada": {"YYZ": "Toronto", "YVR": "Vancouver", "YUL": "Montreal"}
    },
    "Africa & Orientul Mijlociu": {
        "Egipt": {"CAI": "Cairo", "HRG": "Hurghada", "SSH": "Sharm El Sheikh"},
        "Maroc": {"CMN": "Casablanca", "RAK": "Marrakech", "AGA": "Agadir"},
        "Tunisia": {"TUN": "Tunis"},
        "Israel": {"TLV": "Tel Aviv"}
    }
}

# --- Cache token Amadeus ---
token_cache = TTLCache(maxsize=1, ttl=1700)

def get_amadeus_token():
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

@st.cache_data(ttl=300)
def search_flights(origin, dest, date, adults=1, cabin="ECONOMY", nonstop=True):
    token = get_amadeus_token()
    if not token: return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": dest,
        "departureDate": date,
        "adults": adults,
        "travelClass": cabin,
        "nonStop": "true" if nonstop else "false",
        "currencyCode": "EUR",
        "max": 30
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

# --- Inițializare stare ---
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "history" not in st.session_state:
    st.session_state.history = {}

# --- UI ---
st.title("✈️ Zboruri Ieftine PRO – Monitorizare & Notificări")
tab1, tab2, tab3 = st.tabs(["Căutare nouă", "Rute monitorizate", "Istoric prețuri"])

with tab1:
    st.header("Caută zboruri ieftine")
    
    col1, col2 = st.columns(2)
    with col1:
        continent = st.selectbox("Continent", options=list(AIRPORTS.keys()))
        country = st.selectbox("Țară", options=list(AIRPORTS[continent].keys()))
        origin_code = st.selectbox("Plecare", options=list(AIRPORTS[continent][country].keys()),
                                   format_func=lambda x: f"{x} - {AIRPORTS[continent][country][x]}")
    with col2:
        dest_continent = st.selectbox("Continent destinație", options=list(AIRPORTS.keys()), index=0)
        dest_country = st.selectbox("Țară destinație", options=list(AIRPORTS[dest_continent].keys()))
        dest_code = st.selectbox("Destinație", options=list(AIRPORTS[dest_continent][dest_country].keys()),
                                 format_func=lambda x: f"{x} - {AIRPORTS[dest_continent][dest_country][x]}")

    col3, col4 = st.columns(2)
    with col3:
        date = st.date_input("Data plecare", datetime.today() + timedelta(days=14))
    with col4:
        adults = st.number_input("Adulți", 1, 9, 1)

    nonstop = st.checkbox("Doar directe", True)
    if st.button("Caută acum", type="primary"):
        with st.spinner("Caut cele mai bune oferte..."):
            data = search_flights(origin_code, dest_code, date.strftime("%Y-%m-%d"), adults, "ECONOMY", nonstop)
            if data and data.get("data"):
                flights = []
                for o in data["data"]:
                    try:
                        price = float(o["price"]["grandTotal"])
                        itin = o["itineraries"][0]
                        dur = itin["duration"].replace("PT","").replace("H","h ").replace("M","m")
                        stops = len(itin["segments"]) - 1
                        airline = itin["segments"][0]["carrierCode"]
                        dep = itin["segments"][0]["departure"]["at"][11:16]
                        arr = itin["segments"][-1]["arrival"]["at"][11:16]
                        flights.append({
                            "Preț": price,
                            "Companie": airline,
                            "Durata": dur,
                            "Escală": stops,
                            "Plecare": dep,
                            "Sosire": arr
                        })
                    except:
                        continue
                
                if flights:
                    df = pd.DataFrame(flights).sort_values("Preț")
                    df["Preț"] = df["Preț"].apply(lambda x: f"{x:,.2f} €")
                    st.success(f"Găsite {len(df)} oferte!")
                    st.dataframe(df.style.highlight_min("Preț", "lightgreen"), use_container_width=True)
                    
                    # Adaugă la monitorizare
                    target = st.number_input("Vreau să fiu notificat dacă scade sub (€)", value=int(df["Preț"].str.replace(" €","", regex=True).str.replace(",","").astype(float).min()) - 5)
                    if st.button("Monitorizează această rută"):
                        route = {
                            "origin": origin_code,
                            "origin_name": AIRPORTS[continent][country][origin_code],
                            "dest": dest_code,
                            "dest_name": AIRPORTS[dest_continent][dest_country][dest_code],
                            "date": date.strftime("%Y-%m-%d"),
                            "adults": adults,
                            "target_price": target,
                            "current_price": float(df.iloc[0]["Preț"].replace(" €","").replace(",","")),
                            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.session_state.watchlist.append(route)
                        st.success("Rută adăugată la monitorizare!")
                        st.rerun()
                else:
                    st.warning("Nu am găsit zboruri.")
            else:
                st.error("Nu am găsit zboruri.")

# --- Tab Monitorizare ---
with tab2:
    st.header("Rute monitorizate")
    if st.session_state.watchlist:
        for i, route in enumerate(st.session_state.watchlist):
            with st.container():
                col1, col2, col3 = st.columns([3,2,1])
                with col1:
                    st.write(f"**{route['origin_name']} → {route['dest_name']}**")
                    st.caption(f"{route['date']} • {route['adults']} adulți • Țintă: {route['target_price']} €")
                with col2:
                    if st.button("Verifică acum", key=f"check_{i}"):
                        with st.spinner("Verific prețul..."):
                            data = search_flights(route["origin"], route["dest"], route["date"], route["adults"])
                            if data and data.get("data"):
                                new_price = float(data["data"][0]["price"]["grandTotal"])
                                route["current_price"] = new_price
                                route["last_check"] = datetime.now().strftime("%H:%M")
                                if new_price <= route["target_price"]:
                                    st.balloons()
                                    st.success(f"PREȚ SCĂZUT! Acum: {new_price:.2f} €")
                                    st.audio("https://www.soundjay.com/buttons/sounds/button-09.mp3", format="audio/mp3")
                                else:
                                    st.info(f"Preț curent: {new_price:.2f} €")
                                st.rerun()
                with col3:
                    if st.button("Șterge", key=f"del_{i}"):
                        st.session_state.watchlist.pop(i)
                        st.rerun()
    else:
        st.info("Nu monitorizezi nicio rută încă.")

# Auto-check la fiecare 3 minute
if st.session_state.watchlist:
    time.sleep(180)
    st.rerun()
