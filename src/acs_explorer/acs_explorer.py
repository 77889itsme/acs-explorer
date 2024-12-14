def acsexplorer_get_geo_info(addresses):
    """
    Get Census geographic information (state, county, tract) using OpenStreetMap Nominatim.

    Parameters:
        address (str): The address to geocode.

    Returns:
        dict: A list of dictionaries containing geo-information.
    """
    import requests

    geo_infos = geocode_address(addresses)
    
    base_url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
    dict_list = []
    for geo_info in geo_infos:
        dict = {}
        lng = geo_info["longitude"]
        lat = geo_info["latitude"]

        params = {
            "x": lng,
            "y": lat,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "format": "json"
        }
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            geographies = data.get("result", {}).get("geographies", {})
            if "Census Tracts" in geographies:
                tract_info = geographies["Census Tracts"][0]
                dict = {"state": tract_info["STATE"],
                    "county": tract_info["COUNTY"],
                    "tract": tract_info["TRACT"],
                    "address": geo_info["display_name"],
                    "lng": lng,
                    "lat": lat
                }
                dict_list.append(dict)
            else:
                raise ValueError("Census tract information not found.")
        else:
            raise ConnectionError(f"Request failed with status code {response.status_code}")
        
    return dict_list

def geocode_address(addresses):
    """
    Geocode an address using OpenStreetMap Nominatim API.

    Parameters:
        address (list): A list of addresses to geocode.

    Returns:
        dict_list: A list of dictionaries containing latitude, longitude, and display name.
    """
    import requests

    if isinstance(addresses, str):
        addresses = [addresses]

    base_url = "https://nominatim.openstreetmap.org/search"
    dict_list = []

    for address in addresses:
        dict = {}
        params = {
            "q": address,
            "format": "json",
            "addressdetails": 1
        }
        headers = {  # OSM requires a header to finish the request.
            "User-Agent": "ACSExplorer (yl5733@columbia.edu)" 
            }
        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0] 
                dict = {
                    "latitude": float(result["lat"]),
                    "longitude": float(result["lon"]),
                    "display_name": result["display_name"],
                    "address": result["address"]
                }
                dict_list.append(dict)
            else:
                raise ValueError("No results found for the provided address.")
        else:
            raise ConnectionError(f"Request failed with status code {response.status_code}")
        
    return dict_list

def acsexplorer_topic_search(keyword, include_shortlist = True):
    """
    Search for variables related to a specific topic using cached Census data.

    Parameters:
        keyword (str): The topic keyword to search for.
        include_shortlist (bool): If True, also return a concise shortlist of searched variables.

    Returns:
        pd.DataFrame: A DataFrame containing relevant variables and metadata.
        pd.DataFrame: A shortlist DataFrame containing concise groups for variables.
    """
    import pandas as pd
    import json
    import os

    cache_api_requests()
    expanded_keywords = expand_keywords(keyword.lower())

    variables = []
    for file_name in os.listdir("cache"):
        if file_name.endswith(".json"):
            file_parts = file_name.replace(".json", "").split("_")
            dataset = file_parts[1] 
            year = int(file_parts[2]) 
            with open(os.path.join("cache", file_name), "r") as f:
                for var_name, var_data in json.load(f).items():
                    variables.append((var_name, var_data, {"dataset": dataset, "year": year}))
                
    # Filter variables based on keyword matches
    results = []
    for var_name, var_data, var_data_info in variables:
        var_description = var_data.get("label", "")
        var_group = var_data.get("group","")
        tokens = clean_text(var_description).split()
        if any(word in tokens for word in expanded_keywords):
            results.append({
                "Variable Name": var_name,
                "Group": var_group,
                "Description": var_description,
                "Dataset": var_data_info.get("dataset"),
                "Year": var_data_info.get("year")
            })

    if results:
        df = pd.DataFrame(results)
        df = process_df(df, keyword.lower())
        if include_shortlist:
            df_shortlist = topic_search_shortlist(df)
            df_group = get_variable_groups(df_shortlist)

            #merging data
            df_shortlist = pd.merge(df_shortlist, df_group, on="Group", how="left")
            cols_s = ["Concept"] + [col for col in df_shortlist.columns if col != "Concept"]
            df_shortlist = df_shortlist[cols_s]

            df = pd.merge(df, df_group, on="Group", how="left")
            cols = ["Concept"] + [col for col in df.columns if col != "Concept"]
            df = df[cols]

            return df, df_shortlist
        else:
            return df
    else:
        print("No matching variables found.")
        return pd.DataFrame()

