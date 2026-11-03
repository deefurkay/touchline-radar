#!/usr/bin/env python3
"""Collect candidate coaching-vacancy links from public Google News RSS results.
Every result is a discovery lead, not a verified vacancy.
"""
import json, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

QUERIES = [
 '"U20" football coach vacancy Glasgow OR Renfrewshire OR Paisley',
 '"U18" football coach wanted Glasgow OR Renfrewshire OR Paisley',
 '"U21" football manager OR coach vacancy Glasgow OR Renfrewshire OR Paisley',
 '"looking for a manager" football Glasgow OR Renfrewshire OR Paisley',
 '"looking for coaches" football club Glasgow OR Renfrewshire OR Paisley',
 '"assistant coach" football vacancy Glasgow OR Renfrewshire OR Paisley',
 '"head coach" football vacancy Glasgow OR Renfrewshire OR Paisley',
 'WOSFL "manager wanted" OR "looking for a manager" Scotland',
 'WOSFL "assistant manager" vacancy OR coach wanted',
 'site:facebook.com football "U20" coach Glasgow',
 'site:facebook.com football "manager wanted" Glasgow club',
 'site:x.com football "U20" coach Glasgow',
 'site:twitter.com football coach vacancy Glasgow club',
 'site:instagram.com football "coach wanted" Glasgow',
 'site:linkedin.com/jobs football coach Glasgow Scotland',
 '"Pollok FC" coach OR manager vacancy OR recruitment',
 '"St Anthonys" coach OR manager vacancy football',
 '"St Cadocs" coach OR manager vacancy football',
 '"Giffnock Soccer Centre" coach OR vacancy',
 '"Finnart FC" coach OR manager vacancy',
 '"Glasgow United FC" coach OR manager vacancy',
 '"Stamperland FC" coach OR vacancy',
 '"Pollok United" football coach vacancy',
 '"Queens Park" academy coach vacancy Glasgow',
 '"Partick Thistle" academy coach vacancy',
 '"Celtic" academy coach vacancy Glasgow',
 '"St Mirren" academy coach vacancy Paisley',
 '"Harmony Row" football coach vacancy Glasgow',
 '"Pro Football Academy" Glasgow South coach jobs',
 '"1st Touch Football" Glasgow coach vacancy',
 '"Pollok United" coach wanted Glasgow',
 '"Giffnock SC" coaching vacancy',
 '"Stamperland FC" coach required',
 '"The W Academy" Glasgow coach vacancy',
 '"Glasgow City Academy" coach vacancy',
 '"Harmony Row" football coach vacancy Glasgow',
 '"Castlemilk Community FC" coach vacancy',
 '"Park Villa Boys Club" coach vacancy Glasgow',
 '"Hillwood Boys Club" coach vacancy Glasgow',
 'site:gadyfl.com coaches required Glasgow',
]
def fetch(query):
 url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query,"hl":"en-GB","gl":"GB","ceid":"GB:en"})
 req=urllib.request.Request(url,headers={"User-Agent":"TouchlineRadar/0.1"})
 with urllib.request.urlopen(req,timeout=25) as response: root=ET.fromstring(response.read())
 found=[]
 for node in root.findall(".//item"):
  title=(node.findtext("title") or "").strip(); link=(node.findtext("link") or "").strip()
  if not title or not link: continue
  source_node=node.find("source")
  snippet=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",node.findtext("description") or "")).strip()
  found.append({"title":title,"url":link,"published":(node.findtext("pubDate") or "").strip(),"snippet":snippet[:500],"source":(source_node.text or "").strip() if source_node is not None else "","query":query})
 return found
unique={}; errors=[]
for query in QUERIES:
 try:
  for item in fetch(query): unique.setdefault(item["url"].split("&ved=")[0],item)
 except Exception as exc: errors.append({"query":query,"error":str(exc)[:250]})
# Keep likely recruitment posts and filter obvious non-football / non-vacancy noise.
intent=re.compile(r"\b(vacanc|recruit|recruiting|looking for|wanted|seeking|join (our|the)|coach(es)? required|manager required|assistant manager|head coach|coach wanted|manager wanted|applications? (are )?open|apply now|trial(s)? for)\b",re.I)
football=re.compile(r"\b(football|soccer|wosfl|west of scotland|academy|junior football|amateur football|youth football|u18|u19|u20|u21|reserves)\b",re.I)
noise=re.compile(r"\b(rugby|basketball|cricket|hockey|american football|nfl|gaelic|netball)\b",re.I)
local=re.compile(r"\b(glasgow|renfrewshire|paisley|johnstone|renfrew|barrhead|giffnock|shawlands|pollok|cathcart|gov(an)?|rutherglen|cambuslang|east kilbride|east renfrewshire|south lanarkshire|clydebank|pollok united|stamperland|st cadoc|saint anthony|st anthony|finnart|glasgow united|queen.?s park|partick thistle|celtic|st mirren|the w academy|harmony row|pro football academy|1st touch|bearsden|milngavie|scotland)\b",re.I)
filtered=[]
for item in unique.values():
 text=" ".join([item.get("title",""),item.get("snippet",""),item.get("source",""),item.get("query","")])
 if noise.search(item.get("title","")): continue
 if not intent.search(text) or not football.search(text): continue
 if not local.search(text): continue
 item["verification_status"]="Unverified lead — check original post, club and location"
 filtered.append(item)
items=sorted(filtered,key=lambda x:x.get("published",""),reverse=True)
payload={"generated_at":datetime.now(timezone.utc).isoformat(),"coverage_note":"Filtered candidate recruitment posts from public search-indexed results. Not exhaustive social-media access. Every lead remains unverified; confirm the original post, club, team level and base within 10 miles of Shawlands.","query_count":len(QUERIES),"raw_result_count":len(unique),"result_count":len(items),"errors":errors,"items":items[:150]}
Path("vacancies-feed.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Wrote {len(payload['items'])} candidate links; {len(errors)} query errors.")
