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
 '"Saint Anthony\'s FC" "first team manager"',
 '"Saint Anthonys FC" "manager wanted"',
 'site:theants.co.uk manager OR "part ways" OR departure',
 '"parts ways with" manager football club Scotland',
 '"manager leaves" football club Glasgow vacancy',
 '"manager departs" WOSFL club',
 '"The Ants" "first team manager" Glasgow',
 '"first team manager wanted" football Glasgow',
 '"first team manager vacancy" WOSFL Scotland',
 '"manager required" "West of Scotland" football',
 '"seeking a manager" WOSFL Glasgow',
 '"Harmony Row" football coach vacancy Glasgow',
 '"Castlemilk Community FC" coach vacancy',
 '"Park Villa Boys Club" coach vacancy Glasgow',
 '"Hillwood Boys Club" coach vacancy Glasgow',
 'site:gadyfl.com coaches required Glasgow',
]

# Build club-by-club public-index searches from the maintained local directory.
# Club names help match posts that omit a town or venue.
try:
 clubs_data=json.loads(Path("clubs.json").read_text(encoding="utf-8"))
 WATCH_CLUBS=[c for c in clubs_data.get("clubs",[]) if c.get("name")]
except Exception:
 WATCH_CLUBS=[]
for club in WATCH_CLUBS:
 name=club["name"]
 QUERIES.extend([
  f'"{name}" (coach OR manager OR "looking for" OR wanted OR vacancy OR recruitment)',
  f'site:facebook.com "{name}" (coach OR manager OR "looking for" OR wanted OR recruitment)',
  f'(site:instagram.com OR site:x.com OR site:twitter.com) "{name}" (coach OR manager OR vacancy OR wanted)',
 ])
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
intent=re.compile(r"\b(vacanc|recruit|recruiting|looking for|wanted|seeking|join (our|the)|coach(es)? required|manager required|manager wanted|manager vacancy|first team manager|parts ways with|part ways with|manager leaves|manager departs|manager resignation|manager steps down|assistant manager required|head coach required|coach wanted|applications? (are )?open|apply now|trial(s)? for)\b",re.I)
football=re.compile(r"\b(football|soccer|wosfl|west of scotland|academy|junior football|amateur football|youth football|u18|u19|u20|u21|reserves|coach|manager)\b",re.I)
club_names=[c.get("name","") for c in WATCH_CLUBS if c.get("name")]
club_pattern=re.compile("|".join(re.escape(n) for n in sorted(club_names,key=len,reverse=True)),re.I) if club_names else None
noise=re.compile(r"\b(rugby|basketball|cricket|hockey|american football|nfl|gaelic|netball)\b",re.I)
local=re.compile(r"\b(glasgow|renfrewshire|paisley|johnstone|renfrew|barrhead|giffnock|shawlands|pollok|cathcart|gov(an)?|rutherglen|cambuslang|east kilbride|east renfrewshire|south lanarkshire|clydebank|pollok united|stamperland|st cadoc|saint anthony|st anthony|finnart|glasgow united|queen.?s park|partick thistle|celtic|st mirren|the w academy|harmony row|pro football academy|1st touch|bearsden|milngavie|scotland)\b",re.I)
filtered=[]
for item in unique.values():
 text=" ".join([item.get("title",""),item.get("snippet",""),item.get("source","")])
 if noise.search(item.get("title","")): continue
 if not intent.search(text) or not football.search(text): continue
 matched=club_pattern.search(text) if club_pattern else None
 if not local.search(text) and not matched: continue
 item["club"]=matched.group(0) if matched else ""
 item["verification_status"]="Unverified lead — check original post, team level and actual base within 10 miles"
 item["discovery_method"]="Club watchlist" if matched else "Public indexed search"
 filtered.append(item)
# Discard stale indexed results and sort newest first.
from email.utils import parsedate_to_datetime
now=datetime.now(timezone.utc)
def recent(item):
 try:
  return (now-parsedate_to_datetime(item.get('published','')).astimezone(timezone.utc)).days <= 180
 except Exception:
  return False
filtered=[x for x in filtered if recent(x)]
items=sorted(filtered,key=lambda x:x.get('published',''),reverse=True)
# Preserve manually verified / user-reported leads across scheduled runs.
try:
 old=json.loads(Path('vacancies-feed.json').read_text(encoding='utf-8'))
 pinned=[x for x in old.get('items',[]) if x.get('lead_type') in ('user_reported','official_departure')]
except Exception:
 pinned=[]
items=pinned+[x for x in items if x.get('url') not in {p.get('url') for p in pinned}]
payload={"generated_at":datetime.now(timezone.utc).isoformat(),"coverage_note":"Recent candidate recruitment posts from public search-indexed results. Search query text is never used to classify a result. Results older than 180 days are excluded. Club-specific searches cover publicly indexed Facebook, Instagram and X posts where search engines expose them; this is not direct platform API access and cannot see every post. Every lead remains unverified; confirm the original post, club, team level and base within 10 miles of Shawlands.","query_count":len(QUERIES),"club_watchlist_count":len(WATCH_CLUBS),"discovery_sources":["public indexed Facebook posts","public indexed Instagram posts","public indexed X posts","club websites and news"],"raw_result_count":len(unique),"result_count":len(items),"errors":errors,"items":items[:150]}
Path("vacancies-feed.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Wrote {len(payload['items'])} candidate links; {len(errors)} query errors.")
