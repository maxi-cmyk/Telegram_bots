import requests
import sys
import os

# Ensure we can import config
sys.path.append(os.getcwd())

try:
    from config import RSS_FEEDS
except ImportError:
    # If config imports fail due to missing env vars, verify checking manual list or handle error
    print("Could not import RSS_FEEDS from config. Ensure .env is set if config checks it.")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, application/atom+xml, text/xml, */*'
}

print(f"Checking {len(RSS_FEEDS)} feeds...")
print("-" * 60)
all_good = True

for url in RSS_FEEDS:
    try:
        response = requests.get(url, headers=headers, timeout=15)
        status = response.status_code
        if status == 200:
            print(f"[200] SUCCESS: {url}")
        else:
            print(f"[{status}] FAIL: {url}")
            all_good = False
    except Exception as e:
        print(f"[ERROR] {url}: {e}")
        all_good = False

print("-" * 60)
if all_good:
    print("All feeds verified successfully.")
else:
    print("Some feeds failed verification.")
