"""Pre-warm all analytics caches by hitting each endpoint once."""
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

endpoints = [
    "/api/analytics/overview",
    "/api/analytics/top-airlines",
    "/api/analytics/day-of-week",
    "/api/analytics/booking-window",
    "/api/analytics/weekend-midweek",
    "/api/analytics/economy-gap",
    "/api/analytics/nonstop-premium",
    "/api/analytics/network-overview",
    "/api/analytics/longest-flights",
    "/api/analytics/top-routes",
    "/api/analytics/top-municipalities",
    "/api/analytics/top-regions",
    "/api/analytics/expensive-destinations",
    "/api/analytics/nonstop-routes",
    "/api/analytics/hub-vs-regional",
    "/api/analytics/region-pricing",
    "/api/analytics/monopoly-routes",
    "/api/analytics/hub-carriers",
    "/api/analytics/aircraft-overview",
    "/api/analytics/seats-pricing",
    "/api/analytics/runway-pricing",
    "/api/analytics/aircraft-pricing",
    "/api/enrichment/weather?airport=ATL",
    "/api/enrichment/wealth",
    "/api/enrichment/brand",
    "/api/enrichment/rail",
    "/api/enrichment/ghost",
]

print(f"Pre-warming {len(endpoints)} endpoints...")
for i, ep in enumerate(endpoints):
    print(f"\n[{i+1}/{len(endpoints)}] {ep}")
    try:
        cmd = f'curl -s -o /dev/null -w "%{{http_code}} %{{time_total}}s" http://localhost:5000{ep}'
        _, o, e = c.exec_command(cmd, timeout=300)
        result = o.read().decode().strip()
        print(f"  -> {result}")
    except Exception as ex:
        print(f"  -> Error: {ex}")

print("\n🎉 All analytics endpoints pre-warmed!")
c.close()
