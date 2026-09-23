#!/usr/bin/env python3
import datetime as dt, html, json, os, urllib.request
from collections import Counter

LOGIN=os.environ.get("GH_LOGIN","mhdsahil1")
TOKEN=os.environ.get("GITHUB_TOKEN")
OUT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W=620
LIGHT="#66B78B"; DARK="#66B78B"
Q='''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}} repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){nodes{name languages(first:12,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}'''

def gql(v):
    r=urllib.request.Request("https://api.github.com/graphql",data=json.dumps({"query":Q,"variables":v}).encode(),headers={"Authorization":f"bearer {TOKEN}","Content-Type":"application/json","User-Agent":"mhdsahil1-profile"})
    with urllib.request.urlopen(r,timeout=30) as x:d=json.load(x)
    if d.get("errors"): raise RuntimeError(d["errors"])
    return d["data"]["user"]

def load():
    today=dt.datetime.now(dt.timezone.utc).date(); start=today-dt.timedelta(days=364)
    u=gql({"login":LOGIN,"from":f"{start}T00:00:00Z","to":f"{today}T23:59:59Z"})
    cal=u["contributionsCollection"]["contributionCalendar"]; days=[d for w in cal["weeks"] for d in w["contributionDays"]]; nums=[d["contributionCount"] for d in days]
    best=cur=0
    for n in nums:
        if n:cur+=1;best=max(best,cur)
        else:cur=0
    cur=0
    for n in reversed(nums):
        if n:cur+=1
        else:break
    sizes=Counter(); repos=Counter()
    for repo in u["repositories"]["nodes"]:
        e=repo.get("languages",{}).get("edges",[])
        for z in e:sizes[z["node"]["name"]]+=z["size"]
        if e:repos[e[0]["node"]["name"]]+=1
    return cal,days,cur,best,sizes.most_common(5),repos.most_common(5),len(u["repositories"]["nodes"])

def esc(x):return html.escape(str(x))
def wrap(body,h):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}"><style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}.d{{fill:{LIGHT}}}.e{{fill:#424a53}}.m{{fill:#8c959f}}.r{{stroke:#d8dee4}}@media(prefers-color-scheme:dark){{.d{{fill:{DARK}}}.e{{fill:#f0f6fc}}.m{{fill:#8b949e}}.r{{stroke:#30363d}}}}</style>{body}</svg>'''
def text(x,y,s,size=12,c="d",anchor="start",weight="400"):
    a=f' text-anchor="{anchor}"' if anchor!="start" else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" class="{c}"{a}>{esc(s)}</text>'
def write(name,body,h):
    with open(os.path.join(OUT,name),"w",encoding="utf-8") as f:f.write(wrap(body,h))

def make_portrait():
    # portrait-dark.svg is a hand-tuned ASCII rendering of the profile photo.
    # Keep it stable across scheduled stat refreshes.
    return

def headings():
    for word in ["about","stack","projects","stats","about this page"]:
        x=18+len(word)*9.6; write("hd-"+word.replace(" ","-")+".svg",text(0,18,word,16,"e",weight="600")+f'<line x1="{x:.0f}" y1="12" x2="{W}" y2="12" class="r"/>',26)

def main():
    cal,days,current,longest,by_size,by_repo,public=load(); weeks=cal["weeks"]; weekly=[sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]; peak=max(weekly or [1])
    bars=[]
    for i,v in enumerate(weekly):
        x=8+i*(W-16)/max(1,len(weekly)-1); h=(v/peak)*62
        bars.append(f'<rect x="{x-2:.1f}" y="{115-h:.1f}" width="4" height="{max(1,h):.1f}" rx="1" class="d"/>')
    body=text(0,26,"GITHUB ACTIVITY / LAST 365 DAYS",11,"m")+text(0,65,cal["totalContributions"],46,"e",weight="600")+text(0,84,"contributions",10,"m")
    for x,v,l in [(300,current,"current streak"),(450,longest,"longest streak"),(610,public,"public repos")]:body+=text(x,56,v,21,"e","end","600")+text(x,73,l,9,"m","end")
    body+=text(0,102,"RECENT ACTIVITY",9,"m")+''.join(bars)
    write("stats.svg",body,130)
    write("streak.svg",text(0,36,current,34,"e",weight="600")+text(0,55,"current streak",10,"m")+text(310,36,longest,34,"e",weight="600")+text(310,55,"longest streak",10,"m"),72)
    total=sum(v for _,v in by_size) or 1; body=text(0,16,"BY BYTES",9,"m")+text(320,16,"BY REPOSITORIES",9,"m")
    for i,(n,v) in enumerate(by_size):
        y=37+i*21;p=v/total*100;body+=text(0,y,n.lower()[:12],10,"e")+text(145,y,f"{p:.0f}%",9,"m","end")+f'<rect x="160" y="{y-8}" width="{min(135,p*1.35):.1f}" height="6" rx="2" class="d"/>'
    for i,(n,v) in enumerate(by_repo):
        y=37+i*21;body+=text(320,y,n.lower()[:12],10,"e")+text(610,y,v,9,"m","end")
    write("langs.svg",body,130)
    ramp=" .:-=+*#%@"; mx=max([d["contributionCount"] for d in days] or [1]); chars=[ramp[min(len(ramp)-1,int((d["contributionCount"]/mx)*(len(ramp)-1)))] for d in days]; rows=["".join(chars[i:i+73]) for i in range(0,len(chars),73)]
    body=text(0,18,"THE YEAR",9,"m")+text(0,33,"one character per day · quiet to loud",10,"m")+''.join(f'<text x="0" y="{51+i*12}" font-size="9" class="d" xml:space="preserve">{esc(r)}</text>' for i,r in enumerate(rows)); write("year.svg",body,60+len(rows)*12)
    headings()
    make_portrait()
    print(f"{cal['totalContributions']} contributions · current {current} · longest {longest}")
if __name__=="__main__":main()
