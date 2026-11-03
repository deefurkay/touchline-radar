# Touchline Radar

Mobile-friendly installable web app for tracking Scottish football coaching vacancies within 10 miles of Shawlands, Glasgow.

## Current features
- Add, edit and delete vacancy records
- Search by club, role, team, location and notes
- Filter by status and team level
- Track New, Interested, Applied and Closed statuses
- Record distance, date found, deadline, source URL and contact notes
- Export vacancies to CSV
- Offline app shell via service worker
- Local browser storage

## Important
This is the first working tracker version. It does not yet automatically scrape social media or sync data between devices. The next stage is to connect a hosted database and a scheduled search/verification service. Social media access depends on platform APIs, permissions and public visibility.

## Deploy
Enable GitHub Pages in repository Settings → Pages → Deploy from a branch → main → /(root). Wait for the Pages URL to appear. Open that URL in Chrome on Android and choose Install app / Add to Home screen.
