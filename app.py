import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
from fpdf import FPDF

st.set_page_config(page_title="Zboruri Ieftine PRO", page_icon="plane", layout="wide")

# === TOATE AEROPORTURILE – IDENTICE PENTRU AMBELE TAB-URI ===
AIRPORTS = {
    "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"},
    "Grecia (Insule)": {"JTR": "Santorini", "JMK": "Mykonos", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia", "KGS": "Kos", "SMI": "Samos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros", "KLX": "Kalamata"},
    "Spania & Insule": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza", "TFS": "Tenerife Sud", "ACE": "Lanzarote", "LPA": "Gran Canaria"},
    "Italia": {"FCO": "Roma Fiumicino", "MXP": "Milano Malpensa", "VCE": "Veneția", "NAP": "Napoli", "CTA": "Catania", "PMO": "Palermo", "BRI": "Bari", "BDS": "Brindisi"},
    "Marea Britanie": {"LHR": "London Heathrow", "LGW": "London Gatwick", "STN": "London Stansted", "LTN": "London Luton", "MAN": "Manchester"},
    "Franța": {"CDG": "Paris CDG", "ORY": "Paris Orly", "NCE": "Nisa", "MRS": "Marseille"},
    "Alte destinații": {"AMS": "Amsterdam", "BER": "Berlin", "VIE": "Viena", "PRG": "Praga", "BUD": "Budapesta", "LIS": "Lisabona", "OPO": "Porto", "IST": "Istanbul", "DXB": "Dubai", "DOH": "Doha"}
}

# Toate destinațiile (fără România) – folosite în ambele tab-uri
ALL_DESTINATIONS = {}
for category, cities in AIRPORTS.items():
    if category != "România":
        for code, name in cities.items():
            ALL_DESTINATIONS[code] = f"{name} ({category})"

# Low-cost airlines
LOW_COST = {"W6", "FR", "U2", "VY", "HV", "EW", "VO", "LS", "TO", "RK"}

# Token cache
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
    except:
        st.error("Eroare conectare Amadeus")
        return None

# === CĂUTARE NORMALĂ ===
@st.cache_data(ttl=600)
def search_flights(origin, dest, dep, ret, adults=1, non_stop=False, only_lowcost=True):
    token = get_token()
    if not token: return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin, "destinationLocationCode": dest,
        "departureDate": dep, "returnDate": ret, "adults": adults,
        "travelClass": "ECONOMY", "nonStop": "true" if non_stop else "false",
        "currencyCode": "EUR", "max": 30
    }
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# === CĂUTARE WEEKEND (doar low-cost) ===
@st.cache_data(ttl=3600)
def search_weekend(origin, dest, friday_date):
    token = get_token()
    if not token: return None
    sunday = friday_date + timedelta(days=2 if (friday_date + timedelta(days=2)).month == friday_date.month else 3)
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin, "destinationLocationCode": dest,
        "departureDate": friday_date.strftime("%Y-%m-%d"),
        "returnDate": sunday.strftime("%Y-%m-%d"),
        "adults": 1, "travelClass": "ECONOMY", "currencyCode": "EUR", "max": 10
    }
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=25)
        if r.status_code == 200 and r.json().get("data"):
            for offer in r.json()["data"]:
                carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                if carrier in LOW_COST:
                    return float(offer["price"]["grandTotal"])
        return None
    except:
        return None

# === PDF ===
def create_pdf_weekend(df, origin, dest, year):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 15, f"Cel mai ieftin weekend {year}", ln=1, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"{origin} → {dest} → {origin}", ln=1)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 10, "Luna", 1, 0, "C", True)
    pdf.cell(80, 10, "Weekend", 1, 0, "C", True)
    pdf.cell(50, 10, "Preț (EUR)", 1, 1, "C", True)
    pdf.set_font("Arial", size=11)
    for i, row in df.iterrows():
        fill = (i == 0)
        pdf.set_fill_color(255, 215, 0) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(60, 10, row["Luna"], 1, 0, "C", fill)
        pdf.cell(80, 10, row["Weekend"], 1, 0, "C", fill)
        pdf.cell(50, 10, f"{row['Preț']:.0f} €", 1, 1, "C", fill)
    return pdf.output(dest="S").encode("latin-1")

# === TABURI ===
tab1, tab2 = st.tabs(["Căutare Dus-Întors", "Cel mai ieftin weekend al anului"])

