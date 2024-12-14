# __init__.py in the acs_explorer package
from src.acs_explorer.acs_explorer import acsexplorer_get_geo_info, acsexplorer_get_data, acsexplorer_topic_search, acsexplorer_topic_search_shortlist, acsexplorer_pipeline_by_location, acsexplorer_pipeline_by_keyword, acsexplorer_analyze_trends, acsexplorer_generate_report

# read version from installed package
from importlib.metadata import version

__all__ = [
    "acsexplorer_get_geo_info",
    "acsexplorer_topic_search",
    "acsexplorer_topic_search_shortlist",
    "acsexplorer_get_data",
    "acsexplorer_pipeline_by_location",
    "acsexplorer_pipeline_by_keyword",
    "acsexplorer_analyze_trends",
    "acsexplorer_generate_report"
]

__version__ = version("acs_explorer")