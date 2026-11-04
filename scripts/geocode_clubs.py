#!/usr/bin/env python3
"""Geocode actual club venues and calculate straight-line distance from Shawlands.
Only a precise venue is measured. Vague or multi-site training descriptions remain
unverified rather than being assigned a guessed distance.
"""
import json, math, re, time, urllib.parse, urllib.request
from pathlib import Path

CENTRE = (55.8298, -4.2820)  # Shawlands Cross, Glasgow
RADIUS = 10.0
HEADERS = {"User-Agent": "TouchlineRadar/1.0 (local football venue distance checker)"}
VAGUE = re.compile(r"to confirm|confirm|multiple|various|team-specific|team specific|check the|several|south glasgow|east renfrewshire /", re.I)

def distance(a,b):
    lat1,lon1=map(math.radians,a); lat2,lon2=map(math.radians,b)
    dlat=lat2-lat1; dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3958.7613*2*math.asin(math.sqrt(h))

def geocode(address):
    url="https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode({
        "q":address+", Scotland, UK","format":"jsonv2","limit":1
    })
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=20) as response:
        rows=json.loads(response.read().decode("utf-8"))
    if not rows: return None
    return (float(rows[0]["lat"]),float(rows[0]["lon"]),rows[0].get("display_name",""))

path=Path("clubs.json")
data=json.loads(path.read_text(encoding="utf-8"))
cache={}
for club in data.get("clubs",[]):
    training=(club.get("trainingBase") or "").strip()
    home=(club.get("homeGround") or "").strip()
    # A specific training venue takes precedence. Vague or multi-site wording
    # falls back to the home ground, and is clearly labelled as such.
    use_training=bool(training and not VAGUE.search(training) and training.lower() not in {"to confirm","unknown","not known"})
    venue=training if use_training else home
    if not venue or VAGUE.search(venue) or venue.lower() in {"to confirm","unknown","not known"}:
        club["distanceMiles"]=None
        club["distanceStatus"]="Unverified — exact team venue needed"
        club["distanceBasis"]="No sufficiently precise venue supplied"
        continue
    key=venue.casefold()
    try:
        if key not in cache:
            cache[key]=geocode(venue)
            time.sleep(1.1)  # Nominatim public service usage limit
        point=cache[key]
        if not point:
            club["distanceMiles"]=None
            club["distanceStatus"]="Unverified — venue could not be geocoded"
            club["distanceBasis"]=venue
            continue
        miles=round(distance(CENTRE,point[:2]),1)
        club["distanceMiles"]=miles
        club["distanceStatus"]="Within 10 miles" if miles<=RADIUS else "Outside 10 miles"
        club["distanceBasis"]="Training base" if use_training else "Home ground proxy — team training base not verified"
        club["geocodedVenue"]=point[2]
    except Exception as exc:
        club["distanceMiles"]=None
        club["distanceStatus"]="Unverified — geocoding unavailable"
        club["distanceBasis"]=venue
        print("Geocoding error",club.get("name"),str(exc)[:160])
data["distance_check"]={
    "centre":"Shawlands Cross, Glasgow",
    "radius_miles":RADIUS,
    "method":"Straight-line distance from Shawlands Cross to the geocoded training venue; home ground is used only as a clearly labelled proxy where no precise training venue is recorded.",
    "checked_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    "provider":"OpenStreetMap Nominatim"
}
data["clubs"].sort(key=lambda c:c.get("name","").casefold())
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
verified=sum(1 for c in data["clubs"] if c.get("distanceMiles") is not None)
print("Distance checks:",verified,"of",len(data["clubs"]))
