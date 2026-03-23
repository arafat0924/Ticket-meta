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
import threading
import time

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# PySpark Session (singleton)
# ---------------------------------------------------------------------------
_spark = None
_spark_status = "cold"
_spark_error = ""
_spark_lock = threading.Lock()


def _build_spark_session():
    """Create a Spark session object (blocking)."""
    spark_master = os.environ.get("SPARK_MASTER", "local[*]")

    builder = (
        SparkSession.builder
        .appName("SkyQuery-FlaskAPI")
        .master(spark_master)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.hive.metastore.jars", "builtin")
        .config("spark.sql.catalogImplementation", "hive")
    )

    if spark_master.startswith("yarn"):
        builder = (
            builder
            .config("spark.submit.deployMode", "client")
            .config("spark.executor.instances", "2")
            .config("spark.yarn.queue", "default")
        )

    metastore_uri = os.environ.get("HIVE_METASTORE_URIS", "thrift://localhost:9083")
    if metastore_uri:
        builder = builder.config("hive.metastore.uris", metastore_uri)

    use_extra_packages = os.environ.get("SPARK_USE_EXTRA_PACKAGES", "0") == "1"
    if use_extra_packages:
        builder = builder.config(
            "spark.jars.packages",
            "org.apache.logging.log4j:log4j-api:2.10.0,"
            "org.apache.derby:derby:10.14.1.0,"
            "org.apache.hive:hive-metastore:3.1.3,"
            "org.apache.hive:hive-exec:3.1.3,"
            "org.apache.hive:hive-common:3.1.3,"
            "org.apache.hive:hive-serde:3.1.3,"
            "com.google.guava:guava:19.0,"
            "org.apache.hadoop:hadoop-client-api:3.1.0,"
            "org.apache.hadoop:hadoop-client-runtime:3.1.0"
        ).config("spark.sql.hive.metastore.version", "3.1.3")

    spark = builder.enableHiveSupport().getOrCreate()

    preferred_db = os.environ.get("FLIGHT_DB", "ticketmeta09")
    try:
        spark.sql(f"USE {preferred_db}")
        print(f"Using database: {preferred_db}")
    except Exception as e:
        print(f"Database '{preferred_db}' not found. Falling back to current schema. Details: {e}")

    try:
        tables = [r["tableName"] for r in spark.sql("SHOW TABLES").collect()]
        if "itineraries_orc" in tables:
            print("Found optimized itineraries_orc table!")
            print("Caching itineraries_orc for faster repeated queries...")
            spark.sql("CACHE LAZY TABLE itineraries_orc")
        else:
            print("No optimized table found. Consider running the optimization script.")
            print("Skipping external-table cache warm-up to avoid metastore compatibility issues.")
    except Exception as e:
        print(f"Cache/optimization check: {e}")

    return spark


def _spark_init_worker():
    """Initialize Spark in background to avoid blocking request threads."""
    global _spark, _spark_status, _spark_error
    try:
        _spark = _build_spark_session()
        _spark_status = "ready"
        _spark_error = ""
    except Exception as e:
        _spark = None
        _spark_status = "error"
        _spark_error = str(e)


def ensure_spark_started():
    """Ensure background Spark initialization is started exactly once."""
    global _spark, _spark_status, _spark_error
    with _spark_lock:
        if _spark is not None:
            try:
                if not _spark._jsc.sc().isStopped():
                    _spark_status = "ready"
                    return
            except Exception:
                pass
            _spark = None
            _spark_status = "cold"

        if _spark_status == "initializing":
            return

        _spark_status = "initializing"
        _spark_error = ""
        threading.Thread(target=_spark_init_worker, daemon=True).start()

def get_spark():
    """Get Spark quickly if ready; start background init if needed."""
    ensure_spark_started()
    if _spark_status == "ready":
        return _spark
    return None


def get_flight_table():
    """Return the best available flight table name.

    Avoid ext_itineraries as implicit fallback because some Hive metastore
    deployments expose API incompatibilities for that external table.
    """
    configured = os.environ.get("FLIGHT_TABLE", "").strip()
    if configured:
        return configured

    spark = get_spark()
    if spark is None:
        return "itineraries_orc"

    try:
        tables = [r["tableName"] for r in spark.sql("SHOW TABLES").collect()]
        # Prefer optimized/internal tables first.
        for candidate in ["itineraries_orc", "itineraries", "flight_prices", "flights"]:
            if candidate in tables:
                return candidate

        # As a last resort, use any non-external-looking table name.
        safe_tables = [t for t in tables if not t.lower().startswith("ext_") and t.lower() != "ext_itineraries"]
        if safe_tables:
            return safe_tables[0]
    except Exception:
        pass

    # Safe default (may still be missing, but avoids known broken external table fallback).
    return "itineraries_orc"