def acsexplorer_topic_search_shortlist(keyword):
    """
    Returns only shortlist.

    Parameters:
        keyword (str): The topic keyword to search for.

    Returns:
        pd.DataFrame: A shortlist grouped by variable prefixes, showing aggregated metadata.
    """
    df, df_shortlist = acsexplorer_topic_search(keyword, include_shortlist = True)
    return df_shortlist

def topic_search_shortlist(df):
    """
    Create a more concise shortlist by grouping variables based on their prefix (before the underscore).

    Parameters:
        pd.DataFrame: The longlist dataframe.

    Returns:
        pd.DataFrame: A shortlist grouped by variable prefixes, showing aggregated metadata.
    """
    import pandas as pd

    # Group by the prefix and aggregate information
    grouped = df.groupby('Group').agg({
        'Variable Name': lambda x: list(x),  # Collect all variable names under the prefix
        'Dataset': lambda x: list(set(sum(x, []))),  # Flatten and deduplicate datasets
        'Year': lambda x: list(sorted(set(sum(x, []))))  # Flatten, deduplicate, and sort years
    }).reset_index()

    return grouped

def get_variable_groups(df):
    """
    Retrieve the first 'concept' for each variable group from the Census API.

    Parameters:
        df_shortlist (pd.DataFrame): A DataFrame containing grouped variables with the 'Group' column.

    Returns:
        pd.DataFrame: A DataFrame with group names and their corresponding concepts.
    """
    import pandas as pd
    import requests

    results = []
    dataset = "acs/acs1"
    groups = df["Group"].unique()

    for group in groups:
        year_list = df[df['Group'] == group]['Year'].values[0]
        year = year_list[-1]
        base_url = f"https://api.census.gov/data/{year}/{dataset}/groups/{group}.json"

        response = requests.get(base_url)
        if response.status_code == 200:
            data = response.json()
            variables = data.get("variables", {})
            
            # Find the first valid variable
            for var_name, var_info in variables.items():
                if var_name == "NAME":  # Explicitly skip 'NAME'
                    continue
                if var_name == "GEO_ID":
                    continue
                concept = var_info.get("concept", "Unknown Concept")
                results.append({"Group": group, "Concept": concept})
                break  # Stop after finding the first valid variable
        else:
            print(f"Request failed for group {group} with status code {response.status_code}")
    
    results_df = pd.DataFrame(results)
    return results_df

def clean_text(text):
    """
    Clean the text by replacing special characters with spaces and turn into lowercase.

    Parameters:
        text (str): The input text to clean and tokenize.

    Returns:
        str: Cleaned text.
    """
    import re
    text_out = re.sub(r"[^\w\s]", " ", text).lower()
    return text_out

def expand_keywords(keyword):
    """
    Expand a single keyword into a list of related words using nltk.

    Parameters:
        keyword (str): The input keyword.

    Returns:
        list: A list of related terms including the original keyword.
    """
    import nltk
    from nltk.corpus import wordnet
    nltk.download('wordnet', quiet=True)
    keyword = keyword.lower()
    synonyms = set()
    for syn in wordnet.synsets(keyword):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().lower().replace("_", " "))
    synonyms = list(synonyms)[:3]
    if keyword not in synonyms:
        synonyms.insert(0, keyword)
    return synonyms

def cache_api_requests(cache_dir="cache"):
    """
    Download and cache variables from Census API for specified datasets and years.

    Parameters:
        cache_dir (str): Directory to store cached JSON responses.

    Returns:
        None
    """
    import os
    import json
    import requests

    datasets = {
        "acs/acs1": range(2005, 2024),  # ACS1 available 2005-2023
        "acs/acs5": range(2009, 2024),  # ACS5 available 2009-2023
    }

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    for dataset, years in datasets.items():
        for year in years:
            cache_file = os.path.join(cache_dir, f"{dataset.replace('/', '_')}_{year}.json")

            if os.path.exists(cache_file):            # Skip if file is already cached
                continue

            # Fetch data from API
            base_url = f"https://api.census.gov/data/{year}/{dataset}/variables.json"
            response = requests.get(base_url)

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Save to cache
                    with open(cache_file, "w") as f:
                        json.dump(data["variables"], f)
                    print(f"Downloaded and cached: {dataset}, {year}")
                except ValueError as e:
                    print(f"Error decoding JSON for {dataset}, {year}: {e}")
            else:
                print(f"Request failed for {dataset}, {year} with status code {response.status_code}")

