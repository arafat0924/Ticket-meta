"""
Optimization Script: Convert ext_itineraries (CSV) → itineraries_orc (ORC + Partitioned)
Run this ONCE on the VM to create the optimized table.

This will reduce query times from 2-8 minutes → 5-30 seconds by:
1. Converting from CSV → ORC (columnar format, ~5x compression)
2. Partitioning by startingAirport (skips irrelevant data)
3. Pre-casting numeric columns (avoids runtime CAST)

Usage:  
  export SPARK_HOME=/opt/spark-3.5.3
  export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
  python3 optimize_table.py

This may take 30-60 minutes for 80M rows but only needs to run ONCE.
"""
from pyspark.sql import SparkSession

print("=" * 60)
print("  Flight Data Optimization: CSV → ORC (Partitioned)")
print("=" * 60)

spark = (
    SparkSession.builder
    .appName("SkyQuery-Optimize")
    .config("spark.sql.shuffle.partitions", "16")
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sql("USE ticketmeta09")

print("\n[1/4] Reading ext_itineraries schema...")
spark.sql("DESCRIBE ext_itineraries").show(50, truncate=False)

print("\n[2/4] Creating optimized ORC table with proper types...")
spark.sql("""
    DROP TABLE IF EXISTS itineraries_orc
""")

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

print("\n[3/4] Inserting data from CSV to ORC (this takes 30-60 min)...")
print("       Progress can be monitored at http://node-master:4040\n")

spark.sql("""
    INSERT OVERWRITE TABLE itineraries_orc PARTITION (startingAirport)
    SELECT
        legId,
        searchDate,
        flightDate,
        destinationAirport,
        fareBasisCode,
        travelDuration,
        elapsedDays,
        isBasicEconomy,
        isRefundable,
        isNonStop,
        CAST(baseFare AS DOUBLE) AS baseFare,
        CAST(totalFare AS DOUBLE) AS totalFare,
        CAST(seatsRemaining AS INT) AS seatsRemaining,
        CAST(totalTravelDistance AS DOUBLE) AS totalTravelDistance,
        segmentsDepartureTimeEpochSeconds,
        segmentsDepartureTimeRaw,
        segmentsArrivalTimeEpochSeconds,
        segmentsArrivalTimeRaw,
        segmentsArrivalAirportCode,
        segmentsDepartureAirportCode,
        segmentsAirlineName,
        segmentsAirlineCode,
        segmentsEquipmentDescription,
        CAST(segmentsDurationInSeconds AS DOUBLE) AS segmentsDurationInSeconds,
        segmentsDistance,
        segmentsCabinCode,
        startingAirport
    FROM ext_itineraries
""")

print("\n[4/4] Verifying optimized table...")
count_result = spark.sql("SELECT COUNT(*) AS cnt FROM itineraries_orc").collect()
print(f"Total rows in itineraries_orc: {count_result[0]['cnt']:,}")

partitions = spark.sql("SHOW PARTITIONS itineraries_orc").collect()
print(f"Number of partitions (airports): {len(partitions)}")

print("\nSample query test (should be fast now):")
spark.sql("""
    SELECT startingAirport, destinationAirport, 
           MIN(totalFare) AS cheapest,
           COUNT(*) AS cnt
    FROM itineraries_orc
    WHERE startingAirport = 'ATL' AND destinationAirport = 'LAX'
    GROUP BY startingAirport, destinationAirport
""").show()

print("\n" + "=" * 60)
print("  DONE! Restart flask_api.py to auto-detect itineraries_orc")
print("  Queries should now be 10-50x faster!")
print("=" * 60)

spark.stop()
