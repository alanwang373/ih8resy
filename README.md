# Resy Availability Dashboard (NiceGUI v1)

Lightweight self-hosted dashboard to poll Resy availability for cached venue IDs or via a best-effort discovery.

Quick start

1. Create a virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Provide your Resy tokens via env vars (do not commit these):

```bash
export RESY_API_KEY='ResyAPIKeyHere'
export RESY_AUTH_TOKEN='AuthTokenFromBrowser'
```

3. Run the app:

```bash
python app.py
```

Then open http://localhost:8080

Notes

- The client uses best-effort endpoint patterns for discovery and availability; you may need to adapt `resy_client.py` to match the live Resy endpoints and payloads.
- Tokens expire unpredictably; the UI will show an auth error when that happens and you can refresh tokens via env vars or Secret Manager.
- For production deployment consider containerizing and running on Cloud Run and storing secrets in GCP Secret Manager.
# ih8resy
## What is this?
A small tool to make finding Resy reservations easier. It filters results so you see relevant times without extra scrolling.

## TL;DR
Set filters once (date, time, party size) and stop manually hunting for reservations. I'm just as much of a foodie as you but Resy's UI is especially painful. 

## Why it exists
- Resy's interface makes important options hard to find.
- Booking should be quick, not a time sink.
- Centralized filters save repeated effort.

## Who it's for
- Busy people who don’t have time to refresh constantly.
- Former restaurant staff and regular diners who want a simpler view.
- Anyone who wants faster, more reliable searches.

## How it helps (quick)
- Filter by date, time, and party size.
- Save and reuse filters across searches.
- Cut down on manual refreshing and lost time.

“If you can’t beat the bots, write worse ones." - me, probably.
