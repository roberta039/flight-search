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
        
                        if data and "data" in data and len(data["data"]) > 0:
            flights = []
            for offer in data["data"]:
                try:
                    price_total = float(offer["price"]["grandTotal"])
                    currency = offer["price"]["currency"]

                    itin = offer["itineraries"][0]
                    segments = itin["segments"]
                    duration = itin["duration"].replace("PT", "").replace("H", "h ").replace("M", "m")

                    stops = len(segments) - 1
                    stop_cities = ", ".join([s["arrival"]["iataCode"] for s in segments[:-1]]) if stops > 0 else "Direct"

                    dep_time = segments[0]["departure"]["at"][11:16]
                    arr_time = segments[-1]["arrival"]["at"][11:16]

                    airline = segments[0]["carrierCode"]

                    flights.append({
                        "Preț": price_total,
                        "Moneda": currency,
                        "Companie": airline,
                        "Durata": duration,
                        "Escală": stops,
                        "Ora plecare": dep_time,
                        "Ora sosire": arr_time,
                        "Escală la": stop_cities,
                    })
                except Exception as e:
                    continue

            if flights:
                df = pd.DataFrame(flights)
                df = df.sort_values(by="Preț", ascending=True).reset_index(drop=True)
                df["Preț"] = df["Preț"].apply(lambda x: f"{x:,.2f} {df['Moneda'].iloc[0]}")

                st.success(f"Am găsit {len(df)} oferte!")

                st.dataframe(
                    df.style.highlight_min(subset=["Preț"], color="#90EE90")
                           .set_properties(**{'text-align': 'center'}),
                    use_container_width=True,
                    height=600
                )

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Descarcă CSV",
                    csv,
                    f"zboruri_{origin}_{destination}_{departure_date}.csv",
                    "text/csv"
                )
            else:
                st.warning("Am primit date de la Amadeus, dar nu am putut extrage zboruri valide.")
        else:
            st.error("Nu am găsit zboruri pentru această rută și dată. Încearcă altă dată sau destinație.")

# Auto-refresh
if auto_refresh:
    st.rerun() if refresh_interval else None
    time.sleep(refresh_interval)
    st.rerun()