# === TAB 1: CĂUTARE NORMALĂ ===
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
    only_lowcost = st.checkbox("Doar low-cost (Wizz, Ryanair etc.)", value=True)
    non_stop = st.checkbox("Doar zboruri directe", value=False)

    if st.button("Caută cele mai ieftine bilete", type="primary"):
        if depart >= ret:
            st.error("Data întoarsă trebuie să fie după plecare!")
        else:
            with st.spinner("Caut cele mai bune oferte..."):
                data = search_flights(origin, destination, depart.strftime("%Y-%m-%d"), ret.strftime("%Y-%m-%d"), adults, non_stop, only_lowcost)
                if data and data.get("data"):
                    flights = []
                    for o in data["data"]:
                        try:
                            price = float(o["price"]["grandTotal"])
                            carrier = o["itineraries"][0]["segments"][0]["carrierCode"]
                            if only_lowcost and carrier not in LOW_COST: continue
                            dur_out = o["itineraries"][0]["duration"][2:].replace("H","h ").replace("M","m")
                            dur_ret = o["itineraries"][1]["duration"][2:].replace("H","h ").replace("M","m")
                            flights.append({
                                "Preț Total": f"{price:,.2f} €",
                                "Companie": carrier,
                                "Durata Dus": dur_out,
                                "Durata Întors": dur_ret
                            })
                        except: continue
                    if flights:
                        df = pd.DataFrame(flights).sort_values(by="Preț Total", key=lambda x: x.str.replace("[^0-9.]","").astype(float))
                        st.success(f"Am găsit {len(df)} oferte!")
                        st.dataframe(df.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True)
                        st.download_button("Descarcă CSV", df.to_csv(index=False).encode(), "zboruri.csv", "text/csv")
                    else:
                        st.warning("Nu am găsit zboruri low-cost.")
                else:
                    st.warning("Nu am găsit zboruri pentru ruta și datele alese.")

# === TAB 2: CEL MAI IEFTIN WEEKEND – ACUM CU TOATE DESTINAȚIILE ===
with tab2:
    st.header("Cel mai ieftin weekend din fiecare lună")
    col1, col2, col3 = st.columns(3)
    with col1:
        origin_w = st.selectbox("Plecare din", list(AIRPORTS["România"].keys()), format_func=lambda x: AIRPORTS["România"][x], key="origin_w")
    with col2:
        destination_w = st.selectbox("Destinație", list(ALL_DESTINATIONS.keys()), format_func=lambda x: ALL_DESTINATIONS[x], key="dest_w")
    with col3:
        year_w = st.selectbox("An", [2025, 2026, 2027, 2028], key="year_w")

    if st.button("Găsește cel mai ieftin weekend din fiecare lună!", type="primary", use_container_width=True):
        with st.spinner(f"Caut în toate weekend-urile lui {year_w}... (poate dura 2-4 minute)"):
            results = []
            progress = st.progress(0)
            for month in range(1, 13):
                progress.progress(month / 12)
                first_day = datetime(year_w, month, 1)
                first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
                best_price = None
                best_weekend = ""
                for offset in [0, 7, 14, 21]:
                    friday = first_friday + timedelta(days=offset)
                    if friday.year != year_w or friday.month != month: continue
                    price = search_weekend(origin_w, destination_w, friday)
                    if price and (best_price is None or price < best_price):
                        best_price = price
                        sunday = friday + timedelta(days=2 if (friday + timedelta(days=2)).month == month else 3)
                        best_weekend = f"{friday.day}-{sunday.day} {friday.strftime('%B')}"
                if best_price:
                    results.append({
                        "Luna": first_day.strftime("%B %Y"),
                        "Weekend": best_weekend,
                        "Preț": best_price
                    })
            progress.empty()
            if results:
                df = pd.DataFrame(results).sort_values("Preț")
                best = df.iloc[0]
                st.balloons()
                st.success(f"CEL MAI IEFTIN WEEKEND DIN {year_w}:")
                st.markdown(f"### {best['Weekend']} → **{best['Preț']:.0f} EUR** dus-întors cu low-cost!")
                st.markdown(f"**Ruta:** {AIRPORTS['România'][origin_w]} → {ALL_DESTINATIONS[destination_w]}")
                st.dataframe(df.style.highlight_min("Preț", "gold"), use_container_width=True, height=500)
                pdf = create_pdf_weekend(df, AIRPORTS["România"][origin_w], ALL_DESTINATIONS[destination_w], year_w)
                st.download_button("Descarcă raport PDF", pdf, f"weekend_{origin_w}_{destination_w}_{year_w}.pdf", "application/pdf")
            else:
                st.warning("Nu am găsit zboruri low-cost în acest an pentru ruta aleasă.")

st.caption("Cea mai puternică aplicație de zboruri ieftine din România – creată pentru tine!")
