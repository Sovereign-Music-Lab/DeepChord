# Sovereign Music Lab

**Authors / Project credits:** [Hee-sung Kang · 강희성](https://ikoffices.com/) · [Do-won Lee · 이도원](https://music.bugs.co.kr/artist/80353758?wl_ref=list_ar_02_search) · [Sungmo Park · 박성모](mailto:vividsaebom@gmail.com)

[Organization](https://github.com/Sovereign-Music-Lab) · [Website](https://sovereign-music-lab.github.io/) · [DeepChord](https://github.com/Sovereign-Music-Lab/DeepChord) · [Sovereign DAW](https://github.com/Sovereign-Music-Lab/sovaroll-DAW) · [Sovereign Flow](https://github.com/Sovereign-Music-Lab/SovaFlow)

## Abstract
**English** · [한국어](README.ko.md)

Human knowledge. Local intelligence. Human performance.

The bilingual public website for Sovereign Music Lab and **DeepChord**, our local piano composition toolkit.

- [English website](https://sovereign-music-lab.github.io/en/)
- [한국어 웹사이트](https://sovereign-music-lab.github.io/)
- [DeepChord repository and installation](https://github.com/Sovereign-Music-Lab/DeepChord)
- [Install and use DeepChord](https://sovereign-music-lab.github.io/en/#getting-started)

## Contents

- [Develop](#develop)
- [Credits](#credits)
- [License and private materials](#license-and-private-materials)
- [Development handoff](#development-handoff)

## Develop

This repository is published from the `site/` subtree of DeepChord. Make source changes there so the toolkit and website stay in sync.

```sh
git clone https://github.com/Sovereign-Music-Lab/DeepChord.git
cd DeepChord
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open `http://127.0.0.1:8765/` for Korean or `http://127.0.0.1:8765/en/` for English. No framework, build step or backend is needed. Update both language pages, their metadata and any interactive messages together.

The website includes a vector favicon, PNG/ICO fallbacks, a touch icon and separate 1200×630 Korean/English Open Graph images. The design uses original geometry and typography. The optional browser sound is an illustrative synthesized motif, not a model-generated composition.

[Publication and maintenance guide](https://github.com/Sovereign-Music-Lab/DeepChord/blob/main/docs/landing-page.md)

## Credits

- [Hee-sung Kang](https://ikoffices.com/)
- [Do-won Lee](https://music.bugs.co.kr/artist/80353758?wl_ref=list_ar_02_search)
- [Sungmo Park](mailto:vividsaebom@gmail.com)

## License and private materials

Code is licensed under [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution. Original PDFs, book-derived RAG records, model weights, adapters, datasets, private configuration and personal music are not included.

## Development handoff

[CONTEXT.md](CONTEXT.md) · [Model operations / 모델 운영](docs/MODEL_OPERATIONS.en.md) · [Reusable skill / 재사용 스킬](skills/model-tier-handoff/SKILL.md)
