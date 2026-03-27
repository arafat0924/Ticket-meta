"""
PySpark ORC Optimization Script
================================
Converts the 30GB CSV ext_itineraries table (80M rows) to ORC format with:
  1. Snappy compression
  2. Partitioning by startingAirport (ATL, LAX, SFO, etc.)
  3. Pre-cast string fare/numeric columns to proper types (DOUBLE, INT, BIGINT)
  4. Eliminates repeated CSV parsing → queries go from minutes to seconds

Usage (run on VM):
    spark-submit --master yarn --deploy-mode client /home/arafat/optimize_orc.py
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
        # ── Performance tuning (conservative for stability) ──
        .config("spark.driver.memory", "1g")
        .config("spark.executor.memory", "2g")
        .config("spark.executor.instances", "1")
        .config("spark.executor.cores", "2")
        .config("spark.sql.shuffle.partitions", "50")
        # ── Fault tolerance ──
        .config("spark.network.timeout", "800s")
        .config("spark.executor.heartbeatInterval", "200s")
        .config("spark.rpc.askTimeout", "600s")
        .config("spark.task.maxFailures", "8")
        .config("spark.yarn.executor.memoryOverhead", "512m")
        .config("spark.speculation", "false")
        .config("spark.locality.wait", "0s")
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
    print("  Target: {}.{} (ORC + Snappy, partitioned)".format(DATABASE, TARGET_TABLE))
    print("=" * 70)
    sys.stdout.flush()

    t0 = time.time()

    # ── Step 1: Create SparkSession ──────────────────────────────────────
    print("\n[1/4] Creating SparkSession on YARN...")
    sys.stdout.flush()
    spark = create_spark()
    spark.sql(f"USE {DATABASE}")
    print(f"  Connected to database: {DATABASE}")
    print(f"  Spark init: {time.time() - t0:.1f}s")
    sys.stdout.flush()

    # ── Step 2: Read source + cast columns ───────────────────────────────
    print(f"\n[2/4] Reading {SOURCE_TABLE} and casting columns...")
    sys.stdout.flush()
    df = spark.table(SOURCE_TABLE)

    # Pre-cast fare/numeric columns from STRING → proper types
    for col_name in DOUBLE_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(DoubleType()))
            print(f"  Cast {col_name} -> DOUBLE")

    for col_name in INT_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(IntegerType()))
            print(f"  Cast {col_name} -> INT")

    for col_name in BIGINT_COLS:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(LongType()))
            print(f"  Cast {col_name} -> BIGINT")

    # Clean partition column: remove nulls/blanks, trim whitespace
    df = df.withColumn(
        "startingAirport",
        F.trim(F.upper(F.col("startingAirport")))
    ).filter(
        (F.col("startingAirport").isNotNull()) &
        (F.col("startingAirport") != "")
    )

    print(f"  Schema ready with {len(df.columns)} columns")
    sys.stdout.flush()

    # ── Step 3: Drop old + Write ORC ─────────────────────────────────────
    print(f"\n[3/4] Writing ORC table with Snappy compression...")
    print(f"  Partitioned by: startingAirport")
    print(f"  Compression: Snappy")
    print(f"  This may take 20-60 minutes for ~80M rows...")
    sys.stdout.flush()

    spark.sql(f"DROP TABLE IF EXISTS {TARGET_TABLE}")

    t_write = time.time()

    # Use Hive-compatible write to register in metastore
    df.write \
        .mode("overwrite") \
        .format("orc") \
        .option("compression", "snappy") \
        .partitionBy("startingAirport") \
        .saveAsTable(TARGET_TABLE)

    write_time = time.time() - t_write
    print(f"  ORC table created in {write_time:.1f}s ({write_time/60:.1f} min)")
    sys.stdout.flush()

    # ── Step 4: Quick verify ─────────────────────────────────────────────
    print(f"\n[4/4] Quick verification...")
    sys.stdout.flush()

    # Quick test query on ORC
    t1 = time.time()
    result = spark.sql(f"""
        SELECT COUNT(*) AS cnt,
               MIN(totalFare) AS minFare,
               ROUND(AVG(totalFare), 2) AS avgFare
        FROM {TARGET_TABLE}
        WHERE startingAirport = 'ATL'
    """).collect()
    orc_time = time.time() - t1

    if result:
        r = result[0]
        print(f"  ORC test query (ATL flights): {orc_time:.2f}s")
        print(f"  count={r['cnt']:,}, minFare=${r['minFare']:.2f}, avgFare=${r['avgFare']:.2f}")

    # Show partitions count
    try:
        partitions = spark.sql(f"SHOW PARTITIONS {TARGET_TABLE}").collect()
        print(f"  Total partitions: {len(partitions)}")
    except:
        pass

    total_time = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  OPTIMIZATION COMPLETE!")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Target: {DATABASE}.{TARGET_TABLE} (ORC+Snappy)")
    print(f"{'='*70}")
    sys.stdout.flush()

    spark.stop()
    print("\n  SparkSession closed. Done!")


if __name__ == "__main__":
    main()
