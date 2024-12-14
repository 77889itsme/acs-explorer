from src.acs_explorer.acs_explorer import acsexplorer_get_geo_info, acsexplorer_get_data, acsexplorer_topic_search, acsexplorer_analyze_trends, acsexplorer_visualize_trends, acsexplorer_generate_report
import pandas as pd
import os

def test_geocoding():
    address = "1600 Amphitheatre Parkway, Mountain View, CA"

    geo_info = acsexplorer_get_geo_info(address)
    
    assert "state" in geo_info[1], "Geo info should contain 'state'."
    assert "county" in geo_info[1], "Geo info should contain 'county'."
    assert "tract" in geo_info[1], "Geo info should contain 'tract'."
    
    print("Geocoding test passed!")

def test_get_data():
    import pandas as pd

    variable = "B28002_001E"  # Internet subscription
    geography = "county"
    year = 2021
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
    df, df_shortlist = acsexplorer_topic_search(keyword, include_shortlist=True)
    
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



import pytest
from unittest.mock import patch, MagicMock
import os
import pandas as pd

@patch("builtins.open", new_callable=MagicMock)
@patch("os.makedirs")
@patch("acsexplorer_analyze_trends")
@patch("visualize_trends")
def test_generate_report(mock_visualize_trends, mock_analyze_trends, mock_makedirs, mock_open):
    # Mock inputs
    variables = ["variable1", "variable2"]
    geography = "state"
    year_range = (2010, 2020)
    dataset = "acs5"
    geo_filter = {"state": "16"}
    output_path = "reports/test_report.html"

    # Mock analysis trends return value
    mock_analyze_trends.return_value = pd.DataFrame({
        "year": [2010, 2011, 2012],
        "variable1": [100, 150, 200],
        "variable2": [50, 75, 100]
    })

    # Mock visualization return value
    mock_fig = MagicMock()
    mock_visualize_trends.return_value = mock_fig

    # Call the function
    result = acsexplorer_generate_report(variables, geography, year_range, dataset, geo_filter, output_path)

    # Check directory creation
    mock_makedirs.assert_called_once_with(os.path.dirname(output_path))

    # Check file writing
    mock_open.assert_called_once_with(output_path, "w")
    handle = mock_open()
    handle.write.assert_any_call("<h1>Comprehensive Report</h1>\n")
    handle.write.assert_any_call("<h2>Trend Analysis</h2>\n")
    
    # Verify the analyze_trends function is called correctly
    mock_analyze_trends.assert_called_once_with(variables, geography, year_range, dataset, geo_filter)

    # Verify visualization is called for each variable
    assert mock_visualize_trends.call_count == len(variables)

    # Verify the output path is returned
    assert result == output_path