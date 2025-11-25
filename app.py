import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.amadeus import search_flights

# Configurare pagină
st.set_page_config(
    page_title="Zboruri Ieftine România",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Căutare Zboruri Ieftine – Amadeus API")
st.markdown("Cel mai rapid tool pentru a găsi bilete ieftine din România")

# Sidebar cu parametri
with st.sidebar:
    st.header("Parametri căutare")
    origin = st.text_input("Plecare (IATA)", value="OTP", help="Ex: OTP, CLJ, TSR, IAS")
    destination = st.text_input("Destinație (IATA)", value="BCN", help="Ex: BCN, LGW, FCO, MXP")
    
    default_date = datetime.today() + timedelta(days=14)
    date = st.date_input("Data plecare", value=default_date, min_value=datetime.today())
    departure_date = date.strftime("%Y-%m-%d")
    
    adults = st.number_input("Adulți", min_value=1, max_value=9, value=1)
    cabin = st.selectbox("Clasă", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
    non_stop = st.checkbox("Doar zboruri directe", value=True)
    
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh la fiecare 2 minute", value=False)

# Buton căutare + auto-refresh
trigger_search = st.button("Caută cele mai ieftine zboruri", type="primary")
if auto_refresh or trigger_search:
    with st.spinner("Interoghez Amadeus... (poate dura 5-10 secunde)"):
        data = search_flights(
            origin=origin.upper(),
            destination=destination.upper(),
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
                except:
                    continue

            if flights:
                df = pd.DataFrame(flights)
                df = df.sort_values(by="Preț", ascending=True).reset_index(drop=True)
                df["Preț"] = df["Preț"].apply(lambda x: f"{x:,.2f} {df['Moneda'].iloc[0]}")

                st.success(f"Găsite {len(df)} oferte pentru {origin} → {destination} pe {date.strftime('%d %b %Y')}")

                # Tabel frumos
                st.dataframe(
                    df.drop(columns=["Moneda"]),  # ascundem coloana Moneda duplicată
                    use_container_width=True,
                    height=600,
                    column_config={
                        "Preț": st.column_config.TextColumn("Preț", help="Preț total per adult"),
                    }
                )

                # Highlight cel mai ieftin
                st.markdown(f"**Cel mai ieftin zbor:** {df['Preț'].iloc[0]}")

                # Descărcare CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descarcă rezultatele ca CSV",
                    data=csv,
                    file_name=f"zboruri_{origin}_{destination}_{departure_date}.csv",
                    mime="text/csv"
                )

            else:
                st.warning("Am primit date de la Amadeus, dar nu am găsit zboruri valide.")
        else:
            st.error("Nu am găsit zboruri pentru ruta și data selectată. Încearcă altă dată sau destinație.")

# Auto-refresh inteligent
if auto_refresh:
    import time
    time.sleep(120)
    st.rerun()
