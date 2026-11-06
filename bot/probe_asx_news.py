"""Probe which ASX announcement endpoints respond from GitHub Actions (prints status + a sample)."""
import requests

H = {"User-Agent": "Mozilla/5.0 (asx-paper-trader)", "Accept": "application/json, text/html"}
TOK = "access_token=83ff96335c2d45a094df02a206a39ff4"
URLS = [
    "https://asx.api.markitdigital.com/asx-research/1.0/companies/BHP/announcements?count=20&market_sensitive=false",
    f"https://asx.api.markitdigital.com/asx-research/1.0/companies/BHP/announcements?count=20&market_sensitive=false&{TOK}",
    f"https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements?page=0&itemsPerPage=50&{TOK}",
    f"https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements?page=0&itemsPerPage=50&priceSensitiveOnly=true&{TOK}",
    "https://www.asx.com.au/asx/1/company/BHP/announcements?count=20&market_sensitive=false",
    "https://www.asx.com.au/asx/v2/statistics/todayAnns.do",
    "https://www.asx.com.au/asx/v2/statistics/prevBusDayAnns.do",
    "https://www.asx.com.au/asx/v2/statistics/announcements.do?by=asxCode&asxCode=BHP&timeframe=D&period=M6",
]
for u in URLS:
    try:
        r = requests.get(u, headers=H, timeout=20)
        body = r.text
        print("=" * 100)
        print(r.status_code, len(body), u)
        print(body[:1500].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        print("ERR", u, e)
