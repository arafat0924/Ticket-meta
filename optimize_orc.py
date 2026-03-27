"""
PySpark ORC Optimization Script
================================
Converts the 30GB CSV ext_itineraries table (80M rows) to ORC format with:
  1. Snappy compression
  2. Partitioning by startingAirport (ATL, LAX, SFO, etc.)
  3. Pre-cast string fare/numeric columns to proper types (DOUBLE, INT, BIGINT)
  4. Eliminates repeated CSV parsing → queries go from minutes to seconds

Usage (run on VM):
    python3 optimize_orc.py

Or via spark-submit:
    spark-submit --master yarn --deploy-mode client optimize_orc.py
"""

import os
import sys
import time

# ── Environment Setup ────────────────────────────────────────────────────────
if os.name != 'nt':
    _env = {
        "JAVA_HOME": "/usr/lib/jvm/java-11-openjdk-amd64",
        "HADOOP_HOME": "/opt/hadoop-3.3.6",
        "HADOOP_CONF_DIR": "/opt/hadoop-3.3.6/etc/hadoop",
        "SPARK_HOME": "/opt/spark-3.5.3",
        "HIVE_HOME": "/opt/apache-hive-4.0.1",
    }
    for k, v in _env.items():
        if k not in os.environ or not os.environ[k]:
            os.environ[k] = v
    extra = [f"{_env['HADOOP_HOME']}/bin", f"{_env['SPARK_HOME']}/bin", f"{_env['HIVE_HOME']}/bin"]
    os.environ["PATH"] = ":".join(extra) + ":" + os.environ.get("PATH", "")

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, LongType

# ── Configuration ────────────────────────────────────────────────────────────
DATABASE = "ticketmeta09"
SOURCE_TABLE = "ext_itineraries"
TARGET_TABLE = "itineraries_orc"
MYSQL_DRIVER = "/opt/apache-hive-4.0.1/lib/mysql-connector-j-8.4.0.jar"

# Columns to cast from STRING → proper numeric types
DOUBLE_COLS = [
    "baseFare", "totalFare", "totalTravelDistance",
    "segmentsDistance",
]
INT_COLS = [
    "seatsRemaining", "elapsedDays",
]
BIGINT_COLS = [
    "segmentsDepartureTimeEpochSeconds",
    "segmentsArrivalTimeEpochSeconds",
    "segmentsDurationInSeconds",
]


def create_spark():
    """Create SparkSession optimized for the ORC conversion job."""
    builder = (
        SparkSession.builder
        .appName("ORC-Optimization-ext_itineraries")
        .master("yarn")
        .config("spark.submit.deployMode", "client")
        .config("spark.driver.extraClassPath", MYSQL_DRIVER)
        .config("spark.executor.extraClassPath", MYSQL_DRIVER)
        .enableHiveSupport()
        # ── Performance tuning for 30GB conversion ──
        .config("spark.driver.memory", "4g")
        .config("spark.executor.memory", "4g")
        .config("spark.executor.instances", "3")
        .config("spark.executor.cores", "2")
        .config("spark.sql.shuffle.partitions", "200")
        # ORC + Snappy
        .config("spark.sql.orc.compression.codec", "snappy")
        .config("spark.sql.hive.convertMetastoreOrc", "true")
        # Adaptive Query Execution (Spark 3.x)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.yarn.queue", "default")
    )
    return builder.getOrCreate()


