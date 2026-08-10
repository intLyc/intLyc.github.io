# Yanchi Li — Homepage

Personal academic homepage built with the [al-folio](https://github.com/alshedivat/al-folio) Jekyll template, deployed on GitHub Pages at **[https://intLyc.github.io](https://intLyc.github.io)**.

## Project structure

| Path                           | Description                                                |
| ------------------------------ | ---------------------------------------------------------- |
| `_pages/about.md`              | Homepage content (bio, profile picture, contact)           |
| `_bibliography/papers.bib`     | Publications (BibTeX)                                      |
| `_data/socials.yml`            | Social links (GitHub, ResearchGate, Google Scholar, email) |
| `_data/repositories.yml`       | GitHub repositories shown on the Repositories page         |
| `_data/venues.yml`             | Venue abbreviations → names/colors for publications        |
| `_data/citations.yml`          | Validated Google Scholar citation snapshot                 |
| `_data/github.yml`             | Stars across original (non-fork) GitHub repositories       |
| `_data/visitors.yml`           | Cumulative GoatCounter visitors by country                 |
| `_news/`                       | Latest news shown on the homepage                          |
| `assets/img/prof_pic.jpg`      | Profile photo                                              |
| `.github/workflows/deploy.yml` | GitHub Actions workflow that builds and deploys the site   |

## Deploy to GitHub Pages

The site is built automatically by GitHub Actions (`.github/workflows/deploy.yml`) and published to the `gh-pages` branch.

1. Create a new **public** repository on GitHub named `intLyc.github.io` (must match your username).
2. Push this folder to it:

   ```bash
   git remote add origin https://github.com/intLyc/intLyc.github.io.git
   git branch -M main
   git push -u origin main
   ```

3. In the repository **Settings → Actions → General → Workflow permissions**, select **Read and write permissions** and save.
4. In **Settings → Pages**, set **Source** to _Deploy from a branch_ and branch to **gh-pages** (the workflow publishes there automatically).
5. Wait for the "Deploy site" workflow to finish (~4 min), then visit https://intLyc.github.io.

## Local preview

Requires Ruby ≥ 3.2 (the macOS system Ruby is too old; e.g. install via `brew install ruby`):

```bash
bundle install
bundle exec jekyll serve
```

Then open http://localhost:4000.

## Dynamic data

- GitHub stars and cumulative GoatCounter visitors are validated and refreshed during each deployment. Transient GoatCounter failures are retried; every successful visitor snapshot is committed back to `main`, and a failed refresh deploys that validated last-known-good snapshot instead of reverting to seed data.
- Visitor totals start at `2026-08-08T00:00:00Z`, when GoatCounter tracking was enabled. Override `GOATCOUNTER_START` only when intentionally changing this baseline.
- Google Scholar is refreshed by `bin/refresh_local.sh` from a residential IP because Scholar blocks many datacenter addresses. Complete or decreasing snapshots are rejected unless an intentional Scholar profile removal is explicitly confirmed.

Run the data regression tests and formatting checks with:

```bash
npm test
```

## Customizing

- **Profile photo**: replace `assets/img/prof_pic.jpg` (keep roughly square).
- **Bio / affiliations**: edit `_pages/about.md`.
- **Publications**: edit `_bibliography/papers.bib`. Supported extra fields include `abbr`, `html`, `code`, `pdf`, `selected`, `note`, `preview`, etc. (see the al-folio docs).
- **Social links**: edit `_data/socials.yml`.
- **News**: add files under `_news/`.
- **GitHub repositories**: edit `_data/repositories.yml`.
