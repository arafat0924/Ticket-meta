"""
Setup Amtrak Rail Routes in HDFS + Hive (for Rail Price Ceiling analysis)
Run on VM: python3 setup_rail_hive.py
"""
import subprocess, os, sys

CSV_LOCAL = os.path.join(os.path.dirname(__file__), "external_data", "amtrak_ne_corridor_routes.csv")
HDFS_DIR = "/user/hive/warehouse/amtrak_rail_routes_staging"
HQL_FILE = os.path.join(os.path.dirname(__file__), "hql_code", "amtrak_rail_routes.hql")

def run(cmd, desc):
    print(f"\n{'='*60}\n{desc}\n{'='*60}")
    print(f"  CMD: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  STDERR: {r.stderr.strip()}")
    else:
        print(f"  OK: {r.stdout.strip()[:200]}")
    return r.returncode == 0

def main():
    if not os.path.exists(CSV_LOCAL):
        print(f"ERROR: CSV not found: {CSV_LOCAL}")
        sys.exit(1)

    # Step 1: Create HDFS directory
    run(f"hdfs dfs -mkdir -p {HDFS_DIR}", "Creating HDFS directory for Amtrak rail routes")

    # Step 2: Remove old data
    run(f"hdfs dfs -rm -f {HDFS_DIR}/*", "Removing old data from HDFS")

    # Step 3: Upload CSV to HDFS
    ok = run(f"hdfs dfs -put {CSV_LOCAL} {HDFS_DIR}/", "Uploading amtrak_ne_corridor_routes.csv to HDFS")
    if not ok:
        print("FAILED to upload CSV to HDFS!")
        sys.exit(1)

    # Step 4: Verify upload
    run(f"hdfs dfs -ls {HDFS_DIR}/", "Verifying HDFS upload")

    # Step 5: Run HQL to create Hive tables
    if os.path.exists(HQL_FILE):
        ok = run(f"beeline -u 'jdbc:hive2://localhost:10000/ticketmeta09' -f {HQL_FILE}", 
                 "Creating Hive tables (staging + ORC)")
        if not ok:
            print("WARNING: beeline failed. Trying hive CLI...")
            run(f"hive -f {HQL_FILE}", "Retrying with hive CLI")
    else:
        print(f"WARNING: HQL file not found: {HQL_FILE}")

    # Step 6: Verify table
    run("beeline -u 'jdbc:hive2://localhost:10000/ticketmeta09' -e \"SELECT rail_available, COUNT(*) FROM amtrak_rail_routes_orc GROUP BY rail_available\"",
        "Verifying amtrak_rail_routes_orc table")

    print("\n✅ Amtrak Rail Routes setup complete!")
    print("   Table: amtrak_rail_routes_orc")
    print("   Columns: origin_airport, destination_airport, rail_available, rail_service, avg_rail_duration_hrs, avg_rail_fare_usd, rail_corridor")

if __name__ == "__main__":
    main()
