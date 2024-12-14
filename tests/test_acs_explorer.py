from module.acs_explorer import acsexplorer_get_geo_info, acsexplorer_get_data, acsexplorer_topic_search, acsexplorer_analyze_trends, acsexplorer_visualize_trends, acsexplorer_generate_report
import pandas as pd
import os

def test_geocoding():
    address = "1600 Amphitheatre Parkway, Mountain View, CA"

    geo_info = acsexplorer_get_geo_info(address)
    
    assert isinstance(geo_info, dict), "Geo info should be a dictionary."
    assert "state" in geo_info, "Geo info should contain 'state'."
    assert "county" in geo_info, "Geo info should contain 'county'."
    assert "tract" in geo_info, "Geo info should contain 'tract'."
    
    print("Geocoding test passed!")

def test_get_data():
    import pandas as pd

    variable = "B28002_001E"  # Internet subscription
    geography = "state"
    year = 2020
    dataset = "acs5"

    data = acsexplorer_get_data(variable, geography, year, dataset)

    assert isinstance(data, pd.DataFrame), "The result should be a pandas DataFrame."
    assert "NAME" in data.columns, "The result should contain a 'NAME' column."
    assert variable in data.columns, f"The result should contain the '{variable}' column."
    assert geography in data.columns, f"The result should contain the '{geography}' column."
    
    print("Data fetching test passed!")

def test_topic_search():
    import nltk
    nltk.download('wordnet', quiet=True)
    
    keyword = "internet"
    df, df_shortlist, df_group = acsexplorer_topic_search(keyword, include_shortlist=True)
    
    assert not df.empty, "Topic search result should not be empty."
    assert "Variable Name" in df.columns, "Result should contain 'Variable Name'."
    
    print("Topic search test passed!")


def test_analyze_trends():
    variable = "B28001_001E"
    geography = "state"
    year_range = (2015, 2020)
    dataset = "acs1"

    trend_data = acsexplorer_analyze_trends(variable, geography, year_range, dataset)
    
    assert not trend_data.empty, "Trend analysis result should not be empty."
    assert "Year" in trend_data.columns, "'Year' column should be present in the result."
    assert "value" in trend_data.columns, "'value' column should be present in the result."

    print("Trend analysis test passed!")


def test_visualization():
    """
    Test visualization functions.
    """
    # Simulated trend data
    trend_data = pd.DataFrame({
        "Year": [2015, 2016, 2017, 2018, 2019, 2020],
        "value": [10, 15, 20, 25, 30, 35]
    })

    variable = "B28002_001E"
    plot_path = acsexplorer_visualize_trends(trend_data, variable)

    print(f"Visualization test result: Plot saved at {plot_path}")



def test_generate_report():
    import pandas as pd
    import os

    data_df = pd.DataFrame({
        "Year": [2015, 2016, 2017, 2018, 2019],
        "geography": ["state"] * 5,
        "B01003_001E": [100, 200, 300, 400, 500],
        "B28002_001E": [50, 100, 150, 200, 250]
    })
    variables = ["B01003_001E", "B28002_001E"]
    output_path = "test_report.html"
    acsexplorer_generate_report(data_df, variables, output_path)


    assert os.path.exists(output_path), "Report file should be generated."
    with open(output_path, "r") as f:
        content = f.read()
        assert "<h1>Comprehensive Report</h1>" in content, "Report header should be present."
        assert "B01003_001E" in content, "First variable should be included in the report."
        assert "B28002_001E" in content, "Second variable should be included in the report."
        assert "<h2>Raw Data</h2>" in content, "Raw data section should be present."
    os.remove(output_path)
