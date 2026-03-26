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
import time
import threading

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# In-Memory Cache (analytics results cached for 1 hour)
# ---------------------------------------------------------------------------
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 3600  # 1 hour in seconds

def cache_get(key):
    """Get cached result if still valid."""
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL:
            return entry["data"]
    return None

def cache_set(key, data):
    """Store result in cache."""
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}

def cached_query(cache_key, query_fn):
    """Run query_fn() with caching. Returns cached result if available."""
    cached = cache_get(cache_key)
    if cached is not None:
        cached["cached"] = True
        return cached
    result = query_fn()
    result["cached"] = False
    cache_set(cache_key, result)
    return result

# ---------------------------------------------------------------------------
# PySpark Session (singleton)
# ---------------------------------------------------------------------------
_spark = None

# MySQL JDBC driver path (required for Hive Metastore connection)
MYSQL_DRIVER = "/opt/apache-hive-4.0.1/lib/mysql-connector-j-8.4.0.jar"

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
            .config("spark.driver.extraClassPath", MYSQL_DRIVER)
            .config("spark.executor.extraClassPath", MYSQL_DRIVER)
            .config("spark.sql.hive.metastore.jars", "builtin")
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
# Cache Management
# ---------------------------------------------------------------------------
@app.route("/api/cache/clear", methods=["POST", "GET"])
def clear_cache():
    """Clear all cached analytics results."""
    with _cache_lock:
        count = len(_cache)
        _cache.clear()
    return jsonify({"message": f"Cleared {count} cached entries", "cleared": count})


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
# 5a. Analytics – Pricing Overview
#     GET /api/analytics/overview
# ---------------------------------------------------------------------------
@app.route("/api/analytics/overview")
def analytics_overview():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT
                COUNT(*)                                        AS totalFlights,
                ROUND(AVG(CAST(totalFare AS DOUBLE)), 2)        AS avgFare,
                ROUND(MIN(CAST(totalFare AS DOUBLE)), 2)        AS minFare,
                ROUND(MAX(CAST(totalFare AS DOUBLE)), 2)        AS maxFare,
                SUM(CASE WHEN isRefundable = 'True'  THEN 1 ELSE 0 END) AS refundableCount,
                SUM(CASE WHEN isRefundable = 'False' THEN 1 ELSE 0 END) AS nonRefundableCount,
                ROUND(AVG(CASE WHEN isRefundable = 'True'  THEN CAST(totalFare AS DOUBLE) END), 2) AS avgFareRefundable,
                ROUND(AVG(CASE WHEN isRefundable = 'False' THEN CAST(totalFare AS DOUBLE) END), 2) AS avgFareNonRefundable,
                SUM(CASE WHEN isBasicEconomy = 'True'  THEN 1 ELSE 0 END) AS basicEconomyCount,
                SUM(CASE WHEN isBasicEconomy = 'False' THEN 1 ELSE 0 END) AS standardEconomyCount,
                SUM(CASE WHEN isNonStop = 'True'  THEN 1 ELSE 0 END) AS nonstopCount,
                SUM(CASE WHEN isNonStop = 'False' THEN 1 ELSE 0 END) AS connectingCount
            FROM {tbl}
        """
        _, rows = run_query(sql)
        overview = clean_row(rows[0]) if rows else {}
        return {"overview": overview, "query": sql.strip()}
    try:
        result = cached_query("analytics_overview", _query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5b. Analytics – Top 15 Airlines
#     GET /api/analytics/top-airlines
# ---------------------------------------------------------------------------
@app.route("/api/analytics/top-airlines")
def analytics_top_airlines():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT segmentsAirlineName AS airline,
                   COUNT(*) AS flightCount,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
                   ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
                   ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare
            FROM {tbl}
            WHERE segmentsAirlineName IS NOT NULL AND segmentsAirlineName != ''
            GROUP BY segmentsAirlineName
            ORDER BY flightCount DESC
            LIMIT 15
        """
        _, rows = run_query(sql)
        airlines = [clean_row(r) for r in rows]
        return {"airlines": airlines, "query": sql.strip()}
    try:
        return jsonify(cached_query("analytics_top_airlines", _query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5c. Analytics – Flights by Day of Week
#     GET /api/analytics/day-of-week
# ---------------------------------------------------------------------------
@app.route("/api/analytics/day-of-week")
def analytics_day_of_week():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT
                CASE DAYOFWEEK(flightDate)
                    WHEN 1 THEN 'Sunday'    WHEN 2 THEN 'Monday'
                    WHEN 3 THEN 'Tuesday'   WHEN 4 THEN 'Wednesday'
                    WHEN 5 THEN 'Thursday'  WHEN 6 THEN 'Friday'
                    WHEN 7 THEN 'Saturday'
                END AS dayName,
                DAYOFWEEK(flightDate) AS dayNum,
                COUNT(*) AS flightCount,
                ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare
            FROM {tbl}
            WHERE flightDate IS NOT NULL
            GROUP BY DAYOFWEEK(flightDate)
            ORDER BY DAYOFWEEK(flightDate)
        """
        _, rows = run_query(sql)
        days = [clean_row(r) for r in rows]
        return {"days": days, "query": sql.strip()}
    try:
        return jsonify(cached_query("analytics_day_of_week", _query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5d. Analytics – Booking Window (avg price vs days before departure)
#     GET /api/analytics/booking-window
# ---------------------------------------------------------------------------
@app.route("/api/analytics/booking-window")
def analytics_booking_window():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT
                DATEDIFF(flightDate, searchDate) AS bookingWindow,
                COUNT(*) AS flightCount,
                ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
                ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare
            FROM {tbl}
            WHERE flightDate IS NOT NULL AND searchDate IS NOT NULL
              AND DATEDIFF(flightDate, searchDate) >= 0
              AND DATEDIFF(flightDate, searchDate) <= 180
            GROUP BY DATEDIFF(flightDate, searchDate)
            ORDER BY bookingWindow ASC
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        return {"bookingWindow": data, "query": sql.strip()}
    try:
        return jsonify(cached_query("analytics_booking_window", _query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5e. Analytics – Weekend vs Mid-week Pricing
#     GET /api/analytics/weekend-midweek
# ---------------------------------------------------------------------------
@app.route("/api/analytics/weekend-midweek")
def analytics_weekend_midweek():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT
                CASE
                    WHEN DAYOFWEEK(flightDate) IN (1, 6, 7) THEN 'Weekend (Fri/Sat/Sun)'
                    ELSE 'Midweek (Mon-Thu)'
                END AS travelType,
                COUNT(*) AS flightCount,
                ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
                ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
                ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare
            FROM {tbl}
            WHERE flightDate IS NOT NULL
            GROUP BY CASE
                    WHEN DAYOFWEEK(flightDate) IN (1, 6, 7) THEN 'Weekend (Fri/Sat/Sun)'
                    ELSE 'Midweek (Mon-Thu)'
                END
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        return {"comparison": data, "query": sql.strip()}
    try:
        return jsonify(cached_query("analytics_weekend_midweek", _query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5f. Analytics – Basic vs Standard Economy Price Gap
#     GET /api/analytics/economy-gap
# ---------------------------------------------------------------------------
@app.route("/api/analytics/economy-gap")
def analytics_economy_gap():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT
                startingAirport, destinationAirport,
                ROUND(AVG(CASE WHEN isBasicEconomy = 'True'  THEN CAST(totalFare AS DOUBLE) END), 2) AS avgBasic,
                ROUND(AVG(CASE WHEN isBasicEconomy = 'False' THEN CAST(totalFare AS DOUBLE) END), 2) AS avgStandard,
                ROUND(
                    AVG(CASE WHEN isBasicEconomy = 'False' THEN CAST(totalFare AS DOUBLE) END) -
                    AVG(CASE WHEN isBasicEconomy = 'True'  THEN CAST(totalFare AS DOUBLE) END)
                , 2) AS priceGap,
                COUNT(*) AS totalFlights
            FROM {tbl}
            GROUP BY startingAirport, destinationAirport
            HAVING AVG(CASE WHEN isBasicEconomy = 'True' THEN CAST(totalFare AS DOUBLE) END) IS NOT NULL
               AND AVG(CASE WHEN isBasicEconomy = 'False' THEN CAST(totalFare AS DOUBLE) END) IS NOT NULL
            ORDER BY priceGap DESC
            LIMIT 20
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        return {"routes": data, "query": sql.strip()}
    try:
        return jsonify(cached_query("analytics_economy_gap", _query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5g. Flight Splicing Engine – Find cost-saving virtual itineraries
#     GET /api/flight-splicing?origin=ATL&dest=SFO&maxLayover=4&minLayover=1
# ---------------------------------------------------------------------------
@app.route("/api/flight-splicing")
def flight_splicing():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()
    max_layover = int(request.args.get("maxLayover", 4))
    min_layover = float(request.args.get("minLayover", 1.5))
    limit = int(request.args.get("limit", 20))

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    tbl = get_flight_table()

    # Step 1: Find best direct flight price for baseline
    direct_sql = f"""
        SELECT ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS bestDirect,
               ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgDirect,
               COUNT(*) AS directCount
        FROM {tbl}
        WHERE startingAirport = '{origin}' AND destinationAirport = '{dest}'
    """

    # Step 2: Find spliced itineraries via intermediate airports
    # Leg 1: origin → hub, Leg 2: hub → dest (same flightDate)
    splice_sql = f"""
        SELECT
            leg1.startingAirport AS origin,
            leg1.destinationAirport AS hub,
            leg2.destinationAirport AS dest,
            leg1.flightDate,
            leg1.segmentsAirlineName AS airline1,
            leg2.segmentsAirlineName AS airline2,
            ROUND(CAST(leg1.totalFare AS DOUBLE), 2) AS fare1,
            ROUND(CAST(leg2.totalFare AS DOUBLE), 2) AS fare2,
            ROUND(CAST(leg1.totalFare AS DOUBLE) + CAST(leg2.totalFare AS DOUBLE), 2) AS combinedFare,
            leg1.segmentsArrivalTimeRaw AS leg1Arrival,
            leg2.segmentsDepartureTimeRaw AS leg2Departure,
            ROUND(
                (CAST(leg2.segmentsDepartureTimeEpochSeconds AS BIGINT) -
                 CAST(leg1.segmentsArrivalTimeEpochSeconds AS BIGINT)) / 3600.0
            , 1) AS layoverHours
        FROM {tbl} leg1
        JOIN {tbl} leg2
            ON leg1.destinationAirport = leg2.startingAirport
            AND leg1.flightDate = leg2.flightDate
        WHERE leg1.startingAirport = '{origin}'
          AND leg2.destinationAirport = '{dest}'
          AND leg1.isNonStop = 'True'
          AND leg2.isNonStop = 'True'
          AND (CAST(leg2.segmentsDepartureTimeEpochSeconds AS BIGINT) -
               CAST(leg1.segmentsArrivalTimeEpochSeconds AS BIGINT)) / 3600.0
              BETWEEN {min_layover} AND {max_layover}
        ORDER BY combinedFare ASC
        LIMIT {limit}
    """

    try:
        # Get direct flight baseline
        _, direct_rows = run_query(direct_sql)
        direct = clean_row(direct_rows[0]) if direct_rows else {}

        # Get spliced itineraries
        _, splice_rows = run_query(splice_sql)
        itineraries = [clean_row(r) for r in splice_rows]

        # Calculate savings for each itinerary
        best_direct = direct.get("bestDirect") or direct.get("bestdirect")
        if best_direct:
            for it in itineraries:
                combined = it.get("combinedFare") or it.get("combinedfare") or 0
                it["savings"] = round(float(best_direct) - float(combined), 2)
                it["savingsPercent"] = round((float(best_direct) - float(combined)) / float(best_direct) * 100, 1) if float(best_direct) > 0 else 0

        return jsonify({
            "origin": origin, "dest": dest,
            "direct": direct,
            "itineraries": itineraries,
            "directQuery": direct_sql.strip(),
            "spliceQuery": splice_sql.strip()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 5h. Where to Fly (Budget) – includes distance for scatter chart
#     GET /api/where-to-fly-budget?origin=ATL&budget=500
# ---------------------------------------------------------------------------
@app.route("/api/where-to-fly-budget")
def where_to_fly_budget():
    origin = request.args.get("origin", "").upper()
    budget = request.args.get("budget", "")
    nonstop = request.args.get("nonstop", "false").lower() == "true"
    limit = int(request.args.get("limit", 50))

    if not origin:
        return jsonify({"error": "origin is required"}), 400

    nonstop_filter = "AND isNonStop = 'True'" if nonstop else ""
    budget_filter = f"HAVING MIN(CAST(totalFare AS DOUBLE)) <= {float(budget)}" if budget else ""

    tbl = get_flight_table()
    sql = f"""
        SELECT destinationAirport,
               ROUND(MIN(CAST(totalFare AS DOUBLE)), 2)  AS minFare,
               ROUND(AVG(CAST(totalFare AS DOUBLE)), 2)  AS avgFare,
               ROUND(AVG(CAST(totalTravelDistance AS DOUBLE)), 0) AS avgDistance,
               COUNT(*) AS flightCount
        FROM {tbl}
        WHERE startingAirport = '{origin}'
          AND totalTravelDistance IS NOT NULL
          AND CAST(totalTravelDistance AS DOUBLE) > 0
          {nonstop_filter}
        GROUP BY destinationAirport
        {budget_filter}
        ORDER BY minFare ASC
        LIMIT {limit}
    """

    try:
        _, rows = run_query(sql)
        destinations = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "destinations": destinations, "query": sql.strip()})
    except Exception as e:
        return jsonify({"error": str(e), "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 6. Airport Search
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
# 6. AI Chatbot  (Text-to-SQL via DeepSeek AI) — STREAMING via SSE
#    POST /api/chatbot  {"question": "cheapest flights from ATL"}
#    POST /api/chatbot/stream  (same body, returns SSE stream)
# ---------------------------------------------------------------------------

CHATBOT_SCHEMA_PROMPT = """
You are a friendly AI flight assistant called Data Turbulence. You help users find flight information by querying a Hive database.

BEHAVIOR RULES:
1. If the user sends a greeting (hi, hello, hey, etc.), a general question, or something NOT related to flights/airports/airlines data, respond conversationally. Start your response with "CHAT:" followed by a friendly message. For example: "CHAT: Hi there! 👋 I'm Data Turbulence, your AI flight assistant. I can help you find cheap flights, compare airlines, discover destinations, and more. Try asking me something like 'cheapest nonstop flights from ATL to LAX' or 'which airlines fly from JFK?'"
2. If the user asks about flights, prices, airports, airlines, destinations, or anything that requires database lookup, generate ONLY the HiveQL/SparkSQL query (no "CHAT:" prefix, no explanation).
3. Remember conversation context — if the user says "now show nonstop only" after a previous query, adjust the previous query accordingly.

DATABASE SCHEMA (ticketmeta09):

TABLE: ext_itineraries (use """ + '"{tbl}"' + """ at runtime)
Columns (ALL STRING type - must CAST for numeric operations):
  legId, searchDate, flightDate, startingAirport, destinationAirport,
  fareBasisCode, travelDuration, elapsedDays, isBasicEconomy, isRefundable,
  isNonStop, baseFare, totalFare, seatsRemaining, totalTravelDistance,
  segmentsDepartureTimeEpochSeconds, segmentsDepartureTimeRaw,
  segmentsArrivalTimeEpochSeconds, segmentsArrivalTimeRaw,
  segmentsArrivalAirportCode, segmentsDepartureAirportCode,
  segmentsAirlineName, segmentsAirlineCode, segmentsEquipmentDescription,
  segmentsDurationInSeconds, segmentsDistance, segmentsCabinCode

Important SQL rules:
- Use CAST(totalFare AS DOUBLE) for fare comparisons
- Use CAST(seatsRemaining AS INT) for seat counts
- isNonStop values are 'True' or 'False' (strings)
- Airport codes are IATA (ATL, LAX, JFK, SFO, ORD, MIA)
- Always add LIMIT (default 20) to avoid huge scans
- ALWAYS use ext_itineraries as the table name

Table: airports
Columns: id INT, ident, type, name, latitude_deg DOUBLE, longitude_deg DOUBLE,
  elevation_ft INT, continent, iso_country, iso_region, municipality,
  scheduled_service, gps_code, iata_code, local_code, home_link,
  wikipedia_link, keywords

Table: countries
Columns: id INT, code, name, continent, wikipedia_link, keywords
"""


def _build_ai_messages(question, history):
    """Build the OpenAI message list from question + history."""
    messages = [{"role": "system", "content": CHATBOT_SCHEMA_PROMPT}]
    if history and isinstance(history, list):
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    else:
        messages.append({"role": "user", "content": question})
    if not messages[-1].get("content", "").strip() == question:
        messages.append({"role": "user", "content": question})
    return messages


def _call_deepseek(messages):
    """Call DeepSeek API and return the raw text response."""
    import openai
    api_key = os.environ.get("DEEPSEEK_API_KEY", "sk-ebc20963bcba441e91e7917fc616a097")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0,
        max_tokens=500,
        timeout=30,  # 30s timeout for AI response
    )
    return response.choices[0].message.content.strip()


def _clean_sql(raw):
    """Clean markdown fences, replace table name placeholder, enforce LIMIT."""
    sql = re.sub(r"^```(sql|hive|sparksql)?\s*", "", raw)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.strip()
    # Replace placeholder table with actual optimised table
    tbl = get_flight_table()
    sql = sql.replace("ext_itineraries", tbl)
    # Enforce LIMIT if missing
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip("; ") + " LIMIT 20"
    return sql


def _run_query_with_timeout(sql, timeout_seconds=120):
    """Run a Spark SQL query with a timeout. Returns (cols, rows) or raises."""
    import threading

    result = {"cols": None, "rows": None, "error": None}

    def target():
        try:
            cols, rows = run_query(sql)
            result["cols"] = cols
            result["rows"] = rows
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise TimeoutError(f"Query timed out after {timeout_seconds}s. Try a more specific query with filters.")
    if result["error"]:
        raise result["error"]
    return result["cols"], result["rows"]


# ---------- SSE streaming endpoint (primary) ----------
@app.route("/api/chatbot/stream", methods=["POST"])
def chatbot_stream():
    from flask import Response

    data = request.get_json(force=True)
    question = data.get("question", "")
    history = data.get("history", [])

    if not question:
        def err():
            yield f"data: {json.dumps({'type': 'error', 'message': 'question is required'})}\n\n"
        return Response(err(), mimetype="text/event-stream")

    def generate():
        # Phase 1 — call DeepSeek AI
        yield f"data: {json.dumps({'type': 'status', 'message': 'Asking AI...'})}\n\n"
        try:
            messages = _build_ai_messages(question, history)
            raw = _call_deepseek(messages)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'AI error: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Phase 2 — check if it's a chat response
        if raw.startswith("CHAT:"):
            chat_msg = raw[5:].strip()
            yield f"data: {json.dumps({'type': 'answer', 'answer': chat_msg, 'sql': None, 'results': None})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Phase 3 — it's SQL
        sql = _clean_sql(raw)

        if not sql.upper().strip().startswith("SELECT"):
            yield f"data: {json.dumps({'type': 'answer', 'answer': sql if len(sql) > 20 else 'I can only run SELECT queries for safety.', 'sql': None, 'results': None})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Send SQL immediately so user sees it while query runs
        yield f"data: {json.dumps({'type': 'sql', 'sql': sql})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': 'Running query on Hive...'})}\n\n"

        # Phase 4 — execute query with timeout
        try:
            cols, rows = _run_query_with_timeout(sql, timeout_seconds=120)
            results = [clean_row(r) for r in rows]
            yield f"data: {json.dumps({'type': 'answer', 'answer': f'Found {len(results)} results.', 'sql': sql, 'results': results})}\n\n"
        except TimeoutError as te:
            yield f"data: {json.dumps({'type': 'answer', 'answer': f'⏱ {str(te)}', 'sql': sql, 'results': None})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'answer', 'answer': f'Query error: {str(e)}', 'sql': sql, 'results': None})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------- Legacy non-streaming endpoint (kept for compatibility) ----------
@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(force=True)
    question = data.get("question", "")
    history = data.get("history", [])

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        import openai
    except ImportError:
        return jsonify({"error": "openai not installed", "answer": "AI not configured."}), 500

    try:
        messages = _build_ai_messages(question, history)
        raw = _call_deepseek(messages)

        if raw.startswith("CHAT:"):
            return jsonify({"answer": raw[5:].strip(), "sql": None, "results": None})

        sql = _clean_sql(raw)

        if not sql.upper().strip().startswith("SELECT"):
            return jsonify({"answer": sql if len(sql) > 20 else "I can only run SELECT queries for safety.", "sql": None, "results": None})

        cols, rows = _run_query_with_timeout(sql, timeout_seconds=120)
        results = [clean_row(r) for r in rows]
        return jsonify({"answer": f"Found {len(results)} results.", "sql": sql, "results": results})

    except TimeoutError as te:
        return jsonify({"answer": f"⏱ {str(te)}", "sql": sql, "results": None})
    except Exception as e:
        return jsonify({"error": str(e), "sql": locals().get("sql", "")}), 500


# ===========================================================================
# DATA ENRICHMENT ENDPOINTS (Requirement 2: External Datasets)
# ===========================================================================
import requests as ext_requests
import csv as csv_mod
import io as io_mod

AIRPORT_CITIES = {
    "ATL":"Atlanta,GA","LAX":"Los Angeles,CA","ORD":"Chicago,IL","DFW":"Dallas,TX",
    "DEN":"Denver,CO","JFK":"New York,NY","SFO":"San Francisco,CA","SEA":"Seattle,WA",
    "LAS":"Las Vegas,NV","MCO":"Orlando,FL","EWR":"Newark,NJ","MIA":"Miami,FL",
    "CLT":"Charlotte,NC","PHX":"Phoenix,AZ","IAH":"Houston,TX","BOS":"Boston,MA",
    "MSP":"Minneapolis,MN","DTW":"Detroit,MI","PHL":"Philadelphia,PA","LGA":"New York,NY",
    "FLL":"Fort Lauderdale,FL","BWI":"Baltimore,MD","DCA":"Washington,DC","SLC":"Salt Lake City,UT",
    "IAD":"Washington,DC","SAN":"San Diego,CA","TPA":"Tampa,FL","BNA":"Nashville,TN",
    "AUS":"Austin,TX","PDX":"Portland,OR","STL":"St. Louis,MO","OAK":"Oakland,CA",
    "RDU":"Raleigh,NC","PIT":"Pittsburgh,PA",
}
AIRPORT_COORDS = {
    "ATL":(33.64,-84.43),"LAX":(33.94,-118.41),"ORD":(41.97,-87.91),"DFW":(32.90,-97.04),
    "DEN":(39.86,-104.67),"JFK":(40.64,-73.78),"SFO":(37.62,-122.38),"SEA":(47.45,-122.31),
    "LAS":(36.08,-115.15),"MCO":(28.43,-81.31),"EWR":(40.69,-74.17),"MIA":(25.80,-80.29),
    "CLT":(35.21,-80.94),"PHX":(33.44,-112.01),"IAH":(29.99,-95.34),"BOS":(42.37,-71.01),
    "MSP":(44.88,-93.22),"DTW":(42.21,-83.35),"PHL":(39.87,-75.24),"LGA":(40.78,-73.87),
    "FLL":(26.07,-80.15),"BWI":(39.18,-76.67),"DCA":(38.85,-77.04),"SLC":(40.79,-111.98),
}
METRO_INCOME = {
    "SFO":112449,"OAK":112449,"SJC":117474,"SEA":94027,"BOS":89212,"DCA":105659,
    "IAD":105659,"JFK":75910,"LGA":75910,"EWR":85245,"LAX":73052,"SAN":83985,
    "DEN":84843,"MSP":84313,"ATL":71193,"AUS":80954,"PDX":78673,"BNA":67571,
    "CLT":64017,"ORD":78304,"DFW":72265,"IAH":69193,"PHX":65210,"PHL":68740,
    "DTW":61003,"MIA":51347,"FLL":58905,"MCO":55021,"TPA":54599,"LAS":58377,
    "SLC":75626,"BWI":82253,"STL":57920,"PIT":61344,"RDU":72576,
}
RAIL_PAIRS = {
    ("BOS","JFK"),("BOS","LGA"),("BOS","EWR"),("BOS","PHL"),("BOS","BWI"),("BOS","DCA"),
    ("JFK","PHL"),("JFK","BWI"),("JFK","DCA"),("JFK","EWR"),("JFK","BOS"),
    ("LGA","PHL"),("LGA","BWI"),("LGA","DCA"),("LGA","EWR"),("LGA","BOS"),
    ("EWR","PHL"),("EWR","BWI"),("EWR","DCA"),("EWR","BOS"),("EWR","JFK"),("EWR","LGA"),
    ("PHL","BWI"),("PHL","DCA"),("PHL","JFK"),("PHL","LGA"),("PHL","EWR"),("PHL","BOS"),
    ("BWI","DCA"),("BWI","PHL"),("BWI","JFK"),("BWI","LGA"),("BWI","EWR"),("BWI","BOS"),
    ("DCA","BWI"),("DCA","PHL"),("DCA","JFK"),("DCA","LGA"),("DCA","EWR"),("DCA","BOS"),
    ("IAD","BWI"),("IAD","PHL"),("IAD","JFK"),("IAD","LGA"),("IAD","EWR"),("IAD","BOS"),
}

# ---------------------------------------------------------------------------
# I. Severe Weather & Capacity Contraction Premium
# ---------------------------------------------------------------------------
@app.route("/api/enrichment/weather")
def enrichment_weather():
    airport = request.args.get("airport", "ATL").upper()
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT flightDate,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
                   COUNT(*) AS flightCount,
                   SUM(CASE WHEN isNonStop='True' THEN 1 ELSE 0 END) AS nonstopCount,
                   SUM(CASE WHEN isNonStop='False' THEN 1 ELSE 0 END) AS connectingCount,
                   ROUND(AVG(CAST(seatsRemaining AS INT)),1) AS avgSeats,
                   ROUND(AVG(DATEDIFF(flightDate,searchDate)),1) AS avgLeadDays
            FROM {tbl}
            WHERE startingAirport='{airport}' AND flightDate IS NOT NULL
            GROUP BY flightDate ORDER BY flightDate
        """
        _, rows = run_query(sql)
        return {"airport": airport, "dailyData": [clean_row(r) for r in rows], "query": sql.strip()}
    try:
        result = cached_query(f"weather_{airport}", _query)
        # Fetch NOAA weather
        weather = {}
        coords = AIRPORT_COORDS.get(airport)
        if coords:
            try:
                pts = ext_requests.get(f"https://api.weather.gov/points/{coords[0]},{coords[1]}",
                                       headers={"User-Agent":"SkyQuery/1.0"}, timeout=10).json()
                station_url = pts.get("properties",{}).get("observationStations","")
                if station_url:
                    stations = ext_requests.get(station_url, headers={"User-Agent":"SkyQuery/1.0"}, timeout=10).json()
                    station_id = stations.get("features",[{}])[0].get("properties",{}).get("stationIdentifier","")
                    if station_id:
                        obs = ext_requests.get(f"https://api.weather.gov/stations/{station_id}/observations?limit=200",
                                               headers={"User-Agent":"SkyQuery/1.0"}, timeout=15).json()
                        for f in obs.get("features",[]):
                            p = f.get("properties",{})
                            ts = (p.get("timestamp") or "")[:10]
                            if ts:
                                weather[ts] = {
                                    "temp": p.get("temperature",{}).get("value"),
                                    "wind": p.get("windSpeed",{}).get("value"),
                                    "precip": p.get("precipitationLastHour",{}).get("value"),
                                    "desc": p.get("textDescription",""),
                                }
            except Exception as we:
                weather = {"error": str(we)}
        result["weather"] = weather
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# II. Geographical Wealth & Purchasing Power Discrimination
# ---------------------------------------------------------------------------
@app.route("/api/enrichment/wealth")
def enrichment_wealth():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT startingAirport,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)/NULLIF(CAST(totalTravelDistance AS DOUBLE),0)),4) AS avgPricePerMile,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
                   ROUND(AVG(CAST(totalTravelDistance AS DOUBLE)),0) AS avgDistance,
                   COUNT(*) AS flightCount
            FROM {tbl}
            WHERE totalTravelDistance IS NOT NULL AND CAST(totalTravelDistance AS DOUBLE) > 50
              AND totalFare IS NOT NULL AND CAST(totalFare AS DOUBLE) > 0
            GROUP BY startingAirport
            HAVING COUNT(*) > 100
            ORDER BY avgPricePerMile DESC
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        # Enrich with income data
        for d in data:
            ap = d.get("startingAirport","")
            d["medianIncome"] = METRO_INCOME.get(ap)
            d["city"] = AIRPORT_CITIES.get(ap,"Unknown")
            if d["medianIncome"] and d["medianIncome"] >= 90000:
                d["incomeTier"] = "High"
            elif d["medianIncome"] and d["medianIncome"] >= 70000:
                d["incomeTier"] = "Medium"
            else:
                d["incomeTier"] = "Low"
        return {"airports": data, "query": sql.strip()}
    try:
        result = cached_query("wealth_analysis", _query)
        # Summary by tier
        tiers = {}
        for a in result.get("airports", []):
            tier = a.get("incomeTier", "Unknown")
            if tier not in tiers:
                tiers[tier] = {"count": 0, "totalPPM": 0, "totalFare": 0}
            tiers[tier]["count"] += 1
            tiers[tier]["totalPPM"] += a.get("avgPricePerMile", 0) or 0
            tiers[tier]["totalFare"] += a.get("avgFare", 0) or 0
        summary = []
        for tier, v in tiers.items():
            if v["count"] > 0:
                summary.append({
                    "tier": tier, "airportCount": v["count"],
                    "avgPricePerMile": round(v["totalPPM"] / v["count"], 4),
                    "avgFare": round(v["totalFare"] / v["count"], 2),
                })
        result["tierSummary"] = sorted(summary, key=lambda x: x["avgPricePerMile"], reverse=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# III. Brand Markup & Service Quality Correlation
# ---------------------------------------------------------------------------
@app.route("/api/enrichment/brand")
def enrichment_brand():
    def _query():
        tbl = get_flight_table()
        # Top 5 competitive routes
        routes_sql = f"""
            SELECT startingAirport, destinationAirport,
                   COUNT(DISTINCT segmentsAirlineName) AS airlineCount,
                   COUNT(*) AS flightCount
            FROM {tbl}
            WHERE segmentsAirlineName IS NOT NULL AND segmentsAirlineName != ''
            GROUP BY startingAirport, destinationAirport
            HAVING COUNT(DISTINCT segmentsAirlineName) >= 5
            ORDER BY flightCount DESC LIMIT 5
        """
        _, route_rows = run_query(routes_sql)
        routes = [clean_row(r) for r in route_rows]

        # For each route, get airline pricing
        all_comparisons = []
        for route in routes[:5]:
            o, d = route["startingAirport"], route["destinationAirport"]
            comp_sql = f"""
                SELECT segmentsAirlineName AS airline,
                       ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
                       ROUND(MIN(CAST(totalFare AS DOUBLE)),2) AS minFare,
                       ROUND(MAX(CAST(totalFare AS DOUBLE)),2) AS maxFare,
                       COUNT(*) AS flightCount,
                       ROUND(AVG(CASE WHEN isNonStop='True' THEN 1.0 ELSE 0.0 END)*100,1) AS nonstopPct
                FROM {tbl}
                WHERE startingAirport='{o}' AND destinationAirport='{d}'
                  AND segmentsAirlineName IS NOT NULL AND segmentsAirlineName != ''
                GROUP BY segmentsAirlineName ORDER BY avgFare DESC
            """
            _, comp_rows = run_query(comp_sql)
            all_comparisons.append({
                "route": f"{o}→{d}", "origin": o, "dest": d,
                "airlines": [clean_row(r) for r in comp_rows]
            })
        return {"routes": routes, "comparisons": all_comparisons, "routeQuery": routes_sql.strip()}
    try:
        result = cached_query("brand_analysis", _query)
        # Load delay data from Hive ORC table (same HDFS+Hive+ORC pipeline as teacher's dataset)
        delay_data = {}
        try:
            delay_sql = """
                SELECT carrier_name,
                       ROUND(SUM(arr_del15),0) AS total_delays,
                       ROUND(SUM(arr_flights),0) AS total_flights,
                       COUNT(*) AS entries,
                       ROUND((1 - SUM(arr_del15)/SUM(arr_flights))*100, 1) AS onTimePct
                FROM airline_delay_cause_orc
                WHERE carrier_name IS NOT NULL
                GROUP BY carrier_name
                ORDER BY total_flights DESC
            """
            _, delay_rows = run_query(delay_sql)
            for row in delay_rows:
                r = clean_row(row)
                carrier = r.get("carrier_name","")
                if carrier:
                    delay_data[carrier] = {
                        "total_delays": r.get("total_delays", 0),
                        "total_flights": r.get("total_flights", 0),
                        "entries": r.get("entries", 0),
                        "onTimePct": r.get("onTimePct"),
                    }
        except Exception as ce:
            delay_data = {"_error": str(ce)}
        result["delayData"] = delay_data
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# IV. Intermodal Competition: Rail Price Ceiling Effect
# ---------------------------------------------------------------------------
@app.route("/api/enrichment/rail")
def enrichment_rail():
    def _query():
        tbl = get_flight_table()
        sql = f"""
            SELECT startingAirport, destinationAirport,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
                   ROUND(AVG(CAST(totalTravelDistance AS DOUBLE)),0) AS avgDistance,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)/NULLIF(CAST(totalTravelDistance AS DOUBLE),0)),4) AS pricePerMile,
                   COUNT(*) AS flightCount
            FROM {tbl}
            WHERE CAST(totalTravelDistance AS DOUBLE) < 500
              AND CAST(totalTravelDistance AS DOUBLE) > 50
              AND totalFare IS NOT NULL AND CAST(totalFare AS DOUBLE) > 0
            GROUP BY startingAirport, destinationAirport
            HAVING COUNT(*) > 20
            ORDER BY pricePerMile DESC
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        rail_covered, rail_vacuum = [], []
        for d in data:
            pair = (d["startingAirport"], d["destinationAirport"])
            d["hasRail"] = pair in RAIL_PAIRS or (pair[1],pair[0]) in RAIL_PAIRS
            if d["hasRail"]:
                rail_covered.append(d)
            else:
                rail_vacuum.append(d)
        # Summary
        rc_ppm = [r["pricePerMile"] for r in rail_covered if r["pricePerMile"]]
        rv_ppm = [r["pricePerMile"] for r in rail_vacuum if r["pricePerMile"]]
        summary = {
            "railCovered": {"count": len(rail_covered),
                           "avgPricePerMile": round(sum(rc_ppm)/len(rc_ppm),4) if rc_ppm else 0},
            "railVacuum": {"count": len(rail_vacuum),
                          "avgPricePerMile": round(sum(rv_ppm)/len(rv_ppm),4) if rv_ppm else 0},
        }
        if summary["railVacuum"]["avgPricePerMile"] > 0:
            summary["priceCeilingEffect"] = round(
                (1 - summary["railCovered"]["avgPricePerMile"]/summary["railVacuum"]["avgPricePerMile"])*100, 1)
        return {"routes": data, "railCovered": rail_covered, "railVacuum": rail_vacuum,
                "summary": summary, "query": sql.strip()}
    try:
        result = cached_query("rail_analysis", _query)
        # Fetch Amtrak stations
        try:
            amtrak = ext_requests.get("https://amtrak-api.marcmap.app/get-stations", timeout=15).json()
            result["amtrakStations"] = len(amtrak) if isinstance(amtrak, list) else 0
            result["amtrakSample"] = amtrak[:20] if isinstance(amtrak, list) else []
        except Exception as ae:
            result["amtrakStations"] = 0
            result["amtrakError"] = str(ae)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# V. Ghost Fare & Price Manipulation Monitoring
# ---------------------------------------------------------------------------
@app.route("/api/enrichment/ghost")
def enrichment_ghost():
    def _query():
        tbl = get_flight_table()
        # Find price anomalies: same route, same flightDate, wildly different fares
        sql = f"""
            SELECT startingAirport, destinationAirport, flightDate,
                   ROUND(MIN(CAST(totalFare AS DOUBLE)),2) AS minFare,
                   ROUND(MAX(CAST(totalFare AS DOUBLE)),2) AS maxFare,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
                   ROUND(MAX(CAST(totalFare AS DOUBLE))/NULLIF(MIN(CAST(totalFare AS DOUBLE)),0),2) AS priceRatio,
                   COUNT(DISTINCT searchDate) AS searchDates,
                   COUNT(*) AS listings
            FROM {tbl}
            WHERE totalFare IS NOT NULL AND CAST(totalFare AS DOUBLE) > 0
            GROUP BY startingAirport, destinationAirport, flightDate
            HAVING MAX(CAST(totalFare AS DOUBLE))/NULLIF(MIN(CAST(totalFare AS DOUBLE)),0) > 3
               AND COUNT(*) > 5
            ORDER BY priceRatio DESC
            LIMIT 50
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        # Sawtooth detection: price jumps within short search windows
        saw_sql = f"""
            SELECT startingAirport, destinationAirport, flightDate, searchDate,
                   ROUND(CAST(totalFare AS DOUBLE),2) AS fare,
                   segmentsAirlineName AS airline
            FROM {tbl}
            WHERE startingAirport='ATL' AND destinationAirport='LAX'
              AND totalFare IS NOT NULL AND CAST(totalFare AS DOUBLE) > 0
            ORDER BY flightDate, searchDate
            LIMIT 200
        """
        _, saw_rows = run_query(saw_sql)
        sawtooth = [clean_row(r) for r in saw_rows]
        return {"anomalies": data, "sawtooth": sawtooth, "query": sql.strip(), "sawtoothQuery": saw_sql.strip()}
    try:
        result = cached_query("ghost_analysis", _query)
        # Fetch Reddit complaints
        try:
            reddit = ext_requests.get(
                "https://www.reddit.com/r/travel/search.json?q=ghost%20fare%20OR%20price%20bait%20OR%20fake%20price&limit=50&sort=relevance",
                headers={"User-Agent": "SkyQuery/1.0"}, timeout=15
            ).json()
            posts = []
            for child in reddit.get("data",{}).get("children",[]):
                d = child.get("data",{})
                posts.append({
                    "title": d.get("title",""),
                    "score": d.get("score",0),
                    "comments": d.get("num_comments",0),
                    "url": f"https://reddit.com{d.get('permalink','')}",
                    "created": d.get("created_utc",0),
                    "subreddit": d.get("subreddit",""),
                })
            result["redditPosts"] = posts
        except Exception as re_err:
            result["redditPosts"] = []
            result["redditError"] = str(re_err)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================================================================
#   NEW ANALYTICS ENDPOINTS — Sections I.10, II, III
# ===========================================================================

# I.10  Nonstop premium — top 20 busiest routes direct vs multi-leg
@app.route("/api/analytics/nonstop-premium")
def analytics_nonstop_premium():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT route, nonstop_avg, connecting_avg,
               (nonstop_avg - connecting_avg) AS premium,
               nonstop_cnt, connecting_cnt
        FROM (
            SELECT CONCAT(startingAirport,' → ',destinationAirport) AS route,
                   AVG(CASE WHEN isNonStop='true' THEN CAST(totalFare AS DOUBLE) END) AS nonstop_avg,
                   AVG(CASE WHEN isNonStop='false' THEN CAST(totalFare AS DOUBLE) END) AS connecting_avg,
                   SUM(CASE WHEN isNonStop='true' THEN 1 ELSE 0 END) AS nonstop_cnt,
                   SUM(CASE WHEN isNonStop='false' THEN 1 ELSE 0 END) AS connecting_cnt,
                   COUNT(*) AS total
            FROM {tbl}
            GROUP BY startingAirport, destinationAirport
            ORDER BY total DESC
            LIMIT 20
        ) sub
        WHERE nonstop_avg IS NOT NULL AND connecting_avg IS NOT NULL
        """
        _, rows = run_query(sql)
        data = [clean_row(r) for r in rows]
        return {"routes": data, "query": sql}
    return jsonify(cached_query("nonstop_premium", _query))

# II.1 + II.2  Network overview — unique airports + null distance records
@app.route("/api/analytics/network-overview")
def analytics_network_overview():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT
            COUNT(DISTINCT startingAirport) AS unique_origins,
            COUNT(DISTINCT destinationAirport) AS unique_destinations,
            SUM(CASE WHEN totalTravelDistance IS NULL OR CAST(totalTravelDistance AS DOUBLE) IS NULL THEN 1 ELSE 0 END) AS null_distance_records,
            COUNT(*) AS total_records
        FROM {tbl}
        """
        _, rows = run_query(sql)
        r = clean_row(rows[0]) if rows else {}
        return {"overview": r, "query": sql}
    return jsonify(cached_query("network_overview", _query))

# II.3  Top 10 longest flights by distance
@app.route("/api/analytics/longest-flights")
def analytics_longest_flights():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT startingAirport, destinationAirport,
               CAST(totalTravelDistance AS DOUBLE) AS distance,
               segmentsAirlineName AS airline,
               CAST(totalFare AS DOUBLE) AS fare, travelDuration
        FROM {tbl}
        WHERE totalTravelDistance IS NOT NULL AND CAST(totalTravelDistance AS DOUBLE) > 0
        ORDER BY CAST(totalTravelDistance AS DOUBLE) DESC
        LIMIT 10
        """
        _, rows = run_query(sql)
        return {"flights": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("longest_flights", _query))

# II.4  Top 20 most frequent routes
@app.route("/api/analytics/top-routes")
def analytics_top_routes():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT startingAirport, destinationAirport,
               CONCAT(startingAirport,' → ',destinationAirport) AS route,
               COUNT(*) AS flightCount,
               ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare
        FROM {tbl}
        GROUP BY startingAirport, destinationAirport
        ORDER BY flightCount DESC
        LIMIT 20
        """
        _, rows = run_query(sql)
        return {"routes": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("top_routes", _query))

# II.5  Top 10 municipalities with most outbound flights
@app.route("/api/analytics/top-municipalities")
def analytics_top_municipalities():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT a.municipality, COUNT(*) AS flightCount,
               ROUND(AVG(CAST(f.totalFare AS DOUBLE)),2) AS avgFare
        FROM {tbl} f
        JOIN airports a ON f.startingAirport = a.iata_code
        WHERE a.municipality IS NOT NULL AND a.municipality != ''
        GROUP BY a.municipality
        ORDER BY flightCount DESC
        LIMIT 10
        """
        _, rows = run_query(sql)
        return {"municipalities": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("top_municipalities", _query))

# II.6  Top 5 regions with most active airports
@app.route("/api/analytics/top-regions")
def analytics_top_regions():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT a.iso_region AS region, COUNT(DISTINCT f.startingAirport) AS airportCount,
               COUNT(*) AS flightCount
        FROM {tbl} f
        JOIN airports a ON f.startingAirport = a.iata_code
        WHERE a.iso_region IS NOT NULL
        GROUP BY a.iso_region
        ORDER BY airportCount DESC
        LIMIT 5
        """
        _, rows = run_query(sql)
        return {"regions": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("top_regions", _query))

# II.7  Top 10 most expensive destination airports
@app.route("/api/analytics/expensive-destinations")
def analytics_expensive_destinations():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT destinationAirport,
               ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
               COUNT(*) AS flightCount,
               ROUND(MIN(CAST(totalFare AS DOUBLE)),2) AS minFare,
               ROUND(MAX(CAST(totalFare AS DOUBLE)),2) AS maxFare
        FROM {tbl}
        GROUP BY destinationAirport
        HAVING COUNT(*) > 100
        ORDER BY avgFare DESC
        LIMIT 10
        """
        _, rows = run_query(sql)
        return {"destinations": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("expensive_destinations", _query))

# II.8  Top 20 routes with highest non-stop volume
@app.route("/api/analytics/nonstop-routes")
def analytics_nonstop_routes():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT CONCAT(startingAirport,' → ',destinationAirport) AS route,
               SUM(CASE WHEN isNonStop='true' THEN 1 ELSE 0 END) AS nonstopCount,
               COUNT(*) AS totalFlights,
               ROUND(SUM(CASE WHEN isNonStop='true' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS nonstopPct
        FROM {tbl}
        GROUP BY startingAirport, destinationAirport
        ORDER BY nonstopCount DESC
        LIMIT 20
        """
        _, rows = run_query(sql)
        return {"routes": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("nonstop_routes", _query))

# II.9  Small regional vs large hub airport pricing
@app.route("/api/analytics/hub-vs-regional")
def analytics_hub_vs_regional():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT a.type AS airport_type,
               COUNT(*) AS flightCount,
               ROUND(AVG(CAST(f.totalFare AS DOUBLE)),2) AS avgFare,
               ROUND(MIN(CAST(f.totalFare AS DOUBLE)),2) AS minFare,
               ROUND(MAX(CAST(f.totalFare AS DOUBLE)),2) AS maxFare
        FROM {tbl} f
        JOIN airports a ON f.startingAirport = a.iata_code
        WHERE a.type IN ('large_airport','medium_airport','small_airport')
        GROUP BY a.type
        ORDER BY flightCount DESC
        """
        _, rows = run_query(sql)
        return {"types": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("hub_vs_regional", _query))

# II.10  Most expensive outbound region/state
@app.route("/api/analytics/region-pricing")
def analytics_region_pricing():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT a.iso_region AS region,
               ROUND(AVG(CAST(f.totalFare AS DOUBLE)),2) AS avgFare,
               COUNT(*) AS flightCount
        FROM {tbl} f
        JOIN airports a ON f.startingAirport = a.iata_code
        WHERE a.iso_region IS NOT NULL
        GROUP BY a.iso_region
        HAVING COUNT(*) > 50
        ORDER BY avgFare DESC
        LIMIT 15
        """
        _, rows = run_query(sql)
        return {"regions": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("region_pricing", _query))

# II.11  Monopoly routes vs competitive routes price-per-mile
@app.route("/api/analytics/monopoly-routes")
def analytics_monopoly_routes():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT competition, COUNT(*) AS routeCount,
               ROUND(AVG(avgFare),2) AS overallAvgFare,
               ROUND(AVG(pricePerMile),4) AS avgPricePerMile
        FROM (
            SELECT CONCAT(startingAirport,'→',destinationAirport) AS route,
                   COUNT(DISTINCT segmentsAirlineCode) AS numAirlines,
                   AVG(CAST(totalFare AS DOUBLE)) AS avgFare,
                   CASE WHEN AVG(CAST(totalTravelDistance AS DOUBLE)) > 0
                        THEN AVG(CAST(totalFare AS DOUBLE)) / AVG(CAST(totalTravelDistance AS DOUBLE))
                        ELSE NULL END AS pricePerMile,
                   CASE WHEN COUNT(DISTINCT segmentsAirlineCode) = 1 THEN 'Monopoly (1 airline)'
                        WHEN COUNT(DISTINCT segmentsAirlineCode) >= 3 THEN 'Competitive (3+ airlines)'
                        ELSE 'Duopoly (2 airlines)' END AS competition
            FROM {tbl}
            WHERE totalTravelDistance IS NOT NULL AND CAST(totalTravelDistance AS DOUBLE) > 0
            GROUP BY startingAirport, destinationAirport
        ) sub
        GROUP BY competition
        ORDER BY competition
        """
        _, rows = run_query(sql)
        return {"data": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("monopoly_routes", _query))

# II.12  Top 5 busiest hubs — legacy vs budget carrier pricing
@app.route("/api/analytics/hub-carriers")
def analytics_hub_carriers():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT startingAirport AS hub,
               segmentsAirlineName AS airline,
               COUNT(*) AS flightCount,
               ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare
        FROM {tbl}
        WHERE startingAirport IN (
            SELECT startingAirport FROM {tbl}
            GROUP BY startingAirport ORDER BY COUNT(*) DESC LIMIT 5
        )
        GROUP BY startingAirport, segmentsAirlineName
        HAVING COUNT(*) > 50
        ORDER BY startingAirport, flightCount DESC
        """
        _, rows = run_query(sql)
        return {"carriers": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("hub_carriers", _query))

# III.1+III.2+III.3  Aircraft overview — count, top 10, Boeing vs Airbus
@app.route("/api/analytics/aircraft-overview")
def analytics_aircraft_overview():
    def _query():
        tbl = get_flight_table()
        sql_count = f"SELECT COUNT(DISTINCT segmentsEquipmentDescription) AS total FROM {tbl} WHERE segmentsEquipmentDescription IS NOT NULL AND segmentsEquipmentDescription != ''"
        sql_top = f"""
        SELECT segmentsEquipmentDescription AS aircraft, COUNT(*) AS flightCount
        FROM {tbl}
        WHERE segmentsEquipmentDescription IS NOT NULL AND segmentsEquipmentDescription != ''
        GROUP BY segmentsEquipmentDescription
        ORDER BY flightCount DESC
        LIMIT 10
        """
        sql_mfr = f"""
        SELECT
            SUM(CASE WHEN UPPER(segmentsEquipmentDescription) LIKE '%BOEING%' OR UPPER(segmentsEquipmentDescription) LIKE '%B7%' THEN 1 ELSE 0 END) AS boeing,
            SUM(CASE WHEN UPPER(segmentsEquipmentDescription) LIKE '%AIRBUS%' OR UPPER(segmentsEquipmentDescription) LIKE '%A3%' THEN 1 ELSE 0 END) AS airbus,
            COUNT(*) AS total
        FROM {tbl}
        WHERE segmentsEquipmentDescription IS NOT NULL AND segmentsEquipmentDescription != ''
        """
        c1, r1 = run_query(sql_count)
        c2, r2 = run_query(sql_top)
        c3, r3 = run_query(sql_mfr)
        return {
            "totalModels": (r1[0].get("total", 0) if r1 else 0) if r1 else 0,
            "topAircraft": [clean_row(r) for r in r2],
            "manufacturers": clean_row(r3[0]) if r3 else {},
            "query": sql_top
        }
    return jsonify(cached_query("aircraft_overview", _query))

# III.4  Zero seats vs available seats pricing
@app.route("/api/analytics/seats-pricing")
def analytics_seats_pricing():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT
            CASE WHEN CAST(seatsRemaining AS INT) = 0 THEN 'Zero Seats'
                 WHEN CAST(seatsRemaining AS INT) BETWEEN 1 AND 3 THEN 'Low (1-3)'
                 ELSE 'Available (4+)' END AS seatCategory,
            COUNT(*) AS flightCount,
            ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
            ROUND(MIN(CAST(totalFare AS DOUBLE)),2) AS minFare,
            ROUND(MAX(CAST(totalFare AS DOUBLE)),2) AS maxFare
        FROM {tbl}
        WHERE seatsRemaining IS NOT NULL
        GROUP BY CASE WHEN CAST(seatsRemaining AS INT) = 0 THEN 'Zero Seats'
                      WHEN CAST(seatsRemaining AS INT) BETWEEN 1 AND 3 THEN 'Low (1-3)'
                      ELSE 'Available (4+)' END
        ORDER BY avgFare DESC
        """
        _, rows = run_query(sql)
        return {"data": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("seats_pricing", _query))

# III.5  Runway length vs ticket price
@app.route("/api/analytics/runway-pricing")
def analytics_runway_pricing():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT
            CASE WHEN CAST(r.length_ft AS INT) >= 10000 THEN 'Long (10000+ ft)'
                 WHEN CAST(r.length_ft AS INT) >= 7000 THEN 'Medium (7000-9999 ft)'
                 ELSE 'Short (<7000 ft)' END AS runwayCategory,
            COUNT(*) AS flightCount,
            ROUND(AVG(CAST(f.totalFare AS DOUBLE)),2) AS avgFare
        FROM {tbl} f
        JOIN airports a ON f.destinationAirport = a.iata_code
        JOIN ext_runways r ON a.ident = r.airport_ident
        WHERE r.length_ft IS NOT NULL AND CAST(r.length_ft AS INT) > 0
        GROUP BY CASE WHEN CAST(r.length_ft AS INT) >= 10000 THEN 'Long (10000+ ft)'
                      WHEN CAST(r.length_ft AS INT) >= 7000 THEN 'Medium (7000-9999 ft)'
                      ELSE 'Short (<7000 ft)' END
        ORDER BY avgFare DESC
        """
        _, rows = run_query(sql)
        return {"data": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("runway_pricing", _query))

# III.6  Aircraft model pricing — wide-body vs regional
@app.route("/api/analytics/aircraft-pricing")
def analytics_aircraft_pricing():
    def _query():
        tbl = get_flight_table()
        sql = f"""
        SELECT
            CASE WHEN UPPER(segmentsEquipmentDescription) LIKE '%777%' OR UPPER(segmentsEquipmentDescription) LIKE '%787%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A350%' OR UPPER(segmentsEquipmentDescription) LIKE '%A330%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A380%' OR UPPER(segmentsEquipmentDescription) LIKE '%767%'
                 THEN 'Wide-body'
                 WHEN UPPER(segmentsEquipmentDescription) LIKE '%ERJ%' OR UPPER(segmentsEquipmentDescription) LIKE '%CRJ%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%EMBRAER%' OR UPPER(segmentsEquipmentDescription) LIKE '%REGIONAL%'
                 THEN 'Regional Jet'
                 WHEN UPPER(segmentsEquipmentDescription) LIKE '%737%' OR UPPER(segmentsEquipmentDescription) LIKE '%A320%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A321%' OR UPPER(segmentsEquipmentDescription) LIKE '%A319%'
                 THEN 'Narrow-body'
                 ELSE 'Other' END AS aircraftCategory,
            COUNT(*) AS flightCount,
            ROUND(AVG(CAST(totalFare AS DOUBLE)),2) AS avgFare,
            ROUND(AVG(CAST(totalTravelDistance AS DOUBLE)),0) AS avgDistance
        FROM {tbl}
        WHERE segmentsEquipmentDescription IS NOT NULL AND segmentsEquipmentDescription != ''
        GROUP BY CASE WHEN UPPER(segmentsEquipmentDescription) LIKE '%777%' OR UPPER(segmentsEquipmentDescription) LIKE '%787%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A350%' OR UPPER(segmentsEquipmentDescription) LIKE '%A330%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A380%' OR UPPER(segmentsEquipmentDescription) LIKE '%767%'
                 THEN 'Wide-body'
                 WHEN UPPER(segmentsEquipmentDescription) LIKE '%ERJ%' OR UPPER(segmentsEquipmentDescription) LIKE '%CRJ%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%EMBRAER%' OR UPPER(segmentsEquipmentDescription) LIKE '%REGIONAL%'
                 THEN 'Regional Jet'
                 WHEN UPPER(segmentsEquipmentDescription) LIKE '%737%' OR UPPER(segmentsEquipmentDescription) LIKE '%A320%'
                      OR UPPER(segmentsEquipmentDescription) LIKE '%A321%' OR UPPER(segmentsEquipmentDescription) LIKE '%A319%'
                 THEN 'Narrow-body'
                 ELSE 'Other' END
        ORDER BY avgFare DESC
        """
        _, rows = run_query(sql)
        return {"data": [clean_row(r) for r in rows], "query": sql}
    return jsonify(cached_query("aircraft_pricing", _query))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize Spark on startup
    print("Initializing SparkSession with Hive support...")
    get_spark()
    print("SparkSession ready. Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
