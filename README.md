# District Times (districttimes.org)

Local news for Washington, D.C. A business unit of Atlas Media Network, LLC.

Static site in Python (Jinja2 + Markdown), newsroom panel with Decap CMS at `/admin/`, hosted on Netlify with automatic deploys from GitHub.

## Branches
- `main` = production (districttimes.org). Merging into `main` publishes.
- Any other branch (e.g. `borrador`) = Netlify preview only.

## Content
- Articles: `content/articles/*.md` (created from `/admin/`).
- Fixed pages: `content/pages/*.md` (About, Standards, Corrections, Contact, Privacy).
- Sections: `sections.json`. Site settings: `site.json` (`"prelaunch": false` at launch removes the preview banner and `noindex`).

## Editorial checks enforced by the build
An article will not build unless it has a headline, section, byline, date, standfirst and at least one linked source. The build fails and names the file.

## Local build
```
pip install -r requirements.txt
python3 build.py      # writes dist/
```

## Newsroom panel (/admin/)
Uses the GitHub backend through Netlify's OAuth provider. In Netlify: Project configuration → Access & security → OAuth → install the GitHub provider (needs a GitHub OAuth App whose callback URL is `https://api.netlify.com/auth/done`). Editors need write access to this repository. With the editorial workflow, drafts are pull requests; "Publish" merges into `main`.

## Before launch
- Privacy notice: legal review pending.
- Vector (SVG) or high-resolution logo to replace `static/img/site/logo.png`.
- Set `"prelaunch": false` in `site.json`.
- Connect the domain `districttimes.org` in Netlify and enable HTTPS.
- Do not use the identity-board image that shows the WMATA Metro "M" sign (third-party trademark).
