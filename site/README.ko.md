# Sovereign Music Lab

**Authors / Project credits:** [Hee-sung Kang · 강희성](https://ikoffices.com/) · [Do-won Lee · 이도원](https://music.bugs.co.kr/artist/80353758?wl_ref=list_ar_02_search) · [Sungmo Park · 박성모](mailto:vividsaebom@gmail.com)

[Organization](https://github.com/Sovereign-Music-Lab) · [Website](https://sovereign-music-lab.github.io/) · [DeepChord](https://github.com/Sovereign-Music-Lab/DeepChord) · [Sovereign DAW](https://github.com/Sovereign-Music-Lab/sovaroll-DAW) · [Sovereign Flow](https://github.com/Sovereign-Music-Lab/SovaFlow)

## 초록
[English](README.md) · **한국어**

인간의 지식에서, 로컬 AI를 거쳐, 다시 인간의 연주로.

Sovereign Music Lab과 로컬 피아노 작곡 도구 **DeepChord**를 소개하는 영어·한국어 웹사이트입니다.

- [한국어 웹사이트](https://sovereign-music-lab.github.io/)
- [English website](https://sovereign-music-lab.github.io/en/)
- [DeepChord 저장소와 설치 안내](https://github.com/Sovereign-Music-Lab/DeepChord/blob/main/README.ko.md)
- [DeepChord 설치하고 사용하기](https://sovereign-music-lab.github.io/#getting-started)

## 목차

- [개발](#개발)
- [크레딧](#크레딧)
- [라이선스와 비공개 자료](#라이선스와-비공개-자료)
- [개발 인계](#개발-인계)

## 개발

이 저장소는 DeepChord의 `site/` 하위 폴더에서 배포합니다. 도구와 웹사이트의 소스가 일치하도록 DeepChord에서 수정하세요.

```sh
git clone https://github.com/Sovereign-Music-Lab/DeepChord.git
cd DeepChord
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

`http://127.0.0.1:8765/`는 한국어, `http://127.0.0.1:8765/en/`는 영어입니다. 프레임워크, 빌드 단계, 백엔드 없이 동작합니다. 두 언어 페이지, 메타데이터, 인터랙션 메시지를 함께 수정하세요.

벡터 파비콘, PNG·ICO 호환 아이콘, 터치 아이콘, 언어별 1200×630 OG 공유 이미지를 포함합니다. 디자인은 직접 만든 도형과 타이포그래피를 사용합니다. 선택적 브라우저 사운드는 개념 설명용 합성 모티프이며 모델이 생성한 작곡 결과가 아닙니다.

[배포와 유지보수 안내](https://github.com/Sovereign-Music-Lab/DeepChord/blob/main/docs/landing-page.ko.md)

## 크레딧

- [Hee-sung Kang · 강희성](https://ikoffices.com/)
- [Do-won Lee · 이도원](https://music.bugs.co.kr/artist/80353758?wl_ref=list_ar_02_search)
- [Sungmo Park · 박성모](mailto:vividsaebom@gmail.com)

## 라이선스와 비공개 자료

코드는 [Apache License 2.0](LICENSE)을 따릅니다. 저작권 표기는 [NOTICE](NOTICE)를 확인하세요. 원본 PDF, 교재 기반 RAG 기록, 모델 가중치, 어댑터, 학습 자료, 개인 설정과 개인 음악은 포함하지 않습니다.

## 개발 인계

[CONTEXT.md](CONTEXT.md) · [Model operations / 모델 운영](docs/MODEL_OPERATIONS.ko.md) · [Reusable skill / 재사용 스킬](skills/model-tier-handoff/SKILL.md)
