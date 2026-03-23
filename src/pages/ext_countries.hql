-- ============================================================================
-- STEP 1.3: EXTERNAL TABLE - countries
-- Run: hive -f 03_ext_countries.hql
-- ============================================================================

USE ticketmeta09;

DROP TABLE IF EXISTS ext_countries;

CREATE EXTERNAL TABLE ext_countries
(
    id              STRING,
    code            STRING,
    name            STRING,
    continent       STRING,
    wikipedia_link  STRING,
    keywords        STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\"",
    "escapeChar"    = "\\"
)
STORED AS TEXTFILE
LOCATION '/user/arafat/ticketmeta09/data/countries'
TBLPROPERTIES ("skip.header.line.count"="1");

-- Verify
SELECT COUNT(*) AS row_count FROM ext_countries;
SELECT * FROM ext_countries LIMIT 5;
