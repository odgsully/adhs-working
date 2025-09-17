"""
mapping.py
---------------

This module defines a static mapping of search names to the entity
details uncovered during the manual investigation of the Arizona
Corporation Commission (ACC) database.  It is **not** used by the
automation (`main.py`), but is provided for reference and to make the
process reproducible without hitting the live website.

Each key in ``ENTITY_DATA`` is a search string taken from the
``Owner_Ownership`` column in the provided Excel file.  The
corresponding value is a list of dictionaries, where each dictionary
contains a subset of the fields returned by the ACC site: entity
name(s), ID(s), entity type, status, formation date, business type,
domicile state, statutory agent, agent address, county, comments and
citation identifiers.  The citations (e.g., ``【526611159694825†L17-L101】``)
refer to the specific lines of the ACC pages captured during
research; these strings are included here merely as documentation and
have no functional role.

Because the mapping was generated manually, some entries may be
incomplete or omit certain fields that were absent on the ACC page.
When running the dynamic automation via `main.py`, these static
results are ignored.
"""

# Static mapping from search names to one or more entity detail records.
ENTITY_DATA = {
    "LEGACY TRADITIONAL SCHOOL - WEST SURPRISE": [
        {
            "Entity Name": "LEGACY TRADITIONAL SCHOOL- WEST SURPRISE",
            "Entity ID": "19967143",
            "Entity Type": "Domestic Nonprofit Corporation",
            "Status": "Active",
            "Formation Date": "4/6/2015",
            "Business Type": "Other – Other – Other – Educational",
            "Domicile State": "Arizona",
            "Statutory Agent": "AARON HALE",
            "Agent Address": "3125 S GILBERT RD, CHANDLER, AZ 85286, USA",
            "County": "Maricopa",
            "Comments": "In Good Standing",
            "Citation": "【908017485398112†L15-L90】",
        }
    ],
    # Additional entries from the analysis could be added here. For brevity
    # and readability, only a handful of representative examples are
    # included.  See acc_final_table.md for the full list of entities
    # discovered during the research.
    "PARADISE VALLEY EVNGLCL LUTHRN CH INC": [
        {
            "Entity Name": "PARADISE VALLEY EVANGELICAL LUTHERAN CHURCH",
            "Entity ID": "01036852",
            "Entity Type": "Domestic Nonprofit Corporation",
            "Status": "Active",
            "Formation Date": "2/6/1976",
            "Business Type": "Other – Other – Religious",
            "Domicile State": "Arizona",
            "Statutory Agent": "Anthony Converti",
            "Agent Address": "14845 N 40th St, Phoenix, AZ 85032",
            "County": "Maricopa",
            "Comments": "In Good Standing",
            "Citation": "【823437213691252†L13-L103】",
        }
    ],
    "91ST AVENUE PROPERTIES LLC": [
        {
            "Entity Name": "91ST AVENUE PROPERTIES LLC",
            "Entity ID": "23218253",
            "Entity Type": "Domestic LLC",
            "Status": "Active",
            "Formation Date": "5/3/2021",
            "Business Type": "Any legal purpose",
            "Domicile State": "Arizona",
            "Statutory Agent": "CT Corporation System",
            "Agent Address": "3800 N Central Ave Ste 460, Phoenix, AZ 85012",
            "County": "Maricopa",
            "Comments": "In Good Standing",
            "Citation": "【10210657032729†L15-L99】",
        }
    ],
    "SCHOOL DISTRICT 14": [
        {
            "Entity Name": "—",
            "Entity ID": "—",
            "Entity Type": "—",
            "Status": "Not found",
            "Formation Date": "—",
            "Business Type": "—",
            "Domicile State": "—",
            "Statutory Agent": "—",
            "Agent Address": "—",
            "County": "—",
            "Comments": "No search results",
            "Citation": "【459489346405190†screenshot】",
        }
    ],
    # ... more mappings can be appended here for each search term.
}

__all__ = ["ENTITY_DATA"]