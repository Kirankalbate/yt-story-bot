# Story-page YouTube bot

Add a folder per story: `stories/<name>/1.jpg, 2.jpg...` (optional `title.txt`, `description.txt`).
Every day GitHub Actions picks the next folder -> OCR -> Hindi voice -> video -> YouTube.

## Setup (one time)
1. Google Cloud Console: new project -> enable **YouTube Data API v3** -> OAuth consent screen
   (add yourself as test user) -> Credentials -> OAuth client ID -> *Desktop app* -> download JSON.
2. On your PC: `pip install google-auth-oauthlib` then `python get_refresh_token.py client_secret.json`.
3. GitHub repo -> Settings -> Secrets -> Actions: add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
4. Push this folder to GitHub, upload story photos, run the workflow manually once to test.

## Notes
- Unverified API projects force uploads to *private*. Request an API audit/verification from YouTube to publish publicly.
- Voice: change `TTS_VOICE` (e.g. `hi-IN-MadhurNeural`, `en-IN-NeerjaNeural`). OCR language: `OCR_LANG`.
- Check OCR quality on a few pages first; fix by editing images (straight, high contrast).
