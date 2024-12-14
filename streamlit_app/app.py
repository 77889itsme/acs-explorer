import streamlit as st
import pandas as pd
from acs_explorer import (
    acsexplorer_get_geo_info,
    acsexplorer_pipeline_by_location,
    acsexplorer_pipeline_by_keyword,
    acsexplorer_topic_search,
    query_census_data
)
import plotly.express as px
import plotly.graph_objects as go

# App Title
st.title("ACS Explorer")

# Navigation Sidebar
st.sidebar.header("Navigation")
pages = ["Geographic Lookup", "Search Variables", "Pipelines"]
selected_page = st.sidebar.radio("Select a Page", pages)

# Page 1: Geographic Lookup
if selected_page == "Geographic Lookup":
    st.header("Geographic Lookup")
    address = st.text_input("Enter an Address", "535 West 116th Street, New York")
    if st.button("Get Geo Info"):
        geo_info = acsexplorer_get_geo_info(address)
        st.write("Geographic Information:")
        st.json(geo_info)
        # Plot the location on a map
        if geo_info:
            for each in geo_info:
                lat, lng = each["lat"], each["lng"]
                fig = go.Figure(go.Scattermapbox(
                    lat=[lat],
                    lon=[lng],
                    mode="markers",
                    marker=go.scattermapbox.Marker(size=14),
                    text=[address]
                ))
                fig.update_layout(
                    mapbox_style="carto-positron",
                    mapbox_zoom=8,
                    mapbox_center={"lat": lat, "lon": lng},
                    height=700
                )
                st.plotly_chart(fig)

# Page 2: Search Variables
if selected_page == "Search Variables":
    st.header("Search Variables")
    keyword = st.text_input("Enter a keyword for variable search", "internet")
    if st.button("Search"):
        df, df_shortlist = acsexplorer_topic_search(keyword, include_shortlist=True)
        st.session_state["df"] = df  # Store the full search results
        st.session_state["df_shortlist"] = df_shortlist  # Store the shortlist

    if "df" in st.session_state and "df_shortlist" in st.session_state:
        df = st.session_state["df"]
        df_shortlist = st.session_state["df_shortlist"]

        # Display the shortlist
        st.write("Shortlist of Variable Groups:")
        st.dataframe(df_shortlist[["Concept", "Group", "Variable Name"]])
        selected_group = st.selectbox(
            "Select a variable group from shortlist to highlight",
            options=df_shortlist["Group"],
            help="Choose a variable group to see where it appears in the full search results."
        )

        if selected_group:
            df["checked"] = df["Group"].apply(
                lambda x: "✅" if x == selected_group else ""
            )
            highlighted_columns = ["checked"] + [col for col in df.columns if col != "checked"]
            st.write("Search Results (Highlighted):")
            st.dataframe(df[highlighted_columns])
    else:
        st.caption("Perform a search to see results.")



# Page 3: Pipelines
if selected_page == "Pipelines":
    st.header("Run Pipelines")
    pipeline_type = st.radio("Choose a Pipeline", ["By Location", "By Search"])

    if pipeline_type == "By Location":
        st.subheader("Pipeline: By Location")
        address = st.text_input("Enter an Address", "535 West 116th Street, New York")
        geography = st.selectbox("Geographic Level", ["state", "county", "tract"])
        variable = st.text_input("Enter Variable Name", "B28002_001E")
        start_year = st.number_input("Start Year", min_value=2005, max_value=2023, value=2017)
        end_year = st.number_input("End Year", min_value=2005, max_value=2023, value=2021)
        dataset = st.selectbox("Dataset", ["acs1", "acs5"])
        if st.button("Run Location Pipeline"):
            query_result = query_census_data(variable, start_year, dataset)
            concept = query_result.get("concept", "")
            st.write(f"**{variable}**: {concept.title()}")

            results = acsexplorer_pipeline_by_location(address, geography, variable, (start_year, end_year), dataset)
            
            st.success("Pipeline Completed!")
            st.write("Pipeline Results:")
            st.dataframe(results)
            fig = px.line(
                results,
                x="Year",  
                y= variable,  
                title= "Population Trends for New York",
                labels={variable: "Population", "Year": "Year"},
                markers=True 
            )
            st.plotly_chart(fig)

    elif pipeline_type == "By Search":
        st.subheader("Pipeline: By Search")
        keyword = st.text_input("Enter a Keyword", "internet")
        geography = st.selectbox("Geographic Level", ["state", "county", "tract"])
        start_year = st.number_input("Start Year", min_value=2005, max_value=2023, value=2015)
        end_year = st.number_input("End Year", min_value=2005, max_value=2023, value=2020)
        dataset = st.selectbox("Dataset", ["acs1", "acs5"])
        output_path = st.text_input("Report File Name", "search_pipeline_report.html")
        if st.button("Run Search Pipeline"):
            results = acsexplorer_pipeline_by_keyword(keyword, geography, (start_year, end_year), dataset, output_path)
            st.success("Pipeline Completed!")
            st.write("Pipeline Results:")
            st.json(results)
