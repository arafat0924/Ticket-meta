# 🛫 Data Turbulence — Team Lead Guide
## How We Process Data: Two Different Pipelines

### Overview
Our project uses **two different data pipelines** depending on the data source. Your teacher's requirement has two parts, and each follows a different process.

---

## 📌 Pipeline 1: Teacher's Dataset (Expedia Flight Data — ~80M rows)
**This is the FULL Big Data pipeline using HDFS + Hive + ORC + SparkSQL.**

### Steps your team must follow:
```
Step 1: Get the CSV dataset from the teacher
        ↓
Step 2: Upload CSV to HDFS (Hadoop Distributed File System)
        $ hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/
        $ hdfs dfs -put itineraries.csv /user/hive/warehouse/ticketmeta09.db/
        ↓
Step 3: Create a Hive External Table pointing to the CSV
        (See: hql/itineraries.hql)
        CREATE EXTERNAL TABLE ext_itineraries (
            legId STRING, searchDate STRING, flightDate STRING, ...
        )
        ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION '/user/hive/warehouse/ticketmeta09.db/';
        ↓
Step 4: Optimize with ORC compression (columnar format, ~10x faster)
        (See: optimize_table.py)
        CREATE TABLE itineraries_orc STORED AS ORC AS
        SELECT * FROM ext_itineraries;
        ↓
Step 5: Query via SparkSQL in Flask API
        spark.sql("SELECT ... FROM itineraries_orc WHERE ...")
        ↓
Step 6: Serve results to React frontend via REST API
```

### Why this pipeline?
- Dataset is **80+ million rows** — too large for regular processing
- HDFS distributes storage across cluster nodes
- Hive provides SQL interface over HDFS files
- ORC format compresses data and enables column-level reads (huge speedup)
- SparkSQL parallelizes query execution across YARN cluster

---

## 📌 Pipeline 2: External Datasets (Requirement 2 — 5 External Analyses)
**This does NOT use HDFS/Hive/ORC. External data is fetched at runtime.**

### Why different?
External datasets are either:
- **Live API calls** (data changes in real-time, small response sizes)
- **Small CSV files** (thousands of rows, not millions)

There's no need to put these in HDFS/Hive because they're tiny compared to 80M rows.

### Our 5 External Data Sources:

| # | Analysis | Source | Type | How We Access It |
|---|----------|--------|------|-----------------|
| 1 | Weather Impact | NOAA (api.weather.gov) | REST API | Flask calls API at runtime, merges with Hive query results |
| 2 | Wealth Discrimination | FRED/Census Bureau | Static Data | Median income data hardcoded from Census (small lookup table) |
| 3 | Brand Markup | DOT Airline_Delay_Cause.csv | CSV File | Uploaded to VM, read by Python `csv` module at runtime |
| 4 | Rail Competition | Amtrak API (amtrak-api.marcmap.app) | REST API | Flask calls API at runtime |
| 5 | Ghost Fares | Reddit API (reddit.com/r/travel) | REST API | Flask calls API at runtime |

### How the enrichment works in code:
```python
# In flask_api.py — example for Weather endpoint:

@app.route("/api/enrichment/weather")
def enrichment_weather():
    # STEP A: Query internal Hive data (teacher's dataset)
    sql = "SELECT flightDate, AVG(totalFare) ... FROM itineraries_orc WHERE ..."
    hive_results = spark.sql(sql)     # ← Uses Pipeline 1
    
    # STEP B: Call external API (NOAA weather)
    weather = requests.get("https://api.weather.gov/...")  # ← Pipeline 2
    
    # STEP C: Merge both and return to frontend
    return jsonify({"hiveData": hive_results, "weather": weather})
```

