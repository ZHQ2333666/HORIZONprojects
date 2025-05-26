import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime, date
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import joblib

st.set_page_config(page_title="Projects and Organizations", layout="wide")

# ----------- Pages -----------
page = st.sidebar.radio("Pages: ", ["Projects", "Organizations", "Predictions of Contributions"])

# ----------- Load data -----------
@st.cache_data

def load_project_data():
    df = pd.read_csv("project.csv")
    df["startDate"] = pd.to_datetime(df["startDate"], errors='coerce')
    df["endDate"] = pd.to_datetime(df["endDate"], errors='coerce')
    df["ecMaxContribution"] = df["ecMaxContribution"].astype(str).str.replace(",", ".", regex=False)
    df["ecMaxContribution"] = pd.to_numeric(df["ecMaxContribution"], errors="coerce")
    return df

@st.cache_data

def load_org_data():
    df = pd.read_csv("organization.csv")
    # Split geolocation to latitude and longitude
    if "geolocation" in df.columns:
        df[["latitude", "longitude"]] = df["geolocation"].str.split(",", expand=True)
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df

# Page1 Projects
if page == "Projects":
    project_df = load_project_data()

    st.title("Search or Filter Projects")

    st.sidebar.header("Conditions for Filtering Projects")

    # Search input
    search_term = st.sidebar.text_input("ID / Title / Acronym Search: ")

    # Date range
    min_date = project_df["startDate"].min()
    max_date = project_df["endDate"].max()

    start_date, end_date = st.sidebar.date_input(
        "Start date and End date: ",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

#    # Amount range slider
#    min_contribution = float(project_df["ecMaxContribution"].min())
#    max_contribution = float(project_df["ecMaxContribution"].max())
#
#    contrib_range = st.sidebar.slider(
#        "Total Funding Amount (€): ",
#        min_value=min_contribution,
#        max_value=max_contribution,
#        value=(min_contribution, max_contribution)
#    )

    # Add a checkbox to control whether to exclude extreme values
    exclude_outliers = st.sidebar.checkbox("Exclude extreme values (>95%)", value=True)

    # Set range of contributions based on whether to exclude extreme values
    if exclude_outliers:
        min_contribution = project_df["ecMaxContribution"].quantile(0.01)
        max_contribution = project_df["ecMaxContribution"].quantile(0.95)
    else:
        min_contribution = float(project_df["ecMaxContribution"].min())
        max_contribution = float(project_df["ecMaxContribution"].max())

    contrib_range = st.sidebar.slider(
        "Total Funding Amount (€): ",
        min_value=float(min_contribution),
        max_value=float(max_contribution),
        value=(float(min_contribution), float(max_contribution))
    )

    # Clip raw DataFrame to exclude outliers if the checkbox is checked
    if exclude_outliers:
        project_df = project_df[project_df["ecMaxContribution"] <= max_contribution]


    # Apply filters
    filtered_df = project_df.copy()

    if search_term:
        search_term_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df["id"].astype(str).str.contains(search_term_lower, case=False) |
            filtered_df["title"].astype(str).str.contains(search_term_lower, case=False) |
            filtered_df["acronym"].astype(str).str.contains(search_term_lower, case=False)
        ]

    filtered_df = filtered_df[
        (filtered_df["startDate"] >= pd.to_datetime(start_date)) &
        (filtered_df["endDate"] <= pd.to_datetime(end_date)) &
        (filtered_df["ecMaxContribution"] >= contrib_range[0]) &
        (filtered_df["ecMaxContribution"] <= contrib_range[1])
    ]

    st.markdown(f"### Filtered Outcome: {len(filtered_df)} projects")
    st.dataframe(filtered_df, use_container_width=True)

    st.download_button(
        label="Download the outcome as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
        file_name="filtered_projects.csv",
        mime="text/csv"
    )