def process_df(df, keyword):
    """
    Process the raw census data to merge by Variable Name, clean descriptions,
    and aggregate dataset and year information using Regex.

    Parameters:
        df (pd.DataFrame): The raw dataset.
        keyword (str): The keyword to prioritize the results by relevance.

    Returns:
        pd.DataFrame: Processed DataFrame with cleaned and aggregated information.
    """
    import re

    def description_cleaned(desc):
        cleaned = re.sub(r"estimate!!", "", desc, flags=re.IGNORECASE)
        cleaned = re.sub(r"Total","", cleaned)
        cleaned = re.sub(r"!!", ": ", cleaned)
        return cleaned.strip(": ")

    df['Description'] = df['Description'].apply(description_cleaned)

    grouped = df.groupby('Variable Name').agg({
        "Group": 'first',
        'Description': 'first',  
        'Dataset': lambda x: list(sorted(set(x))),  
        'Year': lambda x: list(sorted(set(x)))  # Aggregate unique years into a list
    }).reset_index()

    grouped['Exact Match'] = grouped['Description'].apply(lambda desc: int(keyword in desc.lower()))
    grouped = grouped.sort_values(by=['Exact Match', 'Variable Name'], ascending=[False, True])
    grouped = grouped.drop(columns=['Exact Match'])

    return grouped

def acsexplorer_get_data(variables, geography, year, dataset, geo_filter=None):
    """
    Retrieve data for specified geography and variables from the Census API.

    Parameters:
        variables (list): List of variable names to fetch data for.
        geography (str): Geographic level (e.g., "state", "county", "tract").
        year (int): Data year.
        dataset (str): Dataset name (e.g., "acs/acs5").
        geo_filter (dict, optional): Additional geographic filters (e.g., {"state": "06"}).

    Returns:
        pd.DataFrame: A DataFrame containing the requested data.
    """
    import pandas as pd
    import requests
    from urllib.parse import urlencode

    if isinstance(variables, str):
        variables = [variables]

    if geography not in ["state", "county", "tract"]:
        raise ValueError(f"Invalid geography: '{geography}'. Must be one of 'state', 'county' or 'tract'.")
    
    params = {
        "get": ",".join(["NAME"] + variables)
    }

    if geography == "state":
        if geo_filter and "state" in geo_filter:
            params["for"] = f"state:{geo_filter['state']}"
        else:
            params["for"] = "state:*"

    elif geography == "county":
        if geo_filter and "state" in geo_filter and "county" in geo_filter:
            params["for"] = f"county:{geo_filter['county']}"
            params["in"] = f"state:{geo_filter['state']}"
        elif geo_filter and "state" in geo_filter:
            params["for"] = "county:*"
            params["in"] = f"state:{geo_filter['state']}"
        else:
            params["for"] = "county:*"

    elif geography == "tract":
        if dataset == "acs1":
            raise ValueError("Census tract level data is not available in 1-year estimates (acs1). Please use ACS5.")
        if not geo_filter or "state" not in geo_filter:
            raise ValueError("When geography is 'tract', 'geo_filter' must include 'state' key.")
        if "county" in geo_filter and "tract" in geo_filter:
            params["for"] = f"tract:{geo_filter['tract']}"
            params["in"] = f"state:{geo_filter['state']} county:{geo_filter['county']}"
        elif "county" in geo_filter:
            params["for"] = "tract:*"
            params["in"] = f"state:{geo_filter['state']} county:{geo_filter['county']}"
        else:
            params["for"] = "tract:*"
            params["in"] = f"state:{geo_filter['state']}"
            
    base_url = f"https://api.census.gov/data/{year}/acs/{dataset}"
    query = urlencode(params, safe=":*")  # safe 参数确保 `*` 不被转义
    url = f"{base_url}?{query}"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = response.json()
            columns = data[0]
            values = data[1:]
            df = pd.DataFrame(values, columns=columns)
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to parse API response: {e}")
    else:
        raise RuntimeError(f"Request failed with status code {response.status_code}: {response.text}")

