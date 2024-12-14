def acsexplorer_get_geo_info(address):
    """
    Get Census geographic information (state, county, tract) using OpenStreetMap Nominatim.

    Parameters:
        address (str): The address to geocode.

    Returns:
        dict: A dictionary containing state, county, and tract information.
    """
    import requests

    geo_info = geocode_address(address)
    lng = geo_info["longitude"]
    lat = geo_info["latitude"]

    base_url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
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
            return {
                "state": tract_info["STATE"],
                "county": tract_info["COUNTY"],
                "tract": tract_info["TRACT"],
                "display_name": geo_info["display_name"]
            }
        else:
            raise ValueError("Census tract information not found.")
    else:
        raise ConnectionError(f"Request failed with status code {response.status_code}")


def geocode_address(address):
    """
    Geocode an address using OpenStreetMap Nominatim API.

    Parameters:
        address (str): The address to geocode.

    Returns:
        dict: A dictionary containing latitude, longitude, and display name.
    """
    import requests

    base_url = "https://nominatim.openstreetmap.org/search"
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
            return dict
        else:
            raise ValueError("No results found for the provided address.")
    else:
        raise ConnectionError(f"Request failed with status code {response.status_code}")


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
    
    if geography not in ["state", "county", "tract"]:
        raise ValueError(f"Invalid geography: '{geography}'. Must be one of 'state', 'county' or 'tract'.")


    # Special handling for census tracts
    if geography == "tract":
        df = acsexplorer_get_data_tract(variables, year, dataset, geo_filter)

    # General cases for other geographies
    else:
        params = {
            "get": ",".join(["NAME"] + variables),
            "for": f"{geography}:*"
        }
        if geo_filter:
            params.update({f"in={key}": value for key, value in geo_filter.items()})
        
        base_url = f"https://api.census.gov/data/{year}/{dataset}"
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")
        columns = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=columns)
    
    return df



def acsexplorer_get_data_tract(variables, year, dataset, geo_filter):
    import requests
    import pandas as pd

    if not geo_filter or "state" not in geo_filter:
        raise ValueError("When geography is 'tract', geo_filter must at least include 'state'.")

    tract = geo_filter.get("tract", "*")
    county = geo_filter.get("county", None)
    state = geo_filter["state"]

    if tract != "*":
        if not county:
            raise ValueError("When querying a specific tract, 'county' must be provided in geo_filter.")
        for_param = f"tract:{tract}"
        in_param = f"state:{state} county:{county}"
    elif county:
        for_param = "tract:*"
        in_param = f"state:{state}&in=county:{county}"
    else:
        for_param = "tract:*"
        in_param = f"state:{state}"

    params = {
        "get": ",".join(["NAME"] + variables),
        "for": for_param,
        "in": in_param
    }
    
    base_url = f"https://api.census.gov/data/{year}/{dataset}"
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
    else:
        raise Exception(f"Request failed with status code {response.status_code}")
    
    columns = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=columns)

    return df  


def acsexplorer_analyze_trends(variable, geography, year_range, dataset):
    """
    Analyze trends for a given variable over a range of years.

    Parameters:
        variable (str): The variable name to analyze.
        geography (str): The geographic resolution (state, county, or tract).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (e.g., 'acs1' or 'acs5').

    Returns:
        pd.DataFrame: A DataFrame containing yearly aggregated data for the variable.
    """
    import pandas as pd

    data = []

    for year in range(year_range[0], year_range[1] + 1):
        try:
            df_data = acsexplorer_get_data(variable, geography, year, dataset)
            df_data["Year"] = year
            data.append(df_data)
        except Exception as e:
            print(f"Failed to fetch data for {variable} in {year}: {e}")

    # Combine all yearly data
    if data:
        trend_data = pd.concat(data, ignore_index=True)
        return trend_data
    else:
        print("No data available for the specified range.")
        return pd.DataFrame()


def acsexplorer_visualize_trends(trend_data, variable, output_path="trend_plot.png"):
    """
    Visualize the trend for a given variable over time.

    Parameters:
        trend_data (pd.DataFrame): The DataFrame containing trend data.
        variable (str): The name of the variable being visualized.
        output_path (str): The file path to save the plot.

    Returns:
        str: The file path of the saved plot.
    """
    import matplotlib.pyplot as plt

    if trend_data.empty:
        print("No data to visualize.")
        return None

    # Group and aggregate data by year
    yearly_data = trend_data.groupby("Year").sum()["value"].reset_index()

    # Plot the trend
    plt.figure(figsize=(10, 6))
    plt.plot(yearly_data["Year"], yearly_data["value"], marker="o", label=variable)
    plt.title(f"Trend Analysis for {variable}")
    plt.xlabel("Year")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot
    plt.savefig(output_path)
    plt.close()

    print(f"Plot saved to {output_path}")
    return output_path


def acsexplorer_generate_report(keyword, geography, year_range, dataset, output_format="HTML"):
    """
    Generate a comprehensive report for a given keyword and time range.

    Parameters:
        keyword (str): The keyword to search for.
        geography (str): The geographic resolution (state, county, or tract).
        year_range (tuple): The range of years (start_year, end_year).
        dataset (str): The dataset name (e.g., 'acs1' or 'acs5').
        output_format (str): The format of the output report ("HTML" or "PDF").

    Returns:
        str: The path to the generated report.
    """
    import pandas as pd

    # Step 1: Search for variables
    df, _ = acsexplorer_topic_search(keyword)
    print(f"Found {len(df)} variables related to '{keyword}'")

    # Step 2: Analyze trends and generate plots for the first variable
    variable = df.iloc[0]["Variable Name"]
    trend_data = acsexplorer_analyze_trends(variable, geography, year_range, dataset)
    plot_path = acsexplorer_visualize_trends(trend_data, variable)

    # Step 3: Generate a simple HTML report
    report_content = f"""
    <h1>ACS Explorer Report</h1>
    <p><strong>Keyword:</strong> {keyword}</p>
    <p><strong>Geography:</strong> {geography}</p>
    <p><strong>Year Range:</strong> {year_range[0]} - {year_range[1]}</p>
    <h2>Variables</h2>
    {df.to_html(index=False)}
    <h2>Trend Analysis</h2>
    <img src="{plot_path}" alt="Trend Plot">
    """
    report_path = "report.html"
    with open(report_path, "w") as f:
        f.write(report_content)

    print(f"Report saved to {report_path}")
    return report_path


def acsexplorer_topic_search(keyword, include_shortlist = True):
    """
    Search for variables related to a specific topic using cached Census data.

    Parameters:
        keyword (str): The topic keyword to search for.
        include_shortlist (bool): If True, also return a concise shortlist of searched variables.

    Returns:
        pd.DataFrame: A DataFrame containing relevant variables and metadata.
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
            df_shortlist = acsexplorer_topic_search_shortlist(df)
            df_group = acsexplorer_get_variable_groups(df_shortlist)
            df_shortlist = pd.merge(df_shortlist, df_group, on="Group", how="left")
            cols = ["Concept"] + [col for col in df_shortlist.columns if col != "Concept"]
            df_shortlist = df_shortlist[cols]
            return df, df_shortlist, df_group
        else:
            return df
    else:
        print("No matching variables found.")
        return pd.DataFrame()


def acsexplorer_topic_search_shortlist(df):
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


def acsexplorer_get_variable_groups(df):
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
                print(f"Cache exists for {dataset}, {year}. Skipping download.")
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