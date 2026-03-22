"""
Full Optimization: Convert ALL 80M rows to ORC (~7 GB compressed)
Creates itineraries_orc partitioned by startingAirport.
Estimated time: 60-120 minutes.

Usage:
  export SPARK_HOME=/opt/spark-3.5.3
  export HADOOP_CONF_DIR=/opt/hadoop-3.4.0/etc/hadoop
  export YARN_CONF_DIR=/opt/hadoop-3.4.0/etc/hadoop  
  export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
  python3 quick_optimize.py
"""
from pyspark.sql import SparkSession
import time

print("=" * 60)
print("  Quick Optimization: CSV → Sampled ORC (Partitioned)")
print("=" * 60)

spark = (
    SparkSession.builder
    .appName("SkyQuery-QuickOptimize")
    .master("yarn")
    .config("spark.submit.deployMode", "client")
    .config("spark.sql.shuffle.partitions", "8")
    .config("spark.driver.memory", "2g")
    .config("spark.executor.memory", "2g")
    .config("spark.executor.instances", "2")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sql("USE ticketmeta09")

# Step 1: Drop old table if exists
print("\n[1/3] Dropping old itineraries_orc if exists...")
spark.sql("DROP TABLE IF EXISTS itineraries_orc")

# Step 2: Create partitioned ORC table
print("[2/3] Creating optimized ORC table structure...")
spark.sql("""
    CREATE TABLE itineraries_orc (
        legId               STRING,
        searchDate           STRING,
        flightDate           STRING,
        destinationAirport   STRING,
        fareBasisCode        STRING,
        travelDuration       STRING,
        elapsedDays          STRING,
        isBasicEconomy       STRING,
        isRefundable         STRING,
        isNonStop            STRING,
        baseFare             DOUBLE,
        totalFare            DOUBLE,
        seatsRemaining       INT,
        totalTravelDistance   DOUBLE,
        segmentsDepartureTimeEpochSeconds STRING,
        segmentsDepartureTimeRaw         STRING,
        segmentsArrivalTimeEpochSeconds  STRING,
        segmentsArrivalTimeRaw           STRING,
        segmentsArrivalAirportCode       STRING,
        segmentsDepartureAirportCode     STRING,
        segmentsAirlineName              STRING,
        segmentsAirlineCode              STRING,
        segmentsEquipmentDescription     STRING,
        segmentsDurationInSeconds        DOUBLE,
        segmentsDistance                 STRING,
        segmentsCabinCode                STRING
    )
    PARTITIONED BY (startingAirport STRING)
    STORED AS ORC
    TBLPROPERTIES ('orc.compress'='SNAPPY')
""")

# Step 3: Insert ALL data (80M rows → ~7 GB ORC)
print("[3/3] Inserting ALL rows into ORC table (this takes ~60-120 min)...")
print("      Monitor at http://node-master:8088\n")

start = time.time()
spark.sql("""
    INSERT OVERWRITE TABLE itineraries_orc PARTITION (startingAirport)
    SELECT
        legId, searchDate, flightDate, destinationAirport,
        fareBasisCode, travelDuration, elapsedDays,
        isBasicEconomy, isRefundable, isNonStop,
        CAST(baseFare AS DOUBLE),
        CAST(totalFare AS DOUBLE),
        CAST(seatsRemaining AS INT),
        CAST(totalTravelDistance AS DOUBLE),
        segmentsDepartureTimeEpochSeconds, segmentsDepartureTimeRaw,
        segmentsArrivalTimeEpochSeconds, segmentsArrivalTimeRaw,
        segmentsArrivalAirportCode, segmentsDepartureAirportCode,
        segmentsAirlineName, segmentsAirlineCode,
        segmentsEquipmentDescription,
        CAST(segmentsDurationInSeconds AS DOUBLE),
        segmentsDistance, segmentsCabinCode,
        startingAirport
    FROM ext_itineraries
""")
elapsed = time.time() - start

# Verify
count = spark.sql("SELECT COUNT(*) AS cnt FROM itineraries_orc").collect()[0]["cnt"]
partitions = spark.sql("SHOW PARTITIONS itineraries_orc").collect()

print(f"\n{'=' * 60}")
print(f"  DONE in {elapsed:.0f} seconds!")
print(f"  Rows in itineraries_orc: {count:,}")
print(f"  Partitions (airports): {len(partitions)}")
print(f"  Queries should now be 10-50x faster!")
print(f"  Restart flask_api.py to auto-detect the new table.")
print(f"{'=' * 60}")

# Quick test
print("\nQuick test: cheapest ATL → LAX")
spark.sql("""
    SELECT startingAirport, destinationAirport,
           ROUND(MIN(totalFare), 2) AS cheapest,
           COUNT(*) AS cnt
    FROM itineraries_orc
    WHERE startingAirport = 'ATL' AND destinationAirport = 'LAX'
    GROUP BY startingAirport, destinationAirport
""").show()

spark.stop()