### The one CSV file (Airline_Delay_Cause.csv):
**This file ALSO goes through the full HDFS → Hive → ORC pipeline** (same as teacher's dataset):
```
Step 1: Download from DOT website (Bureau of Transportation Statistics)
        ↓
Step 2: Copy CSV to VM
        $ scp Airline_Delay_Cause.csv azmine@192.168.56.105:~/
        ↓
Step 3: Upload to HDFS
        $ hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/airline_delay_cause
        $ hdfs dfs -put Airline_Delay_Cause.csv /user/hive/warehouse/ticketmeta09.db/airline_delay_cause/
        ↓
Step 4: Create Hive External Table
        (See: hql_code/airline_delay_cause.hql)
        CREATE EXTERNAL TABLE ext_airline_delay_cause (...)
        ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION '/user/hive/warehouse/ticketmeta09.db/airline_delay_cause'
        ↓
Step 5: Create ORC Optimized Table
        CREATE TABLE airline_delay_cause_orc STORED AS ORC
        AS SELECT * FROM ext_airline_delay_cause;
        ↓
Step 6: Query via SparkSQL in Flask API
        spark.sql("SELECT carrier_name, ... FROM airline_delay_cause_orc ...")
```
**This ensures ALL datasets follow the same HDFS → Hive → ORC pipeline**, satisfying the teacher's requirement.

---

## � Key Difference Summary

| Aspect | Teacher's Dataset | External Datasets |
|--------|------------------|-------------------|
| **Size** | ~80 million rows | Small (API responses / 23K rows CSV) |
| **Storage** | HDFS | VM local filesystem / API calls |
| **Schema** | Hive External Table | Python dicts / JSON |
| **Optimization** | ORC columnar format | Not needed (data is small) |
| **Query Engine** | SparkSQL on YARN cluster | Python requests library / csv module |
| **When data loads** | Pre-loaded in HDFS, cached in Spark | Fetched on each API request (real-time) |
| **Processing** | Distributed (Spark executors) | Single-threaded (Flask) |

---

## �🚀 Steps for Team Members

### If you're working on Pipeline 1 (Hive/Spark features):
1. SSH into VM: `ssh azmine@192.168.56.105`
2. Data is already in HDFS under `ticketmeta09` database
3. Use `optimize_table.py` to create ORC table if not already done
4. Add new endpoints to `flask_api.py` using `run_query(sql)` helper
5. Add frontend API function in `frontend/src/api.js`
6. Create page component in `frontend/src/pages/`
7. Register route in `App.js` and nav link in `Navbar.js`

### If you're working on Pipeline 2 (External data enrichment):
1. Find your external API/dataset
2. Add a new endpoint in the `# DATA ENRICHMENT ENDPOINTS` section of `flask_api.py`
3. In the endpoint: first query Hive for internal data, then call external API
4. Merge both results and return as JSON
5. Add API function in `frontend/src/api.js`
6. Add a new tab in `DataEnrichment.js`

### Deploying changes:
```bash
# From Windows (local machine):
python deploy_api.py        # Uploads flask_api.py to VM and restarts API
cd frontend && npm start    # Start frontend dev server
```

### Git workflow:
```bash
git checkout -b YourName           # Create your branch
git add . && git commit -m "..."   # Commit with meaningful message
git push -u origin YourName        # Push your branch
git checkout main                  # Switch to main
git merge YourName --no-ff         # Merge with merge commit
git push origin main               # Push to GitHub
```

---

## 📁 Project Structure
```
Ticket-meta/
├── flask_api.py              ← Backend API (runs on VM with Spark/Hive)
├── Airline_Delay_Cause.csv   ← External CSV dataset (Pipeline 2)
├── deploy_api.py             ← Script to upload & restart API on VM
├── optimize_table.py         ← Creates ORC table from Hive external table
├── hql/                      ← Hive DDL scripts
│   └── itineraries.hql       ← Creates ext_itineraries table
├── frontend/
│   ├── src/api.js            ← All API calls to backend
│   ├── src/App.js            ← Routes
│   ├── src/components/
│   │   └── Navbar.js         ← Navigation bar
│   └── src/pages/
│       ├── FlightSearch.js   ← Search flights (Pipeline 1)
│       ├── AnalyticsDashboard.js ← Analytics (Pipeline 1)
│       ├── FlightSplicing.js ← Spliced itineraries (Pipeline 1)
│       ├── DataEnrichment.js ← 5 External analyses (Pipeline 1 + 2)
│       ├── Chatbot.js        ← AI chatbot (Pipeline 1 + DeepSeek)
│       └── Landing.js        ← Homepage
```

---

**Questions? Ask Azmine (team lead) or check the README.md**
