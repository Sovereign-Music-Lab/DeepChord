# Sovereign Music Lab 랜딩페이지

[English](landing-page.md) · **한국어**

- 한국어: https://sovereign-music-lab.github.io/
- English: https://sovereign-music-lab.github.io/en/
- 웹사이트 저장소: https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io

소스는 DeepChord 저장소의 `site/`에 있습니다. 이 하위 폴더만 웹사이트 저장소에 배포합니다. 정적 HTML·CSS·JavaScript, 로고·공유 이미지, 문서·라이선스, 검색 엔진 안내 파일을 포함합니다. 원본 교재, 교재 기반 RAG 기록, 모델·어댑터, 생성 음악과 개인 실행 설정은 포함하지 않습니다.

## 수정과 미리보기

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

한국어 페이지는 `http://127.0.0.1:8765/`, 영어 페이지는 `http://127.0.0.1:8765/en/`에서 확인합니다. 두 HTML을 함께 수정하고, 각 페이지의 `lang`, canonical·hreflang·OG 메타데이터를 유지하세요. 언어 링크는 JavaScript 없이도 동작하며, JavaScript가 켜져 있으면 현재 섹션을 유지합니다.

넓은 화면과 좁은 화면에서 배치, 목차, 언어 전환, 저장소·문서 링크, 명령 복사, 선택적 사운드 버튼을 확인하세요. 설치 안내의 명령은 README와 일치해야 합니다. 설치 검사 예제와 로컬 AI의 작곡을 구분하세요. 사운드는 설명을 위해 브라우저에서 합성하는 독창적 모티프이며 모델 생성 음악이 아닙니다. 자동 재생, 분석 도구, 외부 폰트 CDN, 백엔드는 없습니다.

```sh
python scripts/check_site.py
python scripts/check_public.py
```

## 파비콘과 링크 미리보기

- `assets/mark.svg`: 벡터 파비콘.
- `assets/favicon-32.png`, `favicon.ico`: 기본 아이콘 호환용.
- `assets/apple-touch-icon.png`: 180×180 터치 아이콘.
- `assets/og-ko.png`, `assets/og-en.png`: 언어별 1200×630 공유 이미지.

이미지는 프로젝트의 도형·타이포그래피로 제작했으며 개인 자료를 사용하지 않습니다. PNG 메타데이터는 제거했습니다. 공개 검사기는 검토한 이미지 파일의 정확한 경로와 SHA-256을 허용합니다. 이미지를 교체할 때 시각 검토 후 허용 해시를 갱신하세요. 다른 바이너리 파일을 포괄적으로 허용하지 마세요.

## 변경사항 배포

검토한 파일을 커밋하고 DeepChord에 푸시한 뒤 사이트 하위 폴더만 배포하세요.

```sh
git push origin main
git subtree split --prefix=site -b pages-release
git push https://github.com/Sovereign-Music-Lab/Sovereign-Music-Lab.github.io.git pages-release:main
```

`pages-release`가 이미 있으면 새 임시 브랜치 이름을 사용하세요. 원격이 변경됐다면 강제 푸시하지 말고 소스를 확인해 반영하세요. GitHub Pages는 `main` 루트를 사용합니다. 빌드 완료와 두 언어 페이지·이미지의 실제 응답을 확인하세요.

표기: Hee-sung Kang(강희성), Do-won Lee(이도원), **Sungmo Park(박성모)**. 링크와 이메일은 프로젝트 소유자의 요청으로 공개합니다. 별도의 직책이나 역할은 추정하지 않습니다.

공개 코드의 라이선스는 [Apache License 2.0](../LICENSE)입니다.
