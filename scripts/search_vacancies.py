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

DIRECT_SOURCES = [
 ("sportscotland jobs","https://sportscotland.org.uk/jobs/"),
 ("Rossvale FC Academy work with us","https://rossvalefcacademy.co.uk/work-with-us/"),
]

# Add every club's own website to the daily direct-page watchlist.
for c in WATCH_CLUBS:
 site=c.get("website","")
 if site and site.startswith("https://"):
  DIRECT_SOURCES.append((c["name"]+" official website",site))

def fetch_direct_pages():
 from html.parser import HTMLParser
 class PageText(HTMLParser):
  def __init__(self): super().__init__(); self.parts=[]; self.links=[]; self.href=None; self.anchor=[]
  def handle_starttag(self,tag,attrs):
   attrs=dict(attrs)
   if tag=="a": self.href=attrs.get("href"); self.anchor=[]
  def handle_data(self,data):
   text=re.sub(r"\s+"," ",data).strip()
   if text:
    self.parts.append(text)
    if self.href:self.anchor.append(text)
  def handle_endtag(self,tag):
   if tag=="a" and self.href:
    self.links.append(( " ".join(self.anchor), self.href))
    self.href=None;self.anchor=[]
 direct=[]
 for source,url in DIRECT_SOURCES:
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 TouchlineRadar/1.0"})
   with urllib.request.urlopen(req,timeout=20) as response:
    page=response.read().decode("utf-8","ignore")
    final=response.geturl()
   parser=PageText();parser.feed(page)
   body=" ".join(parser.parts)
   # Keep only role-relevant pages; use the actual page URL unless a specific
   # advert link appears in the same page.
   if not re.search(r"(coach|manager|recruit|vacan|assistant coach|goalkeeping coach)",body,re.I):continue
   candidates=[(t,h) for t,h in parser.links if re.search(r"(coach|manager|recruit|vacan|apply|career|job)",t,re.I)]
   title=(candidates[0][0] if candidates else source)
   link=(urllib.parse.urljoin(final,candidates[0][1]) if candidates else final)
   direct.append({"title":title+" — "+source,"url":link,"published":datetime.now(timezone.utc).isoformat(),"snippet":body[:900],"source":source,"query":"Direct official noticeboard check","club":"","verification_status":"Official noticeboard page; individual role and local team base require confirmation","discovery_method":"Direct source"})
  except Exception as exc:
   errors.append({"source":source,"error":str(exc)[:200]})
 return direct

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
# Add direct official and specialist noticeboard pages to indexed search results.
for direct_item in fetch_direct_pages(): unique.setdefault(direct_item['url'],direct_item)

# Keep only explicit coaching and management recruitment, not general club posts.
# Require an explicit coaching/management role AND explicit recruitment language.
# Generic club updates, player recruitment, camps and off-pitch volunteering are not vacancies.
ROLE_RECRUITMENT = re.compile(
 r"(?:"
 r"\b(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)?\s*(?:football\s+)?coach(?:es)?\s+(?:wanted|required|needed|sought|vacanc(?:y|ies))\b"
 r"|\b(?:first[ -]?team\s+)?manager\s+(?:wanted|required|needed|sought|vacanc(?:y|ies))\b"
 r"|\b(?:vacanc(?:y|ies)|recruit(?:ing|ment)?|paid position|applications? (?:are )?open)\b.{0,120}\b(?:coach|manager|coaching staff)\b"
 r"|\b(?:coach|manager|coaching staff)\b.{0,120}\b(?:vacanc(?:y|ies)|recruit(?:ing|ment)?|wanted|required|needed|apply|applications? open|paid position)\b"
 r"|\blooking for (?:an? )?(?:(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)\s+)?(?:football\s+)?(?:coach|manager)\b"
 r"|\bseeking (?:an? )?(?:(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)\s+)?(?:football\s+)?(?:coach|manager)\b"
 r"|\b(?:join|joining) (?:our|the) coaching (?:team|staff)\b"
 r"|\b(?:appoint|appointing|appointment of)\b.{0,100}\b(?:coach|manager)\b"
 r"|\b(?:coach|manager)\b.{0,100}\b(?:steps down|resigns?|departs?|leaves|parts ways)\b"
 r")", re.I)
NON_JOB_CONTEXT = re.compile(
 r"\b(?:looking for players|recruiting players|players wanted|player recruitment|open for bookings|book now|football camp|holiday camp|tots classes|sessions? for children|social media volunteers?|fundraising|sponsors? wanted|team behind the team|help behind the scenes)\b",
 re.I)
def is_coaching_vacancy(text):
 return bool(ROLE_RECRUITMENT.search(text)) and not bool(NON_JOB_CONTEXT.search(text))

football=re.compile(r"\b(football|soccer|wosfl|west of scotland|academy|junior football|amateur football|youth football|u18|u19|u20|u21|reserves|coach|manager)\b",re.I)
club_names=[c.get("name","") for c in WATCH_CLUBS if c.get("name")]
club_pattern=re.compile("|".join(re.escape(n) for n in sorted(club_names,key=len,reverse=True)),re.I) if club_names else None
noise=re.compile(r"\b(rugby|basketball|cricket|hockey|american football|nfl|gaelic|netball|women.?s football|girls.? football|female football|women.?s team|girls.? team|bsc glasgow women|glasgow city fc)\b",re.I)
local=re.compile(r"\b(glasgow|renfrewshire|paisley|johnstone|renfrew|barrhead|giffnock|shawlands|pollok|cathcart|gov(an)?|rutherglen|cambuslang|east kilbride|east renfrewshire|south lanarkshire|clydebank|pollok united|stamperland|st cadoc|saint anthony|st anthony|finnart|glasgow united|queen.?s park|partick thistle|celtic|st mirren|the w academy|harmony row|pro football academy|1st touch|bearsden|milngavie|scotland)\b",re.I)
filtered=[]
for item in unique.values():
 text=" ".join([item.get("title",""),item.get("snippet",""),item.get("source","")])
 if noise.search(text) or not football.search(text) or not is_coaching_vacancy(text): continue
 matched=club_pattern.search(text) if club_pattern else None
 if not local.search(text) and not matched: continue
 item["club"]=matched.group(0) if matched else ""
 item["verification_status"]="Coaching/management recruitment signal found — verify original advert, team level and base"
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
