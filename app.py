import streamlit as st
from opencage.geocoder import OpenCageGeocode
from streamlit_folium import st_folium
import folium
from google import genai
from google.genai import types

st.set_page_config(page_title="Chat with Google Maps", layout="wide")


st.markdown(
    "<h1 style='text-align: center;'>Chat Google Maps with AI</h1>",
    unsafe_allow_html=True
)

if "lat" not in st.session_state: st.session_state.lat = 11.6854
if "lon" not in st.session_state: st.session_state.lon = 76.1320
if "zoom" not in st.session_state: st.session_state.zoom = 18
if "google_api_key" not in st.session_state: st.session_state.google_api_key = None
if "opencage_key" not in st.session_state: st.session_state.opencage_key = None

st.subheader("🗺️ Interactive Map")

m = folium.Map(
    location=[st.session_state.lat, st.session_state.lon],
    zoom_start=st.session_state.zoom,
)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google Satellite",
    name="Satellite View"
).add_to(m)

folium.Marker(
    [st.session_state.lat, st.session_state.lon],
    tooltip="Searched Location",
    icon=folium.Icon(color="red")
).add_to(m)

folium.LayerControl().add_to(m)

map_data = st_folium(m, width=1400, height=500)

clicked_lat, clicked_lon = None, None
if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]

left_api, right_api = st.columns(2)

with left_api:
    st.header("🔐 Google API Key")
    google_api_key = st.text_input("Enter Google API Key:", type="password")

with right_api:
    st.header("🔑 OpenCage API Key")
    opencage_key = st.text_input("Enter OpenCage API Key:", type="password")

save_btn = st.button("Save API Keys")
if save_btn:
    if not google_api_key or not opencage_key:
        st.error("Please fill in both API keys.")
    else:
        st.session_state.google_api_key = google_api_key
        st.session_state.opencage_key = opencage_key
        st.success("API keys saved successfully!")

client = genai.Client(api_key=st.session_state.google_api_key) if st.session_state.google_api_key else None
geocoder = OpenCageGeocode(st.session_state.opencage_key) if st.session_state.opencage_key else None


st.markdown("<h2 style='text-align:center;'>📍 Clicked Coordinates</h2>", unsafe_allow_html=True)

if clicked_lat and clicked_lon:
    st.markdown(f"<p style='text-align:center;'>Lat: {clicked_lat:.6f}, Lon: {clicked_lon:.6f}</p>",
                unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align:center;'>Click anywhere on the map to get coordinates.</p>",
                unsafe_allow_html=True)
place = st.text_input("Search a place:", "New Delhi")
search_btn = st.button("Search Location")


chat_col, output_col = st.columns(2)

with chat_col:
    st.header("💬 Chat and Search About This Location")

    

    if search_btn:
        if geocoder is None:
            st.error("Enter OpenCage Key first")
        else:
            results = geocoder.geocode(place)
            if results:
                st.session_state.lat = results[0]["geometry"]["lat"]
                st.session_state.lon = results[0]["geometry"]["lng"]
                st.success("Location Updated!")
            else:
                st.error("Place not found.")

    query = st.text_input("Ask something like:", "Best restaurants nearby")
    chat_btn = st.button("Ask Gemini")


with output_col:
    st.header("✨ Gemini Response")

    if chat_btn and query:
        if client is None:
            st.error("Please enter Google API Key.")
        else:
            active_lat = clicked_lat if clicked_lat else st.session_state.lat
            active_lon = clicked_lon if clicked_lon else st.session_state.lon

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Find {query} near these coordinates: {active_lat}, {active_lon}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_maps=types.GoogleMaps())],
                    tool_config=types.ToolConfig(
                        retrieval_config=types.RetrievalConfig(
                            lat_lng=types.LatLng(latitude=active_lat, longitude=active_lon)
                        )
                    ),
                ),
            )

            gemini_text = response.text

      
            sources_list = []

            if hasattr(response.candidates[0], "grounding_metadata"):
                for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                    if hasattr(chunk, "maps"):
                        title = chunk.maps.title
                        uri = chunk.maps.uri
                        sources_list.append(f"- {title}: {uri}")

            sources_text = "\n".join(sources_list)
          
            html_box = f"""
                    <div style="
                        background-color: #000;
                        padding: 20px;
                        border-radius: 10px;
                        height: 350px;
                        overflow-y: scroll;
                        border: 1px solid #444;
                    ">
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 14px; color: white;">
                    {gemini_text}
                    {sources_text}
                    """
            st.markdown(html_box, unsafe_allow_html=True)