def main():
    print("=" * 70)
    print("  PySpark ORC Optimization Script")
    print("  Source: {}.{} (CSV, ~80M rows, ~30GB)".format(DATABASE, SOURCE_TABLE))
    print("  Target: {}.{} (ORC + Snappy, partitioned by startingAirport)".format(DATABASE, TARGET_TABLE))
    print("=" * 70)

    t0 = time.time()

    # ── Step 1: Create SparkSession ──────────────────────────────────────
    print("\n[1/6] Creating SparkSession on YARN...")
    spark = create_spark()
    spark.sql(f"USE {DATABASE}")
    print(f"  ✅ Connected to database: {DATABASE}")
    print(f"  ⏱  Spark init: {time.time() - t0:.1f}s")

    # ── Step 2: Inspect source table ─────────────────────────────────────
    print(f"\n[2/6] Inspecting source table: {SOURCE_TABLE}...")
    row_count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {SOURCE_TABLE}").collect()[0]["cnt"]
    print(f"  📊 Source row count: {row_count:,}")

    # Get distinct airport codes for partition preview
    airports = spark.sql(f"""
        SELECT startingAirport, COUNT(*) AS cnt
        FROM {SOURCE_TABLE}
        WHERE startingAirport IS NOT NULL AND startingAirport != ''
        GROUP BY startingAirport
        ORDER BY cnt DESC
    """).collect()
    print(f"  🏢 Unique startingAirport values: {len(airports)}")
    for ap in airports[:10]:
        print(f"      {ap['startingAirport']}: {ap['cnt']:,} rows")
    if len(airports) > 10:
        print(f"      ... and {len(airports) - 10} more")

    # ── Step 3: Read source + cast columns ───────────────────────────────
    print(f"\n[3/6] Reading {SOURCE_TABLE} and casting columns...")
    df = spark.table(SOURCE_TABLE)

    # Pre-cast fare/numeric columns from STRING → proper types
    for col_name in DOUBLE_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(DoubleType()))
            print(f"  📐 Cast {col_name} → DOUBLE")

    for col_name in INT_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(IntegerType()))
            print(f"  📐 Cast {col_name} → INT")

    for col_name in BIGINT_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(LongType()))
            print(f"  📐 Cast {col_name} → BIGINT")

    # Clean partition column: remove nulls/blanks, trim whitespace
    df = df.withColumn(
        "startingAirport",
        F.trim(F.upper(F.col("startingAirport")))
    ).filter(
        (F.col("startingAirport").isNotNull()) &
        (F.col("startingAirport") != "")
    )

    print(f"  ✅ Schema ready with {len(df.columns)} columns")

    # ── Step 4: Drop old target table if exists ──────────────────────────
    print(f"\n[4/6] Dropping old {TARGET_TABLE} if it exists...")
    spark.sql(f"DROP TABLE IF EXISTS {TARGET_TABLE}")
    print(f"  ✅ Old table dropped (if any)")

    # ── Step 5: Write as ORC with Snappy + partition by startingAirport ──
    print(f"\n[5/6] Writing ORC table with Snappy compression...")
    print(f"  📦 Partitioned by: startingAirport")
    print(f"  🗜️  Compression: Snappy")
    print(f"  ⏳ This may take 15-45 minutes for 80M rows...")

    t_write = time.time()

    # Use Hive-compatible write to register in metastore
    df.write \
        .mode("overwrite") \
        .format("orc") \
        .option("compression", "snappy") \
        .partitionBy("startingAirport") \
        .saveAsTable(TARGET_TABLE)

    write_time = time.time() - t_write
    print(f"  ✅ ORC table created in {write_time:.1f}s ({write_time/60:.1f} min)")

    # ── Step 6: Verify & benchmark ───────────────────────────────────────
    print(f"\n[6/6] Verifying optimized table...")

    # Row count
    orc_count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {TARGET_TABLE}").collect()[0]["cnt"]
    print(f"  📊 ORC row count: {orc_count:,} (source: {row_count:,})")

    # Table size
    try:
        spark.sql(f"ANALYZE TABLE {TARGET_TABLE} COMPUTE STATISTICS")
        desc = spark.sql(f"DESCRIBE EXTENDED {TARGET_TABLE}").collect()
        for row in desc:
            if "totalSize" in str(row) or "rawDataSize" in str(row) or "Statistics" in str(row):
                print(f"  💾 {row}")
    except Exception as e:
        print(f"  ⚠️  Stats computation: {e}")

    # Benchmark: compare query time CSV vs ORC
    print(f"\n  ⏱  Benchmarking query speed...")

    # Benchmark on ORC
    t1 = time.time()
    result_orc = spark.sql(f"""
        SELECT startingAirport, destinationAirport,
               MIN(totalFare) AS minFare,
               AVG(totalFare) AS avgFare,
               COUNT(*) AS cnt
        FROM {TARGET_TABLE}
        WHERE startingAirport = 'ATL' AND destinationAirport = 'LAX'
        GROUP BY startingAirport, destinationAirport
    """).collect()
    orc_time = time.time() - t1

    # Benchmark on CSV
    t2 = time.time()
    result_csv = spark.sql(f"""
        SELECT startingAirport, destinationAirport,
               MIN(CAST(totalFare AS DOUBLE)) AS minFare,
               AVG(CAST(totalFare AS DOUBLE)) AS avgFare,
               COUNT(*) AS cnt
        FROM {SOURCE_TABLE}
        WHERE startingAirport = 'ATL' AND destinationAirport = 'LAX'
        GROUP BY startingAirport, destinationAirport
    """).collect()
    csv_time = time.time() - t2

    speedup = csv_time / orc_time if orc_time > 0 else 0

    print(f"\n  {'='*50}")
    print(f"  📊 BENCHMARK RESULTS (ATL → LAX query)")
    print(f"  {'='*50}")
    print(f"  CSV (ext_itineraries):  {csv_time:.2f}s")
    print(f"  ORC (itineraries_orc):  {orc_time:.2f}s")
    print(f"  Speedup:               {speedup:.1f}x faster! 🚀")
    if result_orc:
        r = result_orc[0]
        print(f"  Result: minFare=${r['minFare']:.2f}, avgFare=${r['avgFare']:.2f}, count={r['cnt']:,}")

    # Show partitions
    partitions = spark.sql(f"SHOW PARTITIONS {TARGET_TABLE}").collect()
    print(f"\n  📂 Total partitions: {len(partitions)}")

    total_time = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  🎉 OPTIMIZATION COMPLETE!")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Source: {DATABASE}.{SOURCE_TABLE} (CSV, {row_count:,} rows)")
    print(f"  Target: {DATABASE}.{TARGET_TABLE} (ORC+Snappy, {orc_count:,} rows)")
    print(f"  Partitions: {len(partitions)} (by startingAirport)")
    print(f"  Query speedup: ~{speedup:.0f}x faster")
    print(f"{'='*70}")

    # Update flask_api.py hint
    print(f"\n  💡 The Flask API will auto-detect '{TARGET_TABLE}' on next request.")
    print(f"     No code changes needed — get_flight_table() checks for it.")

    spark.stop()
    print("\n  SparkSession closed. Done! ✈️")


if __name__ == "__main__":
    main()
