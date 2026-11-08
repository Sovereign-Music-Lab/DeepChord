# Sovereign Music Lab landing page

**English** · [한국어](landing-page.ko.md)

Korean: https://sovereign-music-lab.github.io/

English: https://sovereign-music-lab.github.io/en/

Website repository: https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io

The source is `site/` inside this working repository. Only that subtree is published to the website repository. It contains static HTML/CSS/JavaScript, original brand images, bilingual documentation, license files, robots/sitemap files and `.nojekyll`. No original books, book-derived RAG records, models, adapters, generated music, or runtime configuration are included.

## Edit and preview

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open `/` for Korean and `/en/` for English. Edit both HTML pages and keep their `lang`, canonical/hreflang/OG metadata and interactive messages in sync. The language switch works without JavaScript; with JavaScript it preserves the current section. Check desktop and narrow layouts, contents links, the DeepChord repository/documentation links, command-copy buttons and the optional sound button. The installation guide uses the public DeepChord CLI; keep its commands aligned with README.md and distinguish the deterministic demo from local-model composition. The sound is an original browser-synthesized conceptual motif, not a model-generated music result. There is no autoplay, analytics, font CDN or backend.

## Publish changes

Commit the reviewed site changes, push DeepChord, then publish only the subtree:

```sh
git push origin main
git subtree split --prefix=site -b pages-release
git push https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io.git pages-release:main
```

Use a new temporary branch name if `pages-release` already exists. Do not force-push when the remote has changed; inspect and reconcile the website source first. GitHub Pages is configured for the root of `main`. Confirm the Pages build completes and the public URL serves the updated page.

The credit names are romanized as Hee-sung Kang (강희성), Do-won Lee (이도원), and Sungmo Park (박성모). Their supplied URLs and email are public at the project owner's request; no titles or professional roles were inferred.

## Brand assets and checks

`assets/mark.svg` is the vector favicon, with `assets/favicon-32.png`, `favicon.ico` and `assets/apple-touch-icon.png` as fallbacks and a 180×180 touch icon. `assets/og-ko.png` and `assets/og-en.png` are separate 1200×630 social previews, made from original project geometry and typography. PNG metadata is stripped.

The public-file scanner accepts only the exact reviewed image paths and SHA-256 values. Review replacement artwork before updating its digest; never broadly allow binary files. Run `python scripts/check_site.py` and `python scripts/check_public.py` before publishing.

Public code is licensed under [Apache License 2.0](../LICENSE).
