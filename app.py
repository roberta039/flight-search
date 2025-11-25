import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
from fpdf import FPDF  # pentru PDF
import base64

st.set_page_config(page_title="Zboruri Ieftine ULTIMATE", page_icon="✈️", layout="wide")

# === COMPANII LOW-COST ===
LOW_COST_AIRLINES = {
    "W6": "Wizz Air", "FR": "Ryanair", "U2": "EasyJet", "VY": "Vueling",
    "HV": "Transavia", "EW": "Eurowings", "VO": "Volotea", "LS": "Jet2"
}

# === AEROPORTURI (toate insulele grecești + România) ===
AIRPORTS = {
    "Europa": {
        "România": {"OTP": "București Otopeni", "CLJ": "Cluj-Napoca", "TSR": "Timișoara", "IAS": "Iași", "SBZ": "Sibiu", "BCM": "Bacău"},
        "Grecia (Toate insulele)": {
            "ATH": "Atena", "HER": "Creta Heraklion", "CHQ": "Creta Chania", "RHO": "Rhodos",
            "JTR": "Santorini", "JMK": "Mykonos", "CFU": "Corfu", "ZTH": "Zakynthos", "EFL": "Kefalonia",
            "KGS": "Kos", "SMI": "Samos", "PVK": "Preveza/Lefkada", "JSI": "Skiathos", "PAS": "Paros"
        },
        "Spania": {"BCN": "Barcelona", "MAD": "Madrid", "AGP": "Malaga", "ALC": "Alicante", "PMI": "Palma de Mallorca", "IBZ": "Ibiza"},
        "Italia": {"FCO": "Roma", "MXP": "Milano", "NAP": "Napoli", "CTA": "Catania"},
        "Alte destinații": {"LON": "London (toate aeroporturile)", "PAR": "Paris (toate)", "BER": "Berlin", "VIE": "Viena", "AMS": "Amsterdam"}
    }
}

# Cache token
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

