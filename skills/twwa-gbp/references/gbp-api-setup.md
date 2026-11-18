# Business Profile API access (step by step)

1. Google Cloud project for TWWA (one for the agency). Billing not required for these APIs.
2. Prerequisites for the access request: a Business Profile that is verified and active for 60+ days (TWWA's own or a client's), a website on that profile, and the applicant's e-mail listed as owner or manager of it (domain-matching e-mail recommended).
3. Submit the "Application for Basic API Access" via the GBP API contact form (Google Business Profile APIs > Prerequisites > request access). Review takes about 14 days; practitioners report longer waits.
4. Check status: in Cloud Console > APIs > quotas, "My Business Business Information API" shows 0 QPM (not approved) or 300 QPM (approved).
5. Enable: My Business Account Management API, My Business Business Information API, Business Profile Performance API, My Business Notifications API, Google My Business API (v4.9: reviews, local posts, media).
6. OAuth consent screen (internal if Workspace, else external with yourself as test user); OAuth client type "Desktop app"; download the client secrets JSON outside every repo.
7. Agency access to clients: invite TWWA's Google user (or an organisation account with location groups) as manager on each client profile; owners stay owners.
8. `gbp.py auth --client-secrets <file>` stores the refresh token at `~/.config/twwa-growth/google-token.json` (mode 600).
Limits: 300 QPM, 10 edits per minute per profile. The Q&A API was discontinued on 2025-11-03; Q&A is replaced by Ask Maps in some countries.
