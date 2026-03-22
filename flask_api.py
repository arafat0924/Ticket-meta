"""
Flask API for Flight Search - connects to Hive via PySpark (ticketmeta09)
Deploy this file on your VM (192.168.56.101)
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from pyspark.sql import SparkSession
import os
import json
import re

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# PySpark Session (singleton)
# ---------------------------------------------------------------------------
_spark = None

def get_spark():
    """Get or create a SparkSession with Hive support."""
    global _spark
    if _spark is None or _spark._jsc.sc().isStopped():
        _spark = (
            SparkSession.builder
            .appName("SkyQuery-FlaskAPI")
            .master("yarn")
            .config("spark.submit.deployMode", "client")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.driver.memory", "2g")
            .config("spark.executor.memory", "2g")
            .config("spark.executor.instances", "2")
            .config("spark.yarn.queue", "default")
            .enableHiveSupport()
            .getOrCreate()
        )
        _spark.sql("USE ticketmeta09")

        # Try to use the optimized ORC table if it exists, otherwise cache
        try:
            tables = [r["tableName"] for r in _spark.sql("SHOW TABLES").collect()]
            if "itineraries_orc" in tables:
                print("Found optimized itineraries_orc table!")
            else:
                print("No optimized table found. Consider running the optimization script.")
                print("Caching ext_itineraries for faster repeated queries...")
                _spark.sql("CACHE LAZY TABLE ext_itineraries")
        except Exception as e:
            print(f"Cache/optimization check: {e}")
    return _spark


def get_flight_table():
    """Return the best available flight table name."""
    spark = get_spark()
    try:
        tables = [r["tableName"] for r in spark.sql("SHOW TABLES").collect()]
        if "itineraries_orc" in tables:
            return "itineraries_orc"
    except:
        pass
    return "ext_itineraries"


def run_query(sql):
    """Execute a Spark SQL / HiveQL query and return rows + column names."""
    spark = get_spark()
    df = spark.sql(sql)
    cols = df.columns
    rows = [row.asDict() for row in df.collect()]
    return cols, rows


def clean_row(row_dict):
    """Clean column names (remove table prefix if present) and convert types."""
    cleaned = {}
    for k, v in row_dict.items():
        key = k.split(".")[-1]
        # Convert Decimal, etc. to float for JSON serialization
        if v is not None and hasattr(v, '__float__'):
            cleaned[key] = float(v)
        else:
            cleaned[key] = v
    return cleaned


# ---------------------------------------------------------------------------
# Health / Tables
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    try:
        spark = get_spark()
        spark.sql("SELECT 1").collect()
        return jsonify({"status": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/tables")
def tables():
    try:
        spark = get_spark()
        df = spark.sql("SHOW TABLES")
        t = [row["tableName"] for row in df.collect()]
        return jsonify({"tables": t})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 1. Search Flights
#    GET /api/search-flights?origin=MIA&dest=SFO&nonstop=true&sort=cheapest&limit=20
# ---------------------------------------------------------------------------
@app.route("/api/search-flights")
def search_flights():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()
    nonstop = request.args.get("nonstop", "false").lower() == "true"
    sort = request.args.get("sort", "cheapest")
    limit = int(request.args.get("limit", 20))
    date = request.args.get("date", "")

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    where = f"startingAirport = '{origin}' AND destinationAirport = '{dest}'"
    if nonstop:
        where += " AND isNonStop = 'True'"
    if date:
        where += f" AND flightDate = '{date}'"

    order = "CAST(totalFare AS DOUBLE) ASC"
    if sort == "fastest":
        order = "CAST(segmentsDurationInSeconds AS DOUBLE) ASC"

    tbl = get_flight_table()
    sql = f"""
        SELECT legId, searchDate, flightDate, startingAirport, destinationAirport,
               travelDuration, isNonStop, isBasicEconomy, isRefundable,
               CAST(baseFare AS DOUBLE) AS baseFare,
               CAST(totalFare AS DOUBLE) AS totalFare,
               CAST(seatsRemaining AS INT) AS seatsRemaining,
               CAST(totalTravelDistance AS DOUBLE) AS totalTravelDistance,
               segmentsDepartureTimeRaw, segmentsArrivalTimeRaw,
               segmentsArrivalAirportCode, segmentsDepartureAirportCode,
               segmentsAirlineName, segmentsAirlineCode,
               segmentsEquipmentDescription, segmentsCabinCode
        FROM {tbl}
        WHERE {where}
        ORDER BY {order}
        LIMIT {limit}
    """

    try:
        cols, rows = run_query(sql)
        flights = [clean_row(r) for r in rows]
        return jsonify({"flights": flights, "count": len(flights), "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 2. Where to Fly
#    GET /api/where-to-fly?origin=ATL&limit=10
# ---------------------------------------------------------------------------
@app.route("/api/where-to-fly")
def where_to_fly():
    origin = request.args.get("origin", "").upper()
    limit = int(request.args.get("limit", 10))
    nonstop = request.args.get("nonstop", "false").lower() == "true"

    if not origin:
        return jsonify({"error": "origin is required"}), 400

    nonstop_filter = "AND isNonStop = 'True'" if nonstop else ""

    tbl = get_flight_table()
    sql = f"""
        SELECT destinationAirport,
               ROUND(MIN(CAST(totalFare AS DOUBLE)), 2)  AS minFare,
               ROUND(AVG(CAST(totalFare AS DOUBLE)), 2)  AS avgFare,
               COUNT(*) AS flightCount
        FROM {tbl}
        WHERE startingAirport = '{origin}' {nonstop_filter}
        GROUP BY destinationAirport
        ORDER BY minFare ASC
        LIMIT {limit}
    """

    try:
        cols, rows = run_query(sql)
        destinations = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "destinations": destinations, "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 3. When to Fly
#    GET /api/when-to-fly?origin=ATL&dest=LAX
# ---------------------------------------------------------------------------
@app.route("/api/when-to-fly")
def when_to_fly():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    tbl = get_flight_table()
    sql = f"""
        SELECT SUBSTR(flightDate, 1, 7) AS month,
               ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
               ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
               ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare,
               COUNT(*) AS flightCount
        FROM {tbl}
        WHERE startingAirport = '{origin}'
          AND destinationAirport = '{dest}'
        GROUP BY SUBSTR(flightDate, 1, 7)
        ORDER BY month ASC
    """

    try:
        cols, rows = run_query(sql)
        months = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "dest": dest, "months": months, "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 4. Airline Comparison
#    GET /api/airline-comparison?origin=ATL&dest=LAX
# ---------------------------------------------------------------------------
@app.route("/api/airline-comparison")
def airline_comparison():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    tbl = get_flight_table()
    sql = f"""
        SELECT segmentsAirlineName AS airline,
               ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
               ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
               ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare,
               COUNT(*) AS flightCount
        FROM {tbl}
        WHERE startingAirport = '{origin}'
          AND destinationAirport = '{dest}'
        GROUP BY segmentsAirlineName
        ORDER BY avgFare ASC
    """

    try:
        cols, rows = run_query(sql)
        airlines = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "dest": dest, "airlines": airlines, "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 5. Airport Search
#    GET /api/airports?q=Tokyo
# ---------------------------------------------------------------------------
@app.route("/api/airports")
def airports():
    q = request.args.get("q", "")
    limit = int(request.args.get("limit", 20))

    if not q:
        return jsonify({"error": "q (search query) is required"}), 400

    sql = f"""
        SELECT id, ident, type, name, latitude_deg, longitude_deg,
               elevation_ft, continent, iso_country, iso_region,
               municipality, scheduled_service, iata_code, home_link,
               wikipedia_link
        FROM airports
        WHERE LOWER(name) LIKE '%{q.lower()}%'
           OR LOWER(municipality) LIKE '%{q.lower()}%'
           OR LOWER(iata_code) LIKE '%{q.lower()}%'
           OR LOWER(ident) LIKE '%{q.lower()}%'
        LIMIT {limit}
    """

    try:
        cols, rows = run_query(sql)
        results = [clean_row(r) for r in rows]
        return jsonify({"airports": results, "count": len(results), "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 6. AI Chatbot  (Text-to-SQL via OpenAI)
#    POST /api/chatbot  {"question": "cheapest flights from ATL"}
# ---------------------------------------------------------------------------
@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(force=True)
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        import openai
    except ImportError:
        return jsonify({
            "error": "openai package not installed. Run: pip install openai",
            "answer": "OpenAI is not configured on the server."
        }), 500

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({
            "error": "OPENAI_API_KEY environment variable not set",
            "answer": "OpenAI API key is not configured on the server."
        }), 500

    schema_prompt = """
