#!/usr/bin/env python3
"""Daily discovery of additional Glasgow grassroots club candidates.
Candidates are not promoted to the verified local directory until their men's/boys'
team venue is checked against the 10-mile Shawlands boundary.
"""
import json, re, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone

SOURCES = [
    "https://www.juniorgrassrootshub.com/clubs/in/glasgow-city",
]
EXCLUDE = re.compile(r"women|girls|female|ladies|wfc|women's", re.I)
LOCAL = re.compile(r"Glasgow City|Renfrewshire|East Renfrewshire", re.I)
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.items=[]; self.href=None; self.label=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a":
            self.href=dict(attrs).get("href"); self.label=[]
    def handle_data(self, data):
        if self.href: self.label.append(data.strip())
    def handle_endtag(self, tag):
        if tag=="a" and self.href:
            name=re.sub(r"\\s+"," "," ".join(x for x in self.label if x)).strip()
            if name: self.items.append((name,self.href))
            self.href=None; self.label=[]

found={}
for source in SOURCES:
    try:
        req=urllib.request.Request(source,headers={"User-Agent":"Mozilla/5.0 TouchlineRadar/1.0"})
        with urllib.request.urlopen(req,timeout=25) as response: html=response.read().decode("utf-8","ignore")
        parser=Links(); parser.feed(html)
        for name,href in parser.items:
            if not name or EXCLUDE.search(name): continue
            if not re.search(r"club|academy|football|fc|yc|boys",name,re.I): continue
            if name.lower() in {"view club","view all clubs","read more"}: continue
            url=href if href.startswith("http") else "https://www.juniorgrassrootshub.com"+href
            key=re.sub(r"[^a-z0-9]","",name.lower())
            if key: found.setdefault(key,{"name":name,"source_url":url,"discovered_from":source})
    except Exception as exc:
        print("Source error",source,str(exc)[:180])

try: existing=json.loads(Path("club-discovery-candidates.json").read_text(encoding="utf-8"))
except Exception: existing={"candidates":[]}
known={re.sub(r"[^a-z0-9]","",x.get("name","").lower()) for x in existing.get("candidates",[])}
try: directory=json.loads(Path("clubs.json").read_text(encoding="utf-8"))
except Exception: directory={"clubs":[]}
known.update(re.sub(r"[^a-z0-9]","",x.get("name","").lower()) for x in directory.get("clubs",[]))
new=[]
for key,item in found.items():
    if key in known: continue
    item["status"]="New candidate — verify men's/boys' team and actual home/training base within 10 miles of Shawlands"
    item["discovered_at"]=datetime.now(timezone.utc).isoformat()
    new.append(item)
all_items=existing.get("candidates",[])+new
# Keep one record per normalised name; retain the first discovery source.
dedup={}
for item in all_items:
    key=re.sub(r"[^a-z0-9]","",item.get("name","").lower())
    if key: dedup.setdefault(key,item)
payload={"checked_at":datetime.now(timezone.utc).isoformat(),"sources":SOURCES,"candidate_count":len(dedup),"new_candidates_this_run":len(new),"note":"These are screening leads, not confirmed in-radius organisations. Verify team gender/level and actual venue before promoting to clubs.json.","candidates":sorted(dedup.values(),key=lambda x:x["name"].casefold())}
Path("club-discovery-candidates.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print("New candidates:",len(new),"Total screening queue:",len(dedup))
