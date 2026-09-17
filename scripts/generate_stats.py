#!/usr/bin/env python3
import datetime as dt, json, os, urllib.request
from collections import Counter

LOGIN = os.environ.get('GH_LOGIN', 'mhdsahil1')
TOKEN = os.environ.get('GITHUB_TOKEN')
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gql(query, variables=None):
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': query, 'variables': variables or {}}).encode(), headers={'Authorization': f'bearer {TOKEN}', 'Content-Type': 'application/json', 'User-Agent': 'profile-generator'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get('errors'):
        raise RuntimeError(data['errors'])
    return data['data']

now = dt.datetime.now(dt.timezone.utc)
today = now.date()
start = dt.datetime.combine(today - dt.timedelta(days=364), dt.time(), tzinfo=dt.timezone.utc)
end = dt.datetime.combine(today, dt.time().replace(hour=23, minute=59, second=59), tzinfo=dt.timezone.utc)

q = '''query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}
      commitContributionsByRepository(maxRepositories:100){contributions(first:100){totalCount} repository{name}}
    }
    repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){nodes{name languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
  }
}'''
data = gql(q, {'login': LOGIN, 'from': start.isoformat(), 'to': end.isoformat()})['user']
cal = data['contributionsCollection']['contributionCalendar']
days = [d for w in cal['weeks'] for d in w['contributionDays']]
counts = [d['contributionCount'] for d in days]

def streak(values):
    best = cur = 0
    for n in values:
        if n:
            cur += 1; best = max(best, cur)
        else: cur = 0
    cur2 = 0
    for n in reversed(values):
        if n: cur2 += 1
        else: break
    return cur2, best
current, longest = streak(counts)

langs = Counter()
for repo in data['repositories']['nodes']:
    for e in repo['languages']['edges']:
        langs[e['node']['name']] += e['size']
lang_total = sum(langs.values()) or 1
langs = langs.most_common(6)

def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def write(name, body, w=900, h=220):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/><g fill="#111" font-family="monospace">{body}</g></svg>'''
    open(os.path.join(OUT,name),'w',encoding='utf-8').write(svg)

spark = counts[-56:]
maxv = max(spark) if spark else 1
bars = ''.join(f'<rect x="{18+i*14}" y="{115-(v/maxv)*72:.1f}" width="8" height="{max(2,(v/maxv)*72):.1f}" rx="1"/>' for i,v in enumerate(spark))
lang_lines = ''.join(f'<text x="30" y="{70+i*24}" font-size="15">{esc(n):&lt;16} {size/lang_total*100:5.1f}%</text>' for i,(n,size) in enumerate(langs))
write('stats.svg', f'''<text x="30" y="38" font-size="18">contributions / last 365 days</text><text x="30" y="82" font-size="38">{cal['totalContributions']:,}</text><text x="250" y="82" font-size="16">current streak</text><text x="250" y="111" font-size="28">{current} days</text><text x="430" y="82" font-size="16">longest streak</text><text x="430" y="111" font-size="28">{longest} days</text><g>{bars}</g><text x="820" y="82" font-size="14">public repos</text><text x="820" y="110" font-size="25">{len(data['repositories']['nodes'])}</text>''', h=145)

# One character per day, using the portrait ramp. Keep it compact enough for a profile README.
ramp = ' .`:-=+*cs#%@'
chars = ''.join(ramp[min(len(ramp)-1, int((v / max(1,max(counts))) * (len(ramp)-1)))] for v in counts)
rows = [chars[i:i+52] for i in range(0,len(chars),52)]
activity = ''.join(f'<text x="28" y="{30+i*17}" font-size="13">{esc(r)}</text>' for i,r in enumerate(rows))
write('year.svg', f'<text x="28" y="18" font-size="12">365-day contribution density</text>{activity}', h=30+len(rows)*17)
print(f'generated stats.svg ({cal["totalContributions"]} contributions), year.svg, current={current}, longest={longest}')
