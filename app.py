# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.amadeus import search_flights

st.set_page_config(page_title="Zboruri Ieftine România", layout="wide")
st.title(" Căutare Zboruri Ieftine (Amadeus API)")

# Sidebar
with st.sidebar:
    st.header("Parametri căutare")
    origin = st.text_input("Din (ex: OTP, CLJ, TSR)", "OTP")
    destination = st.text_input("Către (ex: BCN, LGW, FCO)", "BCN")
    
    date = st.date_input("Data plecare", datetime.today() + timedelta(days=7))
    departure_date = date.strftime("%Y-%m-%d")
    
    adults = st.number_input("Adulți", 1, 8, 1)
    cabin = st.selectbox("Clasă", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
    non_stop = st.checkbox("Doar zboruri directe", value=True)
    
    auto_refresh = st.checkbox(" Auto-refresh la fiecare 2 minute")
    refresh_interval = 120 if auto_refresh else 0

if st.button("Caută cele mai ieftine zboruri") or auto_refresh:
    with st.spinner("Caut cele mai bune oferte..."):
        data = search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            adults=adults,
            travel_class=cabin,
            non_stop=non_stop
        )
        
        if data and "data" in data:
            flights = []
            for offer in data["data"]:
                price = float(offer["price"]["total"])
                currency = offer["price"]["currency"]
                
                itin = offer["itineraries"][0]
                segments = itin["segments"]
                duration = itin["duration"].replace("PT", "").replace("H", "h ").replace("M", "m")
                
                # Pentru zboruri cu escală
                stops = len(segments) - 1
                stop_cities = ", ".join([seg["arrival"]["iataCode"] for seg in segments[:-1]]) if stops > 0 else "Direct"
                
                departure = segments[0]["departure"]["at"][11:16]
                arrival = segments[-1]["arrival"]["at"][11:16]
                
                airline = segments[0]["carrierCode"]
                
                flights.append({
                    "Preț": f"{price} {currency}",
                    "Companie": airline,
                    "Durata": duration,
                    "Escală": stops,
                    "Ora plecare": departure,
                    "Ora sosire": arrival,
                    "Detalii escală": stop_cities,
                    "Link rezervare": offer.get("offerId", "")
                })
            
            df = pd.DataFrame(flights)
            df = df.sort_values(by="Preț", key=lambda x: x.str.extract(r'(\d+\.?\d*)').astype(float)[0])
            
            st.success(f"Am găsit {len(df)} oferte!")
            
            # Tabel frumos ca Excel
            st.dataframe(
                df.style.highlight_min(subset=["Preț"], color="#90EE90")
                       .format({"Preț": lambda x: x}),
                use_container_width=True,
                height=600
            )
            
            # Buton descărcare CSV
            csv = df.to_csv(index=False).encode()
            st.download_button("Descarcă rezultate CSV", csv, "zboruri_ieftine.csv", "text/csv")
            
        else:
            st.error("Nu am găsit zboruri sau a apărut o eroare.")

# Auto-refresh
if auto_refresh:
    st.rerun() if refresh_interval else None
    time.sleep(refresh_interval)
    st.rerun()
