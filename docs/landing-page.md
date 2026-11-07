# Sovereign Music Lab landing page

Public URL: https://sovereign-music-lab.github.io/

Website repository: https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io

The source is `site/` inside this working repository. Only that subtree is published to the website repository. It contains static HTML/CSS/JavaScript, an original vector mark, robots/sitemap files and `.nojekyll`. No original books, RAG records, models, adapters, generated music, or runtime configuration are included.

## Edit and preview

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open the printed local URL. Check desktop and narrow layouts, the contents links and the optional sound button. The sound is an original browser-synthesized conceptual motif, not a model-generated music result. There is no autoplay, analytics, font CDN or backend.

## Publish changes

Commit the reviewed site changes locally, then publish only the subtree:

```sh
git subtree split --prefix=site -b pages-release
git push https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io.git pages-release:main
```

Use a new temporary branch name if `pages-release` already exists. Do not force-push when the remote has changed; inspect and reconcile the website source first. GitHub Pages is configured for the root of `main`. Confirm the Pages build completes and the public URL serves the updated page.

The credit names are romanized as Hee-sung Kang (강희성), Do-won Lee (이도원), and Seong-mo Park (박성모). Their supplied URLs and email are public at the project owner's request; no titles or professional roles were inferred.
