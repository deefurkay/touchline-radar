#!/usr/bin/env python3
"""Optional first-party social API ingestion for Touchline Radar.

Credentials are read only from GitHub Actions secrets. No scraping or login automation.
X: recent search (last 7 days) using X_API_BEARER_TOKEN.
Facebook: public Page feed requires Meta app approval / Page Public Content Access.
Instagram: hashtag recent_media requires an eligible professional account and Meta approval.
"""
import json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEED=Path("vacancies-feed.json")
NOW=datetime.now(timezone.utc)
FOOTBALL=re.compile(r"\b(football|soccer|wosfl|academy|youth|u18|u19|u20|u21|reserve|development|first team|senior team|coach|manager)\b",re.I)
EXCLUDED=re.compile(r"\b(women.?s football|girls.? football|female football|women.?s team|girls.? team|bsc glasgow women|glasgow city fc)\b",re.I)
ROLE_RECRUITMENT=re.compile(r"(?:\b(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)?\s*(?:football\s+)?coach(?:es)?\s+(?:wanted|required|needed|sought|vacanc(?:y|ies))\b|\b(?:first[ -]?team\s+)?manager\s+(?:wanted|required|needed|sought|vacanc(?:y|ies))\b|\b(?:vacanc(?:y|ies)|recruit(?:ing|ment)?|paid position|applications? (?:are )?open)\b.{0,120}\b(?:coach|manager|coaching staff)\b|\b(?:coach|manager|coaching staff)\b.{0,120}\b(?:vacanc(?:y|ies)|recruit(?:ing|ment)?|wanted|required|needed|apply|applications? open|paid position)\b|\blooking for (?:an? )?(?:(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)\s+)?(?:football\s+)?(?:coach|manager)\b|\bseeking (?:an? )?(?:(?:head|assistant|goalkeeping|academy|youth|first[ -]?team|development)\s+)?(?:football\s+)?(?:coach|manager)\b|\b(?:join|joining) (?:our|the) coaching (?:team|staff)\b|\b(?:appoint|appointing|appointment of)\b.{0,100}\b(?:coach|manager)\b|\b(?:coach|manager)\b.{0,100}\b(?:steps down|resigns?|departs?|leaves|parts ways)\b)",re.I)
NON_JOB_CONTEXT=re.compile(r"\b(?:looking for players|recruiting players|players wanted|player recruitment|open for bookings|book now|football camp|holiday camp|tots classes|sessions? for children|social media volunteers?|fundraising|sponsors? wanted|team behind the team|help behind the scenes)\b",re.I)
def is_coaching_vacancy(text):
 return bool(ROLE_RECRUITMENT.search(text)) and not bool(NON_JOB_CONTEXT.search(text))
def get(url, token):
 req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"User-Agent":"TouchlineRadar/1.0"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read())
def make_item(title,url,created,text,source,club=""):
 body=(title+" "+text).strip()
 if EXCLUDED.search(body):return None
 if not is_coaching_vacancy(body) or not FOOTBALL.search(body):return None
 return {"id":"social-"+str(abs(hash(url))),"title":title or "Football coaching recruitment post","url":url,"published":created or NOW.isoformat(),"snippet":text[:700],"source":source,"verification_status":"Social post lead — verify original advert and role","lead_type":"social_api","club":club or "Unmatched club","query":"Direct social API"}
items=[];status={}
# X recent search
xt=os.getenv("X_API_BEARER_TOKEN","").strip()
if xt:
 queries=[
  '"coach wanted" football Scotland','"manager wanted" football Scotland',
  '"first team manager" Scotland football','"assistant manager" football vacancy Scotland',
  '"U20" coach OR manager Scotland football','"U18" coach OR manager Scotland football',
  '"looking for a manager" football Scotland','"coach required" football Glasgow',
  '"parts ways" manager football Scotland','"steps down" manager football Scotland'
 ]
 try:
  for q in queries:
   url="https://api.x.com/2/tweets/search/recent?"+urllib.parse.urlencode({"query":q+" lang:en -is:retweet","max_results":50,"tweet.fields":"created_at,author_id,entities"})
   data=get(url,xt)
   users={u["id"]:u.get("username","") for u in data.get("includes",{}).get("users",[])}
   for post in data.get("data",[]):
    username=users.get(post.get("author_id"),"")
    link="https://x.com/"+username+"/status/"+post["id"] if username else "https://x.com/search?q="+urllib.parse.quote(post["text"][:100])
    item=make_item(post["text"][:160],link,post.get("created_at"),post["text"],"X API")
    if item:items.append(item)
  status["x"]="connected"
 except Exception as e:status["x"]="error: "+str(e)[:180]
