#!/usr/bin/env python3
import datetime as dt
import json
import os
import urllib.request
from collections import Counter

LOGIN = os.environ.get("GH_LOGIN", "mhdsahil1")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


now = dt.datetime.now(dt.timezone.utc)
today = now.date()
start = dt.datetime.combine(today - dt.timedelta(days=364), dt.time(), tzinfo=dt.timezone.utc)
end = dt.datetime.combine(today, dt.time().replace(hour=23, minute=59, second=59), tzinfo=dt.timezone.utc)

query = """query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
    repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){
      nodes{
        name
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){
          edges{size node{name}}
        }
      }
    }
  }
}"""

data = gql(query, {"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()})["user"]
calendar = data["contributionsCollection"]["contributionCalendar"]
days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
counts = [day["contributionCount"] for day in days]


def streak(values):
    best = current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0

    trailing = 0
    for value in reversed(values):
        if value:
            trailing += 1
        else:
            break
    return trailing, best


current_streak, longest_streak = streak(counts)

langs = Counter()
for repo in data["repositories"]["nodes"]:
    for edge in repo["languages"]["edges"]:
        langs[edge["node"]["name"]] += edge["size"]
lang_total = sum(langs.values()) or 1
langs = langs.most_common(5)


def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(name, body, width=900, height=220):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="10" fill="#0d1117"/>
<g font-family="monospace" fill="#f0f6fc">{body}</g>
</svg>'''
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as file:
        file.write(svg)


# ---------- stats.svg ----------
width = 900
spark = counts[-56:]
max_value = max(spark) if spark else 1
bar_width = 10
bar_gap = 4
spark_x = 32
spark_base = 194
spark_height = 48
bars = []
for i, value in enumerate(spark):
    height = max(2, (value / max_value) * spark_height)
    x = spark_x + i * (bar_width + bar_gap)
    y = spark_base - height
    bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{height:.1f}" rx="2" fill="#58a6ff"/>')

lang_lines = []
for i, (name, size) in enumerate(langs):
    pct = size / lang_total * 100
    lang_lines.append(
        f'<text x="690" y="{105 + i * 17}" font-size="12">{esc(name)} {pct:4.1f}%</text>'
    )

body = f'''
<text x="32" y="31" font-size="14" fill="#8b949e">GITHUB ACTIVITY / LAST 365 DAYS</text>
<text x="32" y="70" font-size="34" font-weight="700">{calendar["totalContributions"]:,}</text>
<text x="32" y="88" font-size="11" fill="#8b949e">contributions</text>

<line x1="220" y1="42" x2="220" y2="92" stroke="#30363d"/>
<text x="250" y="58" font-size="12" fill="#8b949e">CURRENT STREAK</text>
<text x="250" y="86" font-size="24" font-weight="700">{current_streak} days</text>

<line x1="430" y1="42" x2="430" y2="92" stroke="#30363d"/>
<text x="460" y="58" font-size="12" fill="#8b949e">LONGEST STREAK</text>
<text x="460" y="86" font-size="24" font-weight="700">{longest_streak} days</text>

<line x1="650" y1="42" x2="650" y2="92" stroke="#30363d"/>
<text x="680" y="58" font-size="12" fill="#8b949e">PUBLIC REPOS</text>
<text x="680" y="86" font-size="24" font-weight="700">{len(data["repositories"]["nodes"])}</text>

<text x="32" y="122" font-size="11" fill="#8b949e">RECENT CONTRIBUTION DENSITY</text>
<line x1="32" y1="194" x2="655" y2="194" stroke="#30363d"/>
<g>{''.join(bars)}</g>
<text x="690" y="92" font-size="11" fill="#8b949e">TOP LANGUAGES</text>
{''.join(lang_lines)}
'''
write_svg("stats.svg", body, width=width, height=220)


# ---------- year.svg ----------
ramp = " .:-=+*#%@"
max_count = max(counts) if counts else 1
rows = []
for i in range(0, len(counts), 52):
    row = counts[i:i + 52]
    rows.append("".join(ramp[min(len(ramp) - 1, int((value / max_count) * (len(ramp) - 1)))] for value in row))

activity = []
for i, row in enumerate(rows):
    activity.append(f'<text x="32" y="{48 + i * 16}" font-size="12" fill="#8b949e">{esc(row)}</text>')

body = f'''
<text x="32" y="26" font-size="14" fill="#f0f6fc">365-DAY CONTRIBUTION MAP</text>
<text x="32" y="42" font-size="10" fill="#8b949e">each character represents one day · darker characters mean more activity</text>
{''.join(activity)}
'''
write_svg("year.svg", body, width=900, height=max(100, 55 + len(rows) * 16))

print(
    f'generated stats.svg ({calendar["totalContributions"]} contributions), '
    f'year.svg, current={current_streak}, longest={longest_streak}'
)
