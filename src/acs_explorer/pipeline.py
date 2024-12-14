from acs_explorer import acsexplorer_get_geo_info, acsexplorer_analyze_trends, acsexplorer_generate_report, acsexplorer_visualize_trends, acsexplorer_topic_search

def acsexplorer_pipeline_by_location(
    address,
    variable,
    year_range,
    dataset="acs5",
    output_format="HTML"
):
    """
    Generate a report for a given address by fetching related Census data.

    Parameters:
        address (str): The address to analyze.
        variable (str): The variable name to analyze (e.g., B28002_001E).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (default: 'acs5').
        output_format (str): The output format of the report ("HTML" or "PDF").

    Returns:
        dict: A dictionary containing analysis results, plots, and report paths.
    """
    import os

    results = {}

    # Step 1: Geocoding
    print(f"Step 1: Getting geographic information for address: {address}...")
    geo_info = acsexplorer_get_geo_info(address)
    state = geo_info["state"]
    county = geo_info["county"]
    tract = geo_info["tract"]
    geo_filter = f"state:{state} county:{county} tract:{tract}"
    print(f"Geographic information: {geo_info}")
    results["geo_info"] = geo_info

    # Step 2: Analyze Trends
    print(f"Step 2: Analyzing trends for variable {variable}...")
    trend_data = acsexplorer_analyze_trends(variable, "tract", year_range, dataset)
    results["trend_data"] = trend_data
    if trend_data.empty:
        print(f"No data found for variable {variable} in the specified range.")
    else:
        print(f"Trend analysis completed for variable: {variable}.")

    # Step 3: Visualize Trends
    print(f"Step 3: Visualizing trends for variable: {variable}...")
    plot_path = acsexplorer_visualize_trends(trend_data, variable)
    results["trend_plot"] = plot_path

    # Step 4: Generate Report
    print(f"Step 4: Generating report...")
    report_path = acsexplorer_generate_report(variable, "tract", year_range, dataset, output_format)
    results["report"] = report_path

    print("Pipeline (by location) completed successfully!")
    return results


def acsexplorer_pipeline_by_keyword(
    keyword,
    geography,
    year_range,
    dataset="acs5",
    output_format="HTML"
):
    """
    Generate a report for a given keyword by fetching related Census data.

    Parameters:
        keyword (str): The keyword or theme to search for.
        geography (str): The geographic resolution (state, county, or tract).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (default: 'acs5').
        output_format (str): The output format of the report ("HTML" or "PDF").

    Returns:
        dict: A dictionary containing analysis results, plots, and report paths.
    """
    import os

    results = {}

    # Step 1: Topic Search
    print(f"Step 1: Searching for variables related to '{keyword}'...")
    df, df_shortlist = acsexplorer_topic_search(keyword, include_shortlist=True)
    results["variables"] = df
    results["shortlist"] = df_shortlist
    print(f"Found {len(df)} variables, with {len(df_shortlist)} in the shortlist.")

    # Step 2: Analyze Trends
    print(f"Step 2: Analyzing trends for the first variable in the shortlist...")
    variable = df_shortlist.iloc[0]["Variable Name"]
    trend_data = acsexplorer_analyze_trends(variable, geography, year_range, dataset)
    results["trend_data"] = trend_data
    if trend_data.empty:
        print(f"No data found for variable {variable} in the specified range.")
    else:
        print(f"Trend analysis completed for variable: {variable}.")

    # Step 3: Visualize Trends
    print(f"Step 3: Visualizing trends for variable: {variable}...")
    plot_path = acsexplorer_visualize_trends(trend_data, variable)
    results["trend_plot"] = plot_path

    # Step 4: Generate Report
    print(f"Step 4: Generating report...")
    report_path = acsexplorer_generate_report(keyword, geography, year_range, dataset, output_format)
    results["report"] = report_path

    print("Pipeline (by keyword) completed successfully!")
    return results