def acsexplorer_analyze_trends(variables, geography, year_range, dataset, geo_filter={}):
    """
    Analyze trends for a specific variable across a range of years.

    Parameters:
        variables (str): A  list of variables to analyze.
        geography (str): Geographic level (e.g., "state").
        year_range (tuple): A tuple specifying the range of years (start, end).
        dataset (str): The dataset name (e.g., "acs5").
        geo_filter (dict, optional): Geographic filter (e.g., {"state": "16", "county": "001"}).

    Returns:
        pd.DataFrame: A DataFrame containing the trend data across years.
    """
    import pandas as pd

    results = []
    for year in range(year_range[0], year_range[1] + 1):
        try:
            data = acsexplorer_get_data(variables, geography, year, dataset, geo_filter)
            data["Year"] = year  # Add year column for trend analysis
            results.append(data)
        except Exception as e:
            print(f"Failed to fetch data for variables {variables} in year {year}: {e}")

    if results:
        trend_data = pd.concat(results, ignore_index=True)
        return trend_data
    else:
        print("No data available for the specified range.")
        return pd.DataFrame()

def visualize_trends(trend_data, variable, output_path="trend_plot.html"):
    """
    Visualize the trend for a given variable over time.

    Parameters:
        trend_data (pd.DataFrame): The DataFrame containing trend data.
        variable (str): The name of the variable being visualized.
        output_path (str): The file path to save the plot.

    Returns:
        str: The file path of the saved plot.
    """
    import plotly.graph_objects as go

    if trend_data.empty:
        print("No data to visualize.")
        return None

    # Check if the variable exists in the DataFrame
    if variable not in trend_data.columns:
        raise ValueError(f"Variable '{variable}' not found in the trend data.")

    # Group and aggregate data by year
    trend_data[variable] = pd.to_numeric(trend_data[variable], errors="coerce")
    yearly_data = trend_data.groupby("Year")[variable].sum().reset_index()

    # Plot the trend
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=yearly_data["Year"],
        y=yearly_data[variable],
        mode="markers+lines",  # Markers and dotted lines
        line=dict(dash="dot", color="blue", width=2),
        marker=dict(size=10, color="blue"),
        name=variable
    ))

    fig.update_layout(
        title=f"Trend Analysis for {variable}",
        xaxis_title="Year",
        yaxis_title="Value",
        template="plotly_white",
        xaxis=dict(tickmode="linear", tick0=yearly_data["Year"].min(), dtick=1),
        font=dict(size=14),
        showlegend=True,
    )

    fig.write_html(output_path)
    print(f"Interactive plot saved to {output_path}")

    return fig

def acsexplorer_generate_report(variables, geography, year_range, dataset, geo_filter=None, output_path="reports/report.html"):
    """
    Generate a comprehensive report for specified variables, geography, and year range.

    Parameters:
        variables (list): A list of variable names to analyze.
        geography (str): The geographic resolution (state, county, or tract).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (e.g., 'acs1' or 'acs5').
        output_path (str): The file path for the generated report.
        geo_filter (dict, optional): Additional geographic filters (e.g., {"state": "16"}).

    Returns:
        str: The file path of the generated report.
    """
    import pandas as pd
    import os
    from plotly.io import to_html

    report_dir = os.path.dirname(output_path)
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    with open(output_path, "w") as report_file:
        report_file.write(f"<h1>Comprehensive Report</h1>\n")

        # Step 1: Analyze trends
        report_file.write("<h2>Trend Analysis</h2>\n")
        trend_data = acsexplorer_analyze_trends(variables, geography, year_range, dataset, geo_filter)
        if trend_data.empty:
            report_file.write("<p>No trend data available for the specified range.</p>\n")
        else:
            report_file.write("<p>Trend data for the selected variables:</p>\n")
            report_file.write(trend_data.to_html(index=False))
            for variable in variables:
                if variable in trend_data.columns:
                    output_plot_path = f"{os.path.splitext(output_path)[0]}_{variable}_plot.png"
                    fig = visualize_trends(trend_data, variable, output_plot_path)
                    plot_html = to_html(fig, full_html=False)
                    report_file.write(f"<h3>Trend Visualization for {variable}</h3>\n")
                    report_file.write(plot_html)
                else:
                    report_file.write(f"<h3>Trend Visualization for {variable}</h3>\n")
                    report_file.write("<p>No data available for this variable.</p>\n")

    print(f"Report generated at {output_path}")
    return output_path

