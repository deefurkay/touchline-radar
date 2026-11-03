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
items=sorted(unique.values(),key=lambda x:x.get("published",""),reverse=True)
payload={"generated_at":datetime.now(timezone.utc).isoformat(),"coverage_note":"Candidate links from public search-indexed results. Not exhaustive social-media access. Each lead is unverified.","query_count":len(QUERIES),"result_count":len(items),"errors":errors,"items":items[:250]}
Path("vacancies-feed.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
print(f"Wrote {len(payload['items'])} candidate links; {len(errors)} query errors.")