# Page2 Organizations
elif page == "Organizations":
    org_df = load_org_data()

    st.title("Table and Map of Organizations")

    st.sidebar.header("Conditions for Filtering Organizations")

    search_org = st.sidebar.text_input(" ID / Name Search: ")
    country_filter = st.sidebar.text_input("Country")
    city_filter = st.sidebar.text_input("City")
    postcode_filter = st.sidebar.text_input("Postcode")

    org_filtered = org_df.copy()

    if search_org:
        search_lower = search_org.lower()
        org_filtered = org_filtered[
            org_filtered["organisationID"].astype(str).str.contains(search_lower, case=False) |
            org_filtered["name"].astype(str).str.contains(search_lower, case=False)
        ]

    if country_filter:
        org_filtered = org_filtered[org_filtered["country"].astype(str).str.contains(country_filter, case=False)]
    if city_filter:
        org_filtered = org_filtered[org_filtered["city"].astype(str).str.contains(city_filter, case=False)]
    if postcode_filter:
        org_filtered = org_filtered[org_filtered["postCode"].astype(str).str.contains(postcode_filter, case=False)]

    st.markdown(f"### Filtered Outcome: {len(org_filtered)} organizations")
    st.dataframe(org_filtered, use_container_width=True)

    # Map
    if not org_filtered.empty:
        map_df = org_filtered.dropna(subset=["latitude", "longitude"]).drop_duplicates(subset="organisationID")

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=map_df["latitude"].mean(),
                longitude=map_df["longitude"].mean(),
                zoom=4,
                pitch=0,
            ),
            layers=[
#                pdk.Layer(
#                    'ScatterplotLayer',
#                    data=map_df,
#                    get_position='[longitude, latitude]',
#                    get_radius=500,
#                    get_fill_color='[180, 0, 200, 140]',
#                    pickable=True
#                )
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_df,
                    get_position='[longitude, latitude]',
                    get_radius=10,                        # Base radius in meters
                    radius_scale=100,                    # Scale factor for radius
                    radius_min_pixels=2,                 # Minimum pixel size for radius
                    radius_max_pixels=20,                # Maximum pixel size for radius
                    get_fill_color='[180, 0, 200, 140]',
                    pickable=True
                )
            ],
            tooltip={"text": "{name}\n{city}, {country}"}
        ))

#    if not org_filtered.empty:
#        map_df = org_filtered.dropna(subset=["latitude", "longitude"]).drop_duplicates(subset="organisationID")
#
#        m = folium.Map(
#            location=[map_df["latitude"].mean(), map_df["longitude"].mean()],
#            zoom_start=4,
#            tiles="cartodb positron"
#        )
#
#        marker_cluster = MarkerCluster().add_to(m)
#
#        for _, row in map_df.iterrows():
#            popup_info = f"<b>{row['name']}</b><br>{row.get('city', '')}, {row.get('country', '')}"
#            folium.Marker(
#                location=[row["latitude"], row["longitude"]],
#                popup=popup_info
#            ).add_to(marker_cluster)
#
#        st_folium(m, width=1000, height=600)

# Page3 Predictions of Contributions
elif page == "Predictions of Contributions":
    st.title("Predictions of Contributions")

    # Load the prediction model or pipeline
    model = joblib.load("model.pkl")
    
    # Fill in the option values of funding scheme and country
    funding_options = ['HORIZON-ERC', 'HORIZON-AG', 'ERC', 'HORIZON-CSA', 'HORIZON-RIA', 'HORIZON-EIC', 'EURATOM-COFUND', 'CSA', 'HORIZON-COFUND', 'HORIZON-IA', 'EIC',
                       'HORIZON-TMA-MSCA-PF-EF', 'EURATOM-CSA', 'EURATOM-RIA', 'EURATOM-IA', 'HORIZON-ERC-SYG', 'ERC-SYG', 'RIA', 'IA', 'HORIZON-PCP', 'HORIZON-JU-RIA',
                       'HORIZON-JU-IA', 'HORIZON-JU-CSA', 'HORIZON-EIT-KIC', 'HORIZON-EIC-ACC-BF', 'EIC-ACC']
    country_options = ['ES', 'PL', 'DE', 'FR', 'FI', 'IL', 'NL', 'NO', 'IT', 'SE', 'PT', 'TR', 'CZ', 'AT', 'DK', 'BE', 'IE', 'EL', 'IS', 'LU', 'SI', 'CH', 'RO', 'HU',
                       'EE', 'CY', 'UK', 'LT', 'AL', 'RS', 'ME', 'SK', 'BA', 'FO', 'LV', 'HR', 'MT', 'UA', 'TN', 'GE', 'ZA', 'BG', 'AM', 'KE', 'NG', 'BD', 'AU']

    with st.form("prediction_form"):
        total_cost = st.number_input("Total Cost (€): ", min_value=0.0)
        sme_label = st.radio("Is SME?", ["Yes", "No"])
        sme = 1 if sme_label == "Yes" else 0
        org_count = st.number_input("Number of Organizations: ", min_value=1, max_value=100)
        start_month = st.selectbox("Start Month: ", list(range(1, 13)))
        date_range = st.date_input("Select Start Date & End Date", [date(2025,1,1), date(2025,12,31)])
        
        if len(date_range) == 2:
           start_date, end_date = date_range
           duration_days = (end_date - start_date).days
           st.markdown(f"Duration in days: {duration_days}")
        else:
           duration_days = None
        funding_scheme = st.selectbox("Funding Scheme: ", funding_options)
        country = st.selectbox("Country: ", country_options)
        submit_button = st.form_submit_button("Predict Contribution")

    if submit_button:
        input_df = pd.DataFrame({
            "totalCost": [total_cost],
            "SME": [sme],
            "org_count": [org_count],
            "startmonth": [start_month],
            "duration_days": [duration_days],
            "fundingScheme": [funding_scheme],
            "organiser_country": [country]
        })

        prediction = model.predict(input_df)
        st.success(f"Predicted Contribution Class: {prediction[0].capitalize()}")