def acsexplorer_pipeline_by_location(addresses, geography, variables, year_range, dataset, output_path="reports"):
    """
    Generate a report for a given address by fetching related Census data.

    Parameters:
        addresses (list): The address to analyze.
        variables (list): The list of variable names to analyze (e.g., [B28002_001E]).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (default: 'acs5').
        output_path (str): The file path for the generated report.

    Returns:
        DataFrame: A df containing the ACS variable informations by year and address.
    """
    import os

    print(f"Step 1: Getting geographic information for addresses: {addresses}...")
    geo_info_list = acsexplorer_get_geo_info(addresses)
    combined_trend_data = []

    for geo_info in geo_info_list:
        state = str(geo_info["state"])
        county = str(geo_info["county"])
        tract = str(geo_info["tract"])

        geo_filter = {"state": state, "county": county, "tract": tract}
        print(f"Geographic information: {geo_info}")

        # Step 2: Analyze Trends
        print(f"Step 2: Analyzing trends for variable {variables}...")
        trend_data = acsexplorer_analyze_trends(variables, geography, year_range, dataset, geo_filter)
        if not trend_data.empty:
            trend_data["Address"] = geo_info["address"]  # Add the address for comparison
            combined_trend_data.append(trend_data)
    
    if combined_trend_data:
        all_trends = pd.concat(combined_trend_data, ignore_index=True)
        print(f"Step 3: Combined trend data for all addresses:")

        csv_path = os.path.join(output_path, "data.csv")
        all_trends.to_csv(csv_path, index=False)
        print(f"Data saved to {csv_path}")

        return all_trends
    else:
        print("No trend data available for any of the addresses.")
        return None

def acsexplorer_pipeline_by_keyword(keyword, geography, year_range, dataset, top_search, output_path="reports"):
    """
    Pipeline to search by keyword, analyze trends, and save results to a CSV file.

    Parameters:
        keyword (str): The keyword to search for.
        geography (str): The geographic resolution (state, county, tract).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (default: 'acs5').
        output_path (str): The output directory for saving the CSV file.

    Returns:
        str: The path to the saved CSV file.
    """
    import os
    import pandas as pd

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    csv_path = os.path.join(output_path, "data.csv")

    print(f"Step 1: Searching for variables related to '{keyword}'...")
    df, df_shortlist = acsexplorer_topic_search(keyword, include_shortlist=True)

    if df.empty:
        print("No matching variables found.")
        return None
    
    variable_groups = df_shortlist["Group"].unique()[:top_search]
    variables = df[df["Group"].isin(variable_groups)]["Variable Name"].unique()

    if not variables.any():
        print("No variables found for trend analysis.")
        return None

    # Step 2: Analyze trends
    print("Step 2: Analyzing trends for the selected variables...")
    all_trends = []

    for variable in variables:
        print(f"Analyzing trends for variable: {variable}")
        try:
            trend_data = acsexplorer_analyze_trends(variable, geography, year_range, dataset)
            trend_data = trend_data.melt(
                id_vars=["NAME", "state", "Year"],
                var_name="Variable Name",
                value_name="Value")
            trend_data = trend_data[trend_data["Variable Name"] == variable]
            all_trends.append(trend_data)
        except Exception as e:
            print(f"Failed to analyze trends for variable {variable}: {e}")

    # Combine all trend data into a single DataFrame
    if all_trends:
        combined_df = all_trends[0]
        for df in all_trends[1:]:
            combined_df = pd.merge(combined_df, df, on=["NAME", "state", "Year"], how="outer")
        combined_df = pd.concat(all_trends, ignore_index=True)

        combined_df.to_csv(csv_path, index=False)
        print(f"Data saved to {csv_path}")
        
        return combined_df
    else:
        print("No trend data available for the specified keyword and range.")
        return None