else:status["x"]="not configured (add X_API_BEARER_TOKEN GitHub secret)"
# Facebook public Page feeds. META_PAGE_IDS format: page_id_1,page_id_2
mt=os.getenv("META_ACCESS_TOKEN","").strip()
page_ids=[x.strip() for x in os.getenv("META_PAGE_IDS","").split(",") if x.strip()]
if mt and page_ids:
 try:
  for pid in page_ids:
   data=get("https://graph.facebook.com/v26.0/"+urllib.parse.quote(pid)+"/posts?"+urllib.parse.urlencode({"fields":"id,message,created_time,permalink_url","limit":100,"access_token":mt}),mt)
   for post in data.get("data",[]):
    item=make_item(post.get("message","")[:160],post.get("permalink_url",""),post.get("created_time"),post.get("message",""),"Facebook Graph API",pid)
    if item:items.append(item)
  status["facebook"]="connected"
 except Exception as e:status["facebook"]="error: "+str(e)[:180]
else:status["facebook"]="not configured (requires approved Meta access, META_ACCESS_TOKEN and META_PAGE_IDS)"
# Instagram hashtag discovery. Public hashtag media is limited and needs an eligible IG professional account.
ig_token=os.getenv("META_ACCESS_TOKEN","").strip()
ig_user=os.getenv("INSTAGRAM_USER_ID","").strip()
hashtags=[x.strip().lstrip("#") for x in os.getenv("INSTAGRAM_HASHTAGS","footballcoach,footballjobs,wosfl,glasgowfootball,scottishfootball,footballacademy").split(",") if x.strip()]
if ig_token and ig_user:
 try:
  for tag in hashtags[:30]:
   q="https://graph.facebook.com/v26.0/ig_hashtag_search?"+urllib.parse.urlencode({"user_id":ig_user,"q":tag,"access_token":ig_token})
   found=get(q,ig_token).get("data",[])
   if not found:continue
   hid=found[0]["id"]
   media=get("https://graph.facebook.com/v26.0/"+hid+"/recent_media?"+urllib.parse.urlencode({"user_id":ig_user,"fields":"id,caption,media_url,permalink,timestamp","limit":50,"access_token":ig_token}),ig_token)
   for post in media.get("data",[]):
    item=make_item((post.get("caption") or "")[:160],post.get("permalink",""),post.get("timestamp"),post.get("caption",""),"Instagram Graph API","#"+tag)
    if item:items.append(item)
  status["instagram"]="connected"
 except Exception as e:status["instagram"]="error: "+str(e)[:180]
else:status["instagram"]="not configured (requires Meta approval, INSTAGRAM_USER_ID and META_ACCESS_TOKEN)"
# Merge API leads into existing feed, preserving pinned/user-sourced leads.
try:feed=json.loads(FEED.read_text(encoding="utf-8"))
except Exception:feed={"items":[],"errors":[]}
existing=feed.get("items",[])
# Purge legacy false positives on every run; retain only manually pinned leads or
# items that independently pass the strict coaching-role test.
existing=[x for x in existing if x.get("lead_type") in ("user_reported","official_departure") or
          (is_coaching_vacancy(" ".join([x.get("title",""),x.get("snippet",""),x.get("role","")])) and
           not EXCLUDED.search(" ".join([x.get("title",""),x.get("snippet",""),x.get("role","")])))]
seen={x.get("url") for x in existing}
for x in items:
 if x and x.get("url") and x["url"] not in seen:
  existing.append(x);seen.add(x["url"])
feed["items"]=sorted(existing,key=lambda x:x.get("published",""),reverse=True)[:300]
feed["result_count"]=len(feed["items"])
feed["social_api_status"]=status
feed["social_api_checked_at"]=NOW.isoformat()
feed["coverage_note"]=(feed.get("coverage_note","")+" Direct social APIs run when their GitHub secrets and platform approvals are configured.").strip()
FEED.write_text(json.dumps(feed,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"social_api_status":status,"new_social_leads":len(items)}))