You are a SQL assistant for Apache Hive / Spark SQL. The database is ticketmeta09.

Table: ext_itineraries
Columns (ALL STRING type - must CAST for numeric operations):
  legId, searchDate, flightDate, startingAirport, destinationAirport,
  fareBasisCode, travelDuration, elapsedDays, isBasicEconomy, isRefundable,
  isNonStop, baseFare, totalFare, seatsRemaining, totalTravelDistance,
  segmentsDepartureTimeEpochSeconds, segmentsDepartureTimeRaw,
  segmentsArrivalTimeEpochSeconds, segmentsArrivalTimeRaw,
  segmentsArrivalAirportCode, segmentsDepartureAirportCode,
  segmentsAirlineName, segmentsAirlineCode, segmentsEquipmentDescription,
  segmentsDurationInSeconds, segmentsDistance, segmentsCabinCode

Important:
- Use CAST(totalFare AS DOUBLE) for fare comparisons
- Use CAST(seatsRemaining AS INT) for seat counts
- isNonStop values are 'True' or 'False' (strings)
- Airport codes are IATA (ATL, LAX, JFK, SFO, ORD, MIA)
- Always add LIMIT (default 20) to avoid huge scans

Table: airports
Columns: id INT, ident, type, name, latitude_deg DOUBLE, longitude_deg DOUBLE,
  elevation_ft INT, continent, iso_country, iso_region, municipality,
  scheduled_service, gps_code, iata_code, local_code, home_link,
  wikipedia_link, keywords

Table: countries
Columns: id INT, code, name, continent, wikipedia_link, keywords

Given a user question, generate ONLY the HiveQL/SparkSQL query. No explanation.
"""

    sql = ""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0,
            max_tokens=500
        )
        sql = response.choices[0].message.content.strip()

        # Clean up markdown code blocks
        sql = re.sub(r"^```(sql|hive|sparksql)?\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)

        # Safety: only allow SELECT
        if not sql.upper().strip().startswith("SELECT"):
            return jsonify({
                "answer": "I can only run SELECT queries for safety.",
                "sql": sql
            })

        cols, rows = run_query(sql)
        results = [clean_row(r) for r in rows]

        return jsonify({
            "answer": f"Found {len(results)} results.",
            "sql": sql,
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e), "sql": sql}), 500


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize Spark on startup
    print("Initializing SparkSession with Hive support...")
    get_spark()
    print("SparkSession ready. Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
