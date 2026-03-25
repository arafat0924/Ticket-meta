"""
Data Enrichment API endpoints - append these to flask_api.py
Implements 5 external data analyses for the teacher's requirement.
"""
import requests
import csv
import io

# ── Airport → City/State mapping for external API lookups ──
AIRPORT_CITIES = {
    "ATL": {"city": "Atlanta", "state": "GA", "lat": 33.6407, "lon": -84.4277},
    "LAX": {"city": "Los Angeles", "state": "CA", "lat": 33.9425, "lon": -118.4081},
    "ORD": {"city": "Chicago", "state": "IL", "lat": 41.9742, "lon": -87.9073},
    "DFW": {"city": "Dallas", "state": "TX", "lat": 32.8998, "lon": -97.0403},
    "DEN": {"city": "Denver", "state": "CO", "lat": 39.8561, "lon": -104.6737},
    "JFK": {"city": "New York", "state": "NY", "lat": 40.6413, "lon": -73.7781},
    "SFO": {"city": "San Francisco", "state": "CA", "lat": 37.6213, "lon": -122.3790},
    "SEA": {"city": "Seattle", "state": "WA", "lat": 47.4502, "lon": -122.3088},
    "LAS": {"city": "Las Vegas", "state": "NV", "lat": 36.0840, "lon": -115.1537},
    "MCO": {"city": "Orlando", "state": "FL", "lat": 28.4312, "lon": -81.3081},
    "EWR": {"city": "Newark", "state": "NJ", "lat": 40.6895, "lon": -74.1745},
    "MIA": {"city": "Miami", "state": "FL", "lat": 25.7959, "lon": -80.2870},
    "CLT": {"city": "Charlotte", "state": "NC", "lat": 35.2140, "lon": -80.9431},
    "PHX": {"city": "Phoenix", "state": "AZ", "lat": 33.4373, "lon": -112.0078},
    "IAH": {"city": "Houston", "state": "TX", "lat": 29.9902, "lon": -95.3368},
    "BOS": {"city": "Boston", "state": "MA", "lat": 42.3656, "lon": -71.0096},
    "MSP": {"city": "Minneapolis", "state": "MN", "lat": 44.8848, "lon": -93.2223},
    "DTW": {"city": "Detroit", "state": "MI", "lat": 42.2124, "lon": -83.3534},
    "PHL": {"city": "Philadelphia", "state": "PA", "lat": 39.8744, "lon": -75.2424},
    "LGA": {"city": "New York", "state": "NY", "lat": 40.7769, "lon": -73.8740},
    "FLL": {"city": "Fort Lauderdale", "state": "FL", "lat": 26.0742, "lon": -80.1506},
    "BWI": {"city": "Baltimore", "state": "MD", "lat": 39.1754, "lon": -76.6684},
    "DCA": {"city": "Washington", "state": "DC", "lat": 38.8512, "lon": -77.0402},
    "SLC": {"city": "Salt Lake City", "state": "UT", "lat": 40.7899, "lon": -111.9791},
    "IAD": {"city": "Washington", "state": "DC", "lat": 38.9531, "lon": -77.4565},
    "SAN": {"city": "San Diego", "state": "CA", "lat": 32.7338, "lon": -117.1933},
    "TPA": {"city": "Tampa", "state": "FL", "lat": 27.9756, "lon": -82.5333},
    "BNA": {"city": "Nashville", "state": "TN", "lat": 36.1263, "lon": -86.6774},
    "AUS": {"city": "Austin", "state": "TX", "lat": 30.1975, "lon": -97.6664},
    "PDX": {"city": "Portland", "state": "OR", "lat": 45.5898, "lon": -122.5951},
    "STL": {"city": "St. Louis", "state": "MO", "lat": 38.7487, "lon": -90.3700},
    "OAK": {"city": "Oakland", "state": "CA", "lat": 37.7213, "lon": -122.2208},
    "RDU": {"city": "Raleigh", "state": "NC", "lat": 35.8801, "lon": -78.7880},
    "PIT": {"city": "Pittsburgh", "state": "PA", "lat": 40.4915, "lon": -80.2329},
}

# ── Income tiers by metro area (approximate median household income) ──
METRO_INCOME = {
    "SFO": 112449, "SJC": 117474, "OAK": 112449, "SEA": 94027,
    "BOS": 89212, "DCA": 105659, "IAD": 105659, "JFK": 75910,
    "LGA": 75910, "EWR": 85245, "LAX": 73052, "SAN": 83985,
    "DEN": 84843, "MSP": 84313, "ATL": 71193, "AUS": 80954,
    "PDX": 78673, "BNA": 67571, "CLT": 64017, "ORD": 78304,
    "DFW": 72265, "IAH": 69193, "PHX": 65210, "PHL": 68740,
    "DTW": 61003, "MIA": 51347, "FLL": 58905, "MCO": 55021,
    "TPA": 54599, "LAS": 58377, "SLC": 75626, "BWI": 82253,
    "STL": 57920, "PIT": 61344, "RDU": 72576, "BNA": 67571,
}

# ── Northeast Corridor rail-covered pairs ──
RAIL_COVERED = {
    ("BOS","JFK"),("BOS","LGA"),("BOS","EWR"),("BOS","PHL"),("BOS","BWI"),("BOS","DCA"),("BOS","IAD"),
    ("JFK","PHL"),("JFK","BWI"),("JFK","DCA"),("JFK","EWR"),("JFK","BOS"),
    ("LGA","PHL"),("LGA","BWI"),("LGA","DCA"),("LGA","EWR"),("LGA","BOS"),
    ("EWR","PHL"),("EWR","BWI"),("EWR","DCA"),("EWR","BOS"),("EWR","JFK"),("EWR","LGA"),
    ("PHL","BWI"),("PHL","DCA"),("PHL","JFK"),("PHL","LGA"),("PHL","EWR"),("PHL","BOS"),
    ("BWI","DCA"),("BWI","PHL"),("BWI","JFK"),("BWI","LGA"),("BWI","EWR"),("BWI","BOS"),
    ("DCA","BWI"),("DCA","PHL"),("DCA","JFK"),("DCA","LGA"),("DCA","EWR"),("DCA","BOS"),
    ("IAD","BWI"),("IAD","PHL"),("IAD","JFK"),("IAD","LGA"),("IAD","EWR"),("IAD","BOS"),
}
