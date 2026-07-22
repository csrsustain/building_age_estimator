# Getting a shareable link for your colleagues

This turns your Colab prototype into a real web page with one URL —
colleagues just open it in a browser, no code, no API key needed on their
end.

## What you need
- A free GitHub account (github.com) if you don't have one
- A free Streamlit Community Cloud account (share.streamlit.io) — you can
  sign in directly with your GitHub account, no separate signup needed

## Step 1: Put this folder in a GitHub repository
1. Go to github.com, click "New repository". Name it something like
   `building-age-lookup`. Keep it **Private** if you don't want the code
   public (Streamlit Cloud can deploy from private repos too).
2. Upload all the files from this folder into that repo:
   - `app.py`
   - `requirements.txt`
   - `os_ngd_client.py`
   - `os_ngd_lookup.py`
   - `address_geocode.py`
   - `nominatim_geocode.py`
   - `single_lookup.py`
   (Easiest way: on the repo page, "Add file" -> "Upload files", drag them
   all in, commit.)

## Step 2: Deploy on Streamlit Community Cloud
1. Go to share.streamlit.io, sign in with GitHub.
2. Click "New app", pick your `building-age-lookup` repo, branch `main`,
   main file `app.py`.
3. **Before clicking Deploy**, open "Advanced settings" -> "Secrets" and
   paste in:
   ```
   OS_API_KEY = "your-actual-os-key-here"
   GOOGLE_API_KEY = "your-actual-google-key-here"
   ```
   GOOGLE_API_KEY is optional but recommended — it gives much better
   address-matching precision than the free fallback (Nominatim), which
   can sometimes only match a street rather than the exact building. Both
   keys are stored securely by Streamlit, never shown to anyone using the
   app, and never sit in your GitHub repo's code.
4. Click Deploy.

## Step 3: Share the link
After a minute or two, Streamlit gives you a URL like:
`https://building-age-lookup-yourname.streamlit.app`

Send that to your colleagues — they open it in any browser, type in an
address and postcode, click the button, done. No installs, no Colab, no
API key needed on their side.

## Notes
- The free tier is fine for a handful of colleagues testing this
  occasionally. If it gets heavy real usage, you'd look at paid hosting
  later — not a concern yet.
- If you regenerate your OS API key later (e.g. after the earlier
  exposure incidents), just update the value in Streamlit Cloud's Secrets
  panel — no redeploy of code needed, it picks it up automatically.
- Nominatim's 1 request/second rate limit still applies here — fine for a
  few colleagues clicking occasionally, would need attention if usage
  grows a lot.