@st.cache_data(ttl=900)
def search_flights(origin, dest, dep, ret, adults=1, non_stop=False, only_lowcost=False):
    token = get_token()
    if not token: return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin, "destinationLocationCode": dest,
        "departureDate": dep, "returnDate": ret, "adults": adults,
        "travelClass": "ECONOMY", "nonStop": "true" if non_stop else "false",
        "currencyCode": "EUR", "max": 30
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# === GENERARE PDF ===
def create_pdf(df, origin, dest, dep, ret):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_fill_color(0, 102, 204)
    pdf.cell(0, 10, "Cele mai ieftine zboruri", ln=1, align="C", fill=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Ruta: {origin} - {dest} - {origin}", ln=1)
    pdf.cell(0, 10, f"Perioada: {dep} - {ret}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    col_widths = [50, 30, 40, 40, 30]
    headers = ["Preț Total", "Companie", "Durata Dus", "Durata Întors", "Escală"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 10, h, 1, fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for _, row in df.head(10).iterrows():
        pdf.cell(col_widths[0], 10, row["Preț Total"], 1)
        pdf.cell(col_widths[1], 10, row["Companie"], 1)
        pdf.cell(col_widths[2], 10, row["Durata Dus"], 1)
        pdf.cell(col_widths[3], 10, row["Durata Întors"], 1)
        pdf.cell(col_widths[4], 10, row["Escală Dus"] + " / " + row["Escală Întors"], 1)
        pdf.ln()
    
    return pdf.output(dest="S").encode("latin-1")

# === UI ===
st.title("Zboruri Ieftine ULTIMATE – Low-Cost + Cel mai ieftin weekend + PDF")

tab1, tab2, tab3 = st.tabs(["Căutare Normală", "Cel mai ieftin weekend", "Rute Monitorizate"])

# === TAB 1: Căutare normală ===
with tab1:
    st.header("Căutare dus-întors")
    col1, col2 = st.columns(2)
    with col1:
        continent1 = st.selectbox("Continent plecare", list(AIRPORTS.keys()), key="c1")
        country1 = st.selectbox("Țară plecare", list(AIRPORTS[continent1].keys()), key="co1")
        origin = st.selectbox("De la", list(AIRPORTS[continent1][country1].keys()),
                              format_func=lambda x: f"{x} – {AIRPORTS[continent1][country1][x]}", key="o1")
    with col2:
        continent2 = st.selectbox("Continent destinație", list(AIRPORTS.keys()), key="c2")
        country2 = st.selectbox("Țară destinație", list(AIRPORTS[continent2].keys()), key="co2")
        destination = st.selectbox("Către", list(AIRPORTS[continent2][country2].keys()),
                                   format_func=lambda x: f"{x} – {AIRPORTS[continent2][country2][x]}", key="d1")

    col3, col4 = st.columns(2)
    with col3:
        depart = st.date_input("Plecare", datetime.today() + timedelta(days=14), key="dep1")
    with col4:
        ret = st.date_input("Întoarcere", datetime.today() + timedelta(days=21), key="ret1")

    adults = st.number_input("Adulți", 1, 9, 1, key="a1")
    only_lowcost = st.checkbox("Doar low-cost (Wizz, Ryanair, EasyJet)", value=True, key="lc1")
    non_stop = st.checkbox("Doar directe", value=False, key="ns1")

    if st.button("Caută acum", type="primary", key="btn1"):
        if depart >= ret:
            st.error("Data întoarsă trebuie să fie după plecare!")
        else:
            with st.spinner("Caut cele mai ieftine oferte..."):
                data = search_flights(origin, destination, depart.strftime("%Y-%m-%d"), ret.strftime("%Y-%m-%d"), adults, non_stop, only_lowcost)
                if data and data.get("data"):
                    flights = []
                    for offer in data["data"]:
                        try:
                            price = float(offer["price"]["grandTotal"])
                            carrier = offer["itineraries"][0]["segments"][0]["carrierCode"]
                            if only_lowcost and carrier not in LOW_COST_AIRLINES: continue
                            airline_name = LOW_COST_AIRLINES.get(carrier, carrier)
                            dur_out = offer["itineraries"][0]["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            dur_ret = offer["itineraries"][1]["duration"].replace("PT","").replace("H","h ").replace("M","m")
                            stops_out = len(offer["itineraries"][0]["segments"]) - 1
                            stops_ret = len(offer["itineraries"][1]["segments"]) - 1
                            flights.append({
                                "Preț Total": f"{price:,.2f} €",
                                "Companie": airline_name,
                                "Durata Dus": dur_out,
                                "Durata Întors": dur_ret,
                                "Escală Dus": "Direct" if stops_out == 0 else f"{stops_out} escală",
                                "Escală Întors": "Direct" if stops_ret == 0 else f"{stops_ret} escală"
                            })
                        except: continue
                    
                    if flights:
                        df = pd.DataFrame(flights).sort_values(by="Preț Total", key=lambda x: x.str.replace("[^0-9.]","").astype(float))
                        st.success(f"Am găsit {len(df)} oferte!")
                        st.dataframe(df.style.highlight_min("Preț Total", "lightgreen"), use_container_width=True)
                        csv = df.to_csv(index=False).encode()
                        st.download_button("Descarcă CSV", csv, "zboruri.csv", "text/csv")
                        
                        pdf_data = create_pdf(df, origin, destination, depart.strftime("%d.%m"), ret.strftime("%d.%m"))
                        st.download_button("Descarcă PDF", pdf_data, f"zboruri_{origin}_{destination}.pdf", "application/pdf")
                    else:
                        st.warning("Nu am găsit zboruri low-cost.")
                else:
                    st.error("Eroare API")

# === TAB 2: Cel mai ieftin weekend din lună ===
with tab2:
    st.header("Cel mai ieftin weekend din luna următoare")
    col1, col2 = st.columns(2)
    with col1:
        origin_w = st.selectbox("De la", ["OTP", "CLJ", "TSR", "IAS"], format_func=lambda x: AIRPORTS["Europa"]["România"][x], key="ow")
    with col2:
        dest_w = st.selectbox("Către", ["JTR", "JMK", "HER", "RHO", "CFU", "ZTH"], 
                              format_func=lambda x: AIRPORTS["Europa"]["Grecia (Toate insulele)"][x], key="dw")

    if st.button("Găsește cel mai ieftin weekend!", type="primary"):
        with st.spinner("Caut în toate weekend-urile lunii... (30-60 sec)"):
            today = datetime.today()
            start = today + timedelta(days=30 - today.day + 1)  # prima zi a lunii următoare
            weekends = []
            for i in range(0, 30, 7):
                friday = start + timedelta(days=i + (4 - start.weekday()) % 7)
                if friday.month != start.month: break
                sunday = friday + timedelta(days=2)
                if sunday.month != start.month: sunday = friday + timedelta(days=3)  # sâmbătă-luni
                data = search_flights(origin_w, dest_w, friday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"), 1, False, True)
                if data and data.get("data"):
                    price = float(data["data"][0]["price"]["grandTotal"])
                    weekends.append({"Weekend": f"{friday.strftime('%d %b')} → {sunday.strftime('%d %b')}", "Preț": price})
            
            if weekends:
                df_w = pd.DataFrame(weekends).sort_values("Preț")
                best = df_w.iloc[0]
                st.success(f"Cel mai ieftin weekend: {best['Weekend']} – doar {best['Preț']:.0f}€!")
                st.dataframe(df_w.style.highlight_min("Preț", "gold"), use_container_width=True)
                st.balloons()
            else:
                st.warning("Nu am găsit zboruri în luna următoare.")

# Monitorizare + auto-refresh (la fel ca înainte)
if "watchlist" not in st.session_state: st.session_state.watchlist = []
if st.session_state.watchlist:
    time.sleep(180)
    st.rerun()
