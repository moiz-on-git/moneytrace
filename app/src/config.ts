/**
 * Where the app reads its data from.
 *
 * The backend is a public, read-only JSON API committed to this repo by the
 * GitHub Action. There is no server to deploy.
 *
 * Two ways to serve it (both free):
 *
 *   1. raw.githubusercontent  (default) - works immediately after you push.
 *      ~5 minute cache, fine for a daily brief.
 *
 *   2. GitHub Pages on /docs  - nicer URLs, proper caching, real CORS.
 *      Settings -> Pages -> Source: Deploy from a branch -> main / docs.
 *      Then set USE_PAGES = true below.
 */
export const REPO_OWNER = "YOUR_GITHUB_USERNAME";
export const REPO_NAME = "money-trace";
export const BRANCH = "main";
export const USE_PAGES = false;

export const API_BASE = USE_PAGES
  ? `https://${REPO_OWNER}.github.io/${REPO_NAME}/v1`
  : `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}/docs/v1`;

/** False until the placeholders above are replaced; the UI explains what to do. */
export const IS_CONFIGURED = REPO_OWNER !== "YOUR_GITHUB_USERNAME";

export const REQUEST_TIMEOUT_MS = 12000;
