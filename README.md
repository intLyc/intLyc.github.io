# Yanchi Li — Homepage

Personal academic homepage migrated from GitBook, hosted on GitHub Pages at
**[https://intLyc.github.io](https://intLyc.github.io)**.

## Project structure

```
intLyc.github.io/
├── index.html            # Main homepage
├── 404.html              # Custom 404 page
├── .nojekyll             # Disables Jekyll processing (pure static site)
├── assets/
│   ├── css/style.css     # Styles
│   └── img/
│       ├── profile.jpg   # Profile photo
│       └── favicon.svg   # Site favicon
└── README.md
```

## How to publish on GitHub Pages

This folder is a Git repository already. To publish:

1. Create a **new public repository** on GitHub named exactly
   `intLyc.github.io` (your GitHub username + `.github.io`). This special name
   makes GitHub serve the site automatically at `https://intLyc.github.io`.
2. Push this folder to that repository:

   ```bash
   git remote add origin https://github.com/intLyc/intLyc.github.io.git
   git branch -M main
   git push -u origin main
   ```

3. In the repository **Settings → Pages**, choose **Deploy from a branch**
   (`main` branch, `/` (root) folder). For a `<username>.github.io` repo,
   Pages is enabled automatically — the site will be live within a few
   minutes.

> Tip: after pushing, your new homepage will temporarily replace your current
> GitBook-based site. Keep the old GitBook content backed up until the new
> site is verified.

## Customize

- **Profile photo**: replace `assets/img/profile.svg` with your photo (e.g.
  save as `assets/img/profile.jpg`) and update the `<img>` tag in
  `index.html`. Keep it roughly square (188×188 px works well).
- **Email**: the email link is in the "About" section of `index.html`.
- **Publications**: edit the `<li class="pub">` entries in `index.html` to
  add or update papers.
- **Colors / fonts**: all design tokens (colors, radius, shadow) are CSS
  variables at the top of `assets/css/style.css`.

## Local preview

Open `index.html` in a browser, or run a local server:

```bash
python3 -m http.server 8000
```

then visit http://localhost:8000.
