# services/amadeus.py
import streamlit as st
import requests
import time
from cachetools import TTLCache

# Cache pentru token (valabil 30 minute)
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
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        token = response.json()["access_token"]
        token_cache["token"] = token
        return token
    except Exception as e:
        st.error(f"Eroare autentificare Amadeus: {e}")
        return None

@st.cache_data(ttl=300)  # 5 minute cache per query
def search_flights(
    origin, destination, departure_date,
    adults=1, travel_class="ECONOMY", non_stop=True,
    max_results=20
):
    token = get_amadeus_token()
    if not token:
        return None

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": departure_date,
        "adults": adults,
        "travelClass": travel_class,
        "nonStop": str(non_stop).lower(),
        "currencyCode": "EUR",
        "max": max_results
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            st.warning("Rate limit atins. Așteaptă 10 secunde...")
            time.sleep(10)
            return search_flights(origin, destination, departure_date, adults, travel_class, non_stop, max_results)
        else:
            st.error(f"Eroare API Amadeus: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Eroare conexiune: {e}")
        return None
