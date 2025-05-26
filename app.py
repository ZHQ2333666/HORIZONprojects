import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime

st.set_page_config(page_title="项目与机构查询面板", layout="wide")

# ----------- 页面控制 -----------
page = st.sidebar.radio("选择页面：", ["项目查询", "机构地图"])

# ----------- 加载数据 -----------
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
    # 拆分 geolocation 列为 latitude 和 longitude
    if "geolocation" in df.columns:
        df[["latitude", "longitude"]] = df["geolocation"].str.split(",", expand=True)
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df

# 页面一：项目查询
if page == "项目查询":
    project_df = load_project_data()

    st.title("项目查询与筛选")

    st.sidebar.header("项目筛选条件")

    # 搜索
    search_term = st.sidebar.text_input("按项目 ID / 名称 / 缩写 搜索：")

    # 时间范围选择
    min_date = project_df["startDate"].min()
    max_date = project_df["endDate"].max()

    start_date, end_date = st.sidebar.date_input(
        "选择项目开始-结束时间范围：",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # 金额筛选
    min_contribution = float(project_df["ecMaxContribution"].min())
    max_contribution = float(project_df["ecMaxContribution"].max())

    contrib_range = st.sidebar.slider(
        "投资总金额范围 (€)：",
        min_value=min_contribution,
        max_value=max_contribution,
        value=(min_contribution, max_contribution)
    )

    # 应用筛选条件
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

    st.markdown(f"### 筛选结果：共 {len(filtered_df)} 个项目")
    st.dataframe(filtered_df, use_container_width=True)

    st.download_button(
        label="下载筛选结果为 CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
        file_name="filtered_projects.csv",
        mime="text/csv"
    )

# 页面二：机构地图
elif page == "机构地图":
    org_df = load_org_data()

    st.title("欧洲机构查询与地图展示")

    st.sidebar.header("机构筛选条件")

    search_org = st.sidebar.text_input("按机构 ID / 名称 搜索：")
    country_filter = st.sidebar.text_input("国家（country）")
    city_filter = st.sidebar.text_input("城市（city）")
    postcode_filter = st.sidebar.text_input("邮政编码（postCode）")

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

    st.markdown(f"### 匹配到 {len(org_filtered)} 个机构")
    st.dataframe(org_filtered, use_container_width=True)

    # 地图展示
    if not org_filtered.empty:
        map_df = org_filtered.dropna(subset=["latitude", "longitude"])

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=map_df["latitude"].mean(),
                longitude=map_df["longitude"].mean(),
                zoom=4,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    'ScatterplotLayer',
                    data=map_df,
                    get_position='[longitude, latitude]',
                    get_radius=10000,
                    get_fill_color='[180, 0, 200, 140]',
                    pickable=True
                )
            ],
            tooltip={"text": "{name}\n{city}, {country}"}
        ))