def get_table_columns(table_name):
    """Return lowercase column names for a table, or empty list if unavailable."""
    spark = get_spark()
    if spark is None:
        return []
    try:
        return [c.lower() for c in spark.table(table_name).columns]
    except Exception:
        return []


def pick_first_column(columns, candidates):
    """Pick the first existing column name from candidates."""
    cols = set(columns)
    for cand in candidates:
        c = cand.lower()
        if c in cols:
            return c
    return None


def alias_metric_expr(column_name, alias_name, cast_type="DOUBLE"):
    """Build a nullable SQL metric expression with a stable alias."""
    if column_name:
        return f"ROUND(CAST({column_name} AS {cast_type}), 2) AS {alias_name}"
    return f"CAST(NULL AS {cast_type}) AS {alias_name}"


def run_query(sql):
    """Execute a Spark SQL / HiveQL query and return rows + column names."""
    spark = get_spark()
    if spark is None:
        raise TimeoutError("Spark is warming up. Please retry in 20-40 seconds.")
    df = spark.sql(sql)
    cols = df.columns
    rows = [row.asDict() for row in df.collect()]
    return cols, rows


def _is_metastore_ext_error(msg):
    m = (msg or "").lower()
    return "unable to fetch table ext_itineraries" in m or ("unable to fetch table" in m and "invalid method name" in m)


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
@app.route("/api.now/health")
def health():
    # Fast health check by default so frontend status polling does not block on Spark startup.
    deep = request.args.get("deep", "0") == "1"
    if not deep:
        return jsonify({"status": "connected", "mode": "quick"})

    try:
        spark = get_spark()
        if spark is None:
            return jsonify({"status": "warming-up", "mode": "deep"}), 503
        spark.sql("SELECT 1").collect()
        return jsonify({"status": "connected", "mode": "deep"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/tables")
@app.route("/api.now/tables")
def tables():
    try:
        spark = get_spark()
        df = spark.sql("SHOW TABLES")
        t = [row["tableName"] for row in df.collect()]
        return jsonify({"tables": t})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/table-schema")
@app.route("/api.now/table-schema")
def table_schema():
    table = request.args.get("table", "").strip()
    if not table:
        return jsonify({"error": "table is required"}), 400

    spark = get_spark()
    try:
        df = spark.table(table)
        schema = [{"name": name, "type": dtype} for name, dtype in df.dtypes]
        return jsonify({"table": table, "columns": schema})
    except Exception as e:
        return jsonify({"error": str(e), "table": table}), 500


# ---------------------------------------------------------------------------
# 1. Search Flights
#    GET /api/search-flights?origin=MIA&dest=SFO&nonstop=true&sort=cheapest&limit=20
# ---------------------------------------------------------------------------
@app.route("/api/search-flights")
@app.route("/api.now/search-flights")
def search_flights():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()
    nonstop = request.args.get("nonstop", "false").lower() == "true"
    sort = request.args.get("sort", "cheapest")
    limit = max(1, min(int(request.args.get("limit", 20)), 100))
    date = request.args.get("date", "")
    allow_slow = request.args.get("allowSlow", "0") == "1"
    sample_cap = max(limit, min(int(request.args.get("sampleCap", 40000)), 100000))

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
    select_cols = """
        legId, searchDate, flightDate, startingAirport, destinationAirport,
        travelDuration, isNonStop, isBasicEconomy, isRefundable,
        CAST(baseFare AS DOUBLE) AS baseFare,
        CAST(totalFare AS DOUBLE) AS totalFare,
        CAST(seatsRemaining AS INT) AS seatsRemaining,
        CAST(totalTravelDistance AS DOUBLE) AS totalTravelDistance,
        segmentsDepartureTimeRaw, segmentsArrivalTimeRaw,
        segmentsArrivalAirportCode, segmentsDepartureAirportCode,
        segmentsAirlineName, segmentsAirlineCode,
        segmentsEquipmentDescription, segmentsCabinCode
    """

    if allow_slow or date:
        # Exact mode: potentially slower but global ordering is preserved.
        sql = f"""
            SELECT {select_cols}
            FROM {tbl}
            WHERE {where}
            ORDER BY {order}
            LIMIT {limit}
        """
    else:
        # Fast mode: avoid global sorting on huge datasets to keep UI responsive.
        sql = f"""
            SELECT {select_cols}
            FROM {tbl}
            WHERE {where}
            LIMIT {limit}
        """

    try:
        cols, rows = run_query(sql)
        flights = [clean_row(r) for r in rows]
        return jsonify({"flights": flights, "count": len(flights), "query": sql.strip()})
    except Exception as e:
        status_code = 503 if isinstance(e, TimeoutError) else 500
        return jsonify({"error": str(e), "query": sql.strip()}), status_code


# ---------------------------------------------------------------------------
# 2. Where to Fly
#    GET /api/where-to-fly?origin=ATL&limit=10
# ---------------------------------------------------------------------------
@app.route("/api/where-to-fly")
@app.route("/api.now/where-to-fly")
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
@app.route("/api.now/when-to-fly")
def when_to_fly():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()
    allow_raw = request.args.get("allowRaw", "0") == "1"
    # Reduced default cap from 250k to 10k to prevent timeouts
    raw_sample_cap = max(5000, min(int(request.args.get("rawSampleCap", 10000)), 50000))

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    spark = get_spark()
    if spark is None:
        return jsonify({"error": "Spark is warming up. Please retry in 20-40 seconds."}), 503
    tables = [r["tableName"] for r in spark.sql("SHOW TABLES").collect()]

    sql = ""
    if "agg_price_by_month" in tables:
        cols = get_table_columns("agg_price_by_month")
        origin_col = pick_first_column(cols, ["startingAirport", "origin", "originAirport", "origin_airport"])
        dest_col = pick_first_column(cols, ["destinationAirport", "dest", "destination", "destAirport", "destination_airport"])
        month_col = pick_first_column(cols, ["month", "flight_month", "year_month"])
        min_col = pick_first_column(cols, ["minFare", "min_fare"])
        avg_col = pick_first_column(cols, ["avgFare", "avg_fare"])
        max_col = pick_first_column(cols, ["maxFare", "max_fare"])
        generic_fare_col = pick_first_column(cols, ["fare", "totalFare", "price", "meanFare", "averageFare"])
        count_col = pick_first_column(cols, ["flightCount", "flight_count", "count", "records", "record_count"])

        # Accept partial aggregate schemas and still return a stable API shape.
        min_expr = alias_metric_expr(min_col or generic_fare_col, "minFare")
        avg_expr = alias_metric_expr(avg_col or generic_fare_col or min_col or max_col, "avgFare")
        max_expr = alias_metric_expr(max_col or generic_fare_col or avg_col or min_col, "maxFare")
        count_expr = f"CAST({count_col} AS BIGINT) AS flightCount" if count_col else "CAST(NULL AS BIGINT) AS flightCount"

        if all([origin_col, dest_col, month_col]) and (min_col or avg_col or max_col or generic_fare_col):
            sql = f"""
                SELECT {month_col} AS month,
                       {min_expr},
                       {avg_expr},
                       {max_expr},
                       {count_expr}
                FROM agg_price_by_month
                WHERE UPPER({origin_col}) = '{origin}'
                  AND UPPER({dest_col}) = '{dest}'
                ORDER BY month ASC
            """

    if not sql and allow_raw:
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

    if not sql:
        # Graceful fallback: use a capped sample from the raw table so users still
        # get trends even when aggregate tables are missing or have schema drift.
        tbl = get_flight_table()
        sql = f"""
            SELECT SUBSTR(flightDate, 1, 7) AS month,
                   ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
                   ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare,
                   COUNT(*) AS flightCount
            FROM (
                SELECT flightDate, totalFare
                FROM {tbl}
                WHERE startingAirport = '{origin}'
                  AND destinationAirport = '{dest}'
                LIMIT {raw_sample_cap}
            ) t
            GROUP BY SUBSTR(flightDate, 1, 7)
            ORDER BY month ASC
        """

    try:
        cols, rows = run_query(sql)
        months = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "dest": dest, "months": months, "query": sql.strip()})
    except Exception as e:
        msg = str(e)
        if _is_metastore_ext_error(msg):
            return jsonify({
                "error": "Flight data table is not compatible with current Hive metastore API. Please use the optimized internal table (itineraries_orc).",
                "query": sql.strip()
            }), 503
        return jsonify({"error": msg, "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 4. Airline Comparison
#    GET /api/airline-comparison?origin=ATL&dest=LAX
# ---------------------------------------------------------------------------
@app.route("/api/airline-comparison")
@app.route("/api.now/airline-comparison")
def airline_comparison():
    origin = request.args.get("origin", "").upper()
    dest = request.args.get("dest", "").upper()
    allow_raw = request.args.get("allowRaw", "0") == "1"
    # Reduced default cap from 250k to 10k to prevent timeouts
    raw_sample_cap = max(5000, min(int(request.args.get("rawSampleCap", 10000)), 50000))

    if not origin or not dest:
        return jsonify({"error": "origin and dest are required"}), 400

    spark = get_spark()
    if spark is None:
        return jsonify({"error": "Spark is warming up. Please retry in 20-40 seconds."}), 503
    tables = [r["tableName"] for r in spark.sql("SHOW TABLES").collect()]

    sql = ""
    if "agg_airline_comparison" in tables:
        cols = get_table_columns("agg_airline_comparison")
        origin_col = pick_first_column(cols, ["startingAirport", "origin", "originAirport", "origin_airport"])
        dest_col = pick_first_column(cols, ["destinationAirport", "dest", "destination", "destAirport", "destination_airport"])
        airline_col = pick_first_column(cols, ["airline", "segmentsAirlineName", "airline_name"])
        min_col = pick_first_column(cols, ["minFare", "min_fare"])
        avg_col = pick_first_column(cols, ["avgFare", "avg_fare"])
        max_col = pick_first_column(cols, ["maxFare", "max_fare"])
        generic_fare_col = pick_first_column(cols, ["fare", "totalFare", "price", "meanFare", "averageFare"])
        count_col = pick_first_column(cols, ["flightCount", "flight_count", "count", "records", "record_count"])

        min_expr = alias_metric_expr(min_col or generic_fare_col, "minFare")
        avg_expr = alias_metric_expr(avg_col or generic_fare_col or min_col or max_col, "avgFare")
        max_expr = alias_metric_expr(max_col or generic_fare_col or avg_col or min_col, "maxFare")
        count_expr = f"CAST({count_col} AS BIGINT) AS flightCount" if count_col else "CAST(NULL AS BIGINT) AS flightCount"

        if all([origin_col, dest_col, airline_col]) and (min_col or avg_col or max_col or generic_fare_col):
            sql = f"""
                SELECT {airline_col} AS airline,
                       {min_expr},
                       {avg_expr},
                       {max_expr},
                       {count_expr}
                FROM agg_airline_comparison
                WHERE UPPER({origin_col}) = '{origin}'
                  AND UPPER({dest_col}) = '{dest}'
                ORDER BY avgFare ASC
            """

    if not sql and allow_raw:
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

    if not sql:
        # Graceful fallback with capped raw scan to avoid hard-failing the UI.
        tbl = get_flight_table()
        sql = f"""
            SELECT segmentsAirlineName AS airline,
                   ROUND(MIN(CAST(totalFare AS DOUBLE)), 2) AS minFare,
                   ROUND(AVG(CAST(totalFare AS DOUBLE)), 2) AS avgFare,
                   ROUND(MAX(CAST(totalFare AS DOUBLE)), 2) AS maxFare,
                   COUNT(*) AS flightCount
            FROM (
                SELECT segmentsAirlineName, totalFare
                FROM {tbl}
                WHERE startingAirport = '{origin}'
                  AND destinationAirport = '{dest}'
                LIMIT {raw_sample_cap}
            ) t
            GROUP BY segmentsAirlineName
            ORDER BY avgFare ASC
        """

    try:
        cols, rows = run_query(sql)
        airlines = [clean_row(r) for r in rows]
        return jsonify({"origin": origin, "dest": dest, "airlines": airlines, "query": sql.strip()})
    except Exception as e:
        msg = str(e)
        if _is_metastore_ext_error(msg):
            return jsonify({
                "error": "Flight data table is not compatible with current Hive metastore API. Please use the optimized internal table (itineraries_orc).",
                "query": sql.strip()
            }), 503
        return jsonify({"error": msg, "query": sql.strip()}), 500


# ---------------------------------------------------------------------------
# 5. Airport Search
#    GET /api/airports?q=Tokyo
# ---------------------------------------------------------------------------
@app.route("/api/airports")
@app.route("/api.now/airports")
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
@app.route("/api.now/chatbot", methods=["POST"])
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
    print("Initializing Flight Search API...")
    try:
        # Ensure Spark is starting in background
        ensure_spark_started()
        
        print("Starting Flask server on port 5000...")
        # Threaded mode keeps health and other lightweight routes responsive
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start server: {e}")
        # Write to a fallback error log just in case stdout is lost
        with open("server_error.log", "w") as f:
            f.write(str(e))
        raise
