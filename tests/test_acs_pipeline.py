from src.acs_explorer.acs_explorer import acsexplorer_pipeline_by_location, acsexplorer_pipeline_by_keyword
import os

def test_pipeline_by_location():
    addresses = ["1600 Amphitheatre Parkway, Mountain View, CA"]
    geography = "state"
    variables = ["B28002_001E"]
    year_range = (2015, 2019)
    dataset = "acs5"
    output_path="reports"

    acsexplorer_pipeline_by_location(addresses, geography, variables, year_range, dataset, output_path)

    assert os.path.exists(output_path), "Pipeline should generate a report file."
    os.remove(output_path)

    print("Pipeline by location test passed!")



def test_pipeline_by_keyword():
    keyword = "internet"
    geography = "state"
    year_range = (2015, 2019)
    dataset = "acs5"
    top_search = 1
    output_path="reports"

    acsexplorer_pipeline_by_keyword(keyword, geography, year_range, dataset, top_search, output_path)

    assert os.path.exists(output_path), "Pipeline should generate a report file."
    os.remove(output_path)

    print("Pipeline by keyword test passed!")