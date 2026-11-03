# Touchline Radar — social API setup

The daily GitHub Actions workflow now runs an optional direct social ingestion step after the public search-index discovery step.

## What it supports

- **X:** Recent Posts search via X API v2. Searches the previous seven days.
- **Facebook:** Reads posts from configured Page IDs through Meta Graph API. Reading Pages that the app does not manage requires Meta's Page Public Content Access approval. A Page access token for Pages you manage can read that Page's posts.
- **Instagram:** Hashtag recent-media search via Instagram Graph API. Requires an eligible Instagram Professional account, linked Facebook Page, required permissions and Meta app review. This is not unrestricted search of all Instagram accounts.

The app does not scrape private accounts, bypass login controls, or use browser automation to evade platform restrictions.

## Add credentials to GitHub

In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.

Add these secrets when available:

| Secret | Value |
|---|---|
| `X_API_BEARER_TOKEN` | X developer app Bearer Token |
| `META_ACCESS_TOKEN` | Meta access token approved for the required Page/Instagram permissions |
| `META_PAGE_IDS` | Comma-separated Facebook Page IDs to monitor |
| `INSTAGRAM_USER_ID` | Instagram Professional account ID connected to the Meta app |

Optional repository variable under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Value |
|---|---|
| `INSTAGRAM_HASHTAGS` | Comma-separated hashtags, without #; default list is used if omitted |

Never commit access tokens into source files, JSON, or this README.

## Meta app permissions

For Facebook public Page discovery, request and obtain approval for **Page Public Content Access**. For Pages you administer, configure the relevant Page permissions and Page access token. See Meta's [Page Public Content Access feature](https://developers.facebook.com/docs/features-reference/page-public-content-access/) and [Page API reference](https://developers.facebook.com/docs/graph-api/reference/page/).

For Instagram hashtag discovery, use an Instagram Professional account connected to a Facebook Page, configure the Instagram Graph API, and request the permissions / feature required for public hashtag media. See the [Meta Instagram API documentation](https://developers.facebook.com/docs/instagram-platform/).

## X setup

Create a developer project and app in the [X Developer Console](https://developer.x.com/), generate a Bearer Token, then store it as `X_API_BEARER_TOKEN`. The adapter uses Recent Search, which covers the previous seven days. X's current API access is consumption-based; check the live [X API pricing](https://developer.x.com/en/products/x-api) before enabling it at scale.

## Test

After saving the secrets, go to **Actions → Daily vacancy discovery → Run workflow**. The workflow logs the social adapter's connection status. The dashboard's social status line reports which adapters are configured. A missing token is reported as not configured; it is not treated as a successful connection.

## Important coverage note

Direct API access is additive. Public search-index discovery remains enabled. Social platforms limit which public content third-party apps can access, so the system cannot promise every post or every club account. The best coverage combines direct APIs, club-specific public web searches, official club websites and manually verified account watchlists.
