import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(page_title="Project and Organization Dashboard", layout="wide")

# ----------- Pages -----------
page = st.sidebar.radio("Options: ", ["Project", "Organization Table and Map"])

# ----------- Load data -----------
@st.cache_data

def load_project_data():
    df = pd.read_excel("project.xlsx")
    df["startDate"] = pd.to_datetime(df["startDate"], errors='coerce')
    df["endDate"] = pd.to_datetime(df["endDate"], errors='coerce')
    df["ecMaxContribution"] = (
        df["ecMaxContribution"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    df["ecMaxContribution"] = pd.to_numeric(df["ecMaxContribution"], errors="coerce")
    return df

@st.cache_data

def load_org_data():
    df = pd.read_excel("organization.xlsx")
    if "geolocation" in df.columns:
        df[["latitude", "longitude"]] = df["geolocation"].str.split(",", expand=True)
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df

# Page one: Project
if page == "Project":
    project_df = load_project_data()

    st.title("Project search and filtering")

    st.sidebar.header("Filtering options")

    search_term = st.sidebar.text_input("id / title / acronym search: ")

    min_date = project_df["startDate"].min()
    max_date = project_df["endDate"].max()

    start_date, end_date = st.sidebar.date_input(
        "Start date - End date",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

#    min_contribution = float(project_df["ecMaxContribution"].min())
#    max_contribution = float(project_df["ecMaxContribution"].max())
#
#    contrib_range = st.sidebar.slider(
#        "Total Funding Amount (€): ",
#        min_value=min_contribution,
#        max_value=max_contribution,
#        value=(min_contribution, max_contribution)
#    )

    # 添加复选框来控制是否排除极端值
    exclude_outliers = st.sidebar.checkbox("排除极端值（> 95% 分位）", value=True)

    # 设置金额范围
    if exclude_outliers:
        # 取 1% ~ 95% 之间的金额，排除极端值
        min_contribution = project_df["ecMaxContribution"].quantile(0.01)
        max_contribution = project_df["ecMaxContribution"].quantile(0.95)
    else:
        min_contribution = float(project_df["ecMaxContribution"].min())
        max_contribution = float(project_df["ecMaxContribution"].max())

    # 使用干净范围构造滑动条
    contrib_range = st.sidebar.slider(
        "投资总金额范围 (€)：",
        min_value=float(min_contribution),
        max_value=float(max_contribution),
        value=(float(min_contribution), float(max_contribution))
    )

    # ✅ 如果用户排除极端值，还需要过滤原始数据
    if exclude_outliers:
        project_df = project_df[
            project_df["ecMaxContribution"] <= max_contribution
        ]


    st.write(f"📊 原始总项目数：{len(project_df)}")

    filtered_df = project_df.copy()

    if search_term:
        search_term_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df["id"].astype(str).str.contains(search_term_lower, case=False) |
            filtered_df["title"].astype(str).str.contains(search_term_lower, case=False) |
            filtered_df["acronym"].astype(str).str.contains(search_term_lower, case=False)
        ]

    st.write(f"🔍 步骤 1：关键词搜索后项目数：{len(filtered_df)}")


#    filtered_df = filtered_df[
#        (filtered_df["startDate"] >= pd.to_datetime(start_date)) &
#        (filtered_df["endDate"] <= pd.to_datetime(end_date)) &
#        (filtered_df["ecMaxContribution"] >= contrib_range[0]) &
#        (filtered_df["ecMaxContribution"] <= contrib_range[1])
#    ]

    # 时间筛选
    before_time_filter = len(filtered_df)
    filtered_df = filtered_df[
        (filtered_df["startDate"] >= pd.to_datetime(start_date)) &
        (filtered_df["endDate"] <= pd.to_datetime(end_date))
    ]
    st.write(f"🔍 步骤 2：时间范围筛选后项目数：{len(filtered_df)}（减少了 {before_time_filter - len(filtered_df)}）")

    # 金额筛选
    before_money_filter = len(filtered_df)
    filtered_df = filtered_df[
        (filtered_df["ecMaxContribution"] >= contrib_range[0]) &
        (filtered_df["ecMaxContribution"] <= contrib_range[1])
    ]
    st.write(f"🔍 步骤 3：金额筛选后项目数：{len(filtered_df)}（减少了 {before_money_filter - len(filtered_df)}）")


    st.write(f"🔍 筛选后剩余项目数：{len(filtered_df)}")

    st.markdown(f"### Filting outcome: {len(filtered_df)} projects")
    st.dataframe(filtered_df, use_container_width=True)

    st.download_button(
        label="Download filtered data as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
        file_name="filtered_projects.csv",
        mime="text/csv"
    )

# Page two: Organization
elif page == "Organization Table and Map":
    org_df = load_org_data()

    st.title("Organization search and filtering")

    st.sidebar.header("Filtering options")

    search_org = st.sidebar.text_input("ID / name search: ")
    country_filter = st.sidebar.text_input("country")
    city_filter = st.sidebar.text_input("city")
    postcode_filter = st.sidebar.text_input("postcode")

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

    st.markdown(f"### Found {len(org_filtered)} organizations")
    st.dataframe(org_filtered, use_container_width=True)

#    map_df = org_filtered.dropna(subset=["latitude", "longitude"])

    map_df = (
        org_filtered
        .dropna(subset=["latitude", "longitude"])
        .drop_duplicates(subset="organisationID")
    )


    if not map_df.empty:
        m = folium.Map(location=[map_df["latitude"].mean(), map_df["longitude"].mean()], zoom_start=4)
        marker_cluster = MarkerCluster().add_to(m)

        for idx, row in map_df.iterrows():
            popup_info = f"<b>{row['name']}</b><br>{row.get('city', '')}, {row.get('country', '')}".strip()
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=popup_info
            ).add_to(marker_cluster)

#        st_folium(m, width=1000, height=600)
        map_data = st_folium(m, width=1000, height=600, returned_objects=["bounds"])

        if map_data and "bounds" in map_data:
            bounds = map_data["bounds"]
            sw = bounds["_southWest"]
            ne = bounds["_northEast"]

            map_df = map_df[
                (map_df["latitude"] >= sw["lat"]) &
                (map_df["latitude"] <= ne["lat"]) &
                (map_df["longitude"] >= sw["lng"]) &
                (map_df["longitude"] <= ne["lng"])
            ]
            st.caption(f"Organizations within the selected map bounds: {len(map_df)}")
        else:
            st.warning("No boundaries loaded, please drag or zoom the map to view!")