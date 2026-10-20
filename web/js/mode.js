// Which copy of the website is this?
//   false = normal site, talks to the live FastAPI server (laptop, Render).
//   true  = static demo copy on GitHub Pages: reads precomputed JSON files instead of the API.
// api/export_static.py rewrites this file to `true` when it builds the GitHub Pages copy.
const STATIC_SITE = false;
