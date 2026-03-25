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


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize Spark on startup
    print("Initializing SparkSession with Hive support...")
    get_spark()
    print("SparkSession ready. Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
