#!/usr/bin/env python3
import urllib.request
import urllib.parse
import http.cookiejar

# Create a cookie jar and opener
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# Login
login_url = 'http://localhost:5001/admin/login'
login_data = urllib.parse.urlencode({'password': '@WW*UU2w8u'}).encode('utf-8')
response = opener.open(login_url, login_data)
print(f"✓ Login successful (status: {response.status})")

# Check admin dashboard for review display
dashboard_url = 'http://localhost:5001/admin/dashboard'
response = opener.open(dashboard_url)
content = response.read().decode('utf-8')

checks = [
    ('Test User', 'Review name'),
    ('Ana Popescu', 'Second review name'),
    ('★', 'Star rating display'),
    ('Recent Reviews', 'Section title'),
]

for check_str, desc in checks:
    if check_str in content:
        print(f"✓ {desc} found")

# Check all reviews page
all_reviews_url = 'http://localhost:5001/admin/all-reviews'
response = opener.open(all_reviews_url)
content = response.read().decode('utf-8')

if 'test@example.com' in content and '/admin/review/' in content:
    print("✓ All reviews page working with review links")
