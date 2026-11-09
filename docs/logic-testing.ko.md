# Logic 편집 재현 시험

[English](logic-testing.md) · **한국어**

개발용 안내입니다. 개인 곡 대신 공개된 생성 코드로 만든 시험용 MIDI를 사용합니다. 이 패턴은 AI 작곡이나 음악 품질 평가가 아닙니다. 생성되는 MIDI, Logic 프로젝트와 실행 기록은 저장소 밖에 두세요.

## 준비

DeepChord 저장소에서 설치를 마치고 [Logic 확장 설정](logic.ko.md#기존-곡의-음표-편집)을 준비합니다. 아래 모델 이름은 실제로 설치된 로컬 Gemma의 이름이어야 합니다. 모델 다운로드나 클라우드 대체는 하지 않습니다.

Mac 화면을 잠그지 않고, 시험 중 Logic이나 다른 앱을 조작하지 않습니다. 먼저 자신의 작업을 저장하고 프로젝트를 닫으세요. `logic build`는 Logic이 닫혀 있으면 실행하며, 실행 중이면 프로젝트 선택 화면이 필요합니다.

```sh
python scripts/check_logic_fixture.py create "$HOME/Music/DeepChord-fixture"
deepchord logic build "$HOME/Music/DeepChord-fixture" \
  --out "$HOME/Music/DeepChord-fixture/Original.logicx" \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

`Target`에는 음표 96개, `Untouched`에는 음표 8개가 들어갑니다. 각 리전에는 페달 이벤트 25개와 프로그램 변경 1개가 있습니다. 두 리전은 1마디에서 시작하는 8마디 길이입니다. `build` 성공만으로 모든 이벤트가 맞게 들어왔다고 판단하지 않습니다. 아래 독립 검사에서 수정 전 기록까지 확인합니다.

## 리전 이동과 저장 확인

```sh
deepchord logic move-region "$HOME/Music/DeepChord-fixture/Original.logicx" \
  'Target 리전을 3마디 시작으로 옮겨줘. 다른 리전은 그대로 유지해줘.' \
  --out "$HOME/Music/DeepChord-fixture/Moved.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
python scripts/check_logic_fixture.py check "$HOME/Music/DeepChord-fixture/Moved.deepchord"
```

검사기는 수정 전·후·저장 파일 재열기 기록을 처음 생성한 패턴과 별도로 대조합니다. 음표의 위치·높이·세기·길이·채널, 페달의 위치·값·채널·개수, 프로그램 변경, 다른 리전과 원본 파일 해시를 확인합니다. 편집 코드의 자체 비교 함수를 재사용하지 않습니다. 마지막 페달 해제 하나가 빠져도 실패해야 합니다.

반대 방향으로도 시험하려면 `Moved.logicx`를 입력으로 사용하여 “Target 리전을 1마디 시작으로 옮겨줘”라고 요청하고, 새 출력 이름을 지정하세요. 결과 폴더를 검사할 때 `--before-bar 3 --after-bar 1`을 붙입니다.

## 음표 수정 확인

```sh
deepchord logic edit-note "$HOME/Music/DeepChord-fixture/Original.logicx" \
  'Target 리전의 첫 번째 음표를 반음 올려줘. 페달과 다른 음표는 그대로 유지해줘.' \
  --out "$HOME/Music/DeepChord-fixture/Pitched.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
python scripts/check_logic_fixture.py check "$HOME/Music/DeepChord-fixture/Pitched.deepchord" \
  --after-bar 1 --first-note-semitones 1
```

항상 새 출력 이름을 사용합니다. 실패한 사본에 음악 수정 명령을 반복하지 마세요. 실패가 수정 전에 일어났다면 `check ... --baseline-only`로 가져온 원래 이벤트만 확인할 수 있습니다. 이 결과는 편집·저장 성공을 뜻하지 않습니다.

## 검증 범위

검사기는 이 고정 패턴과 Logic의 4/4·960틱 이벤트 표시에 한정됩니다. 임의의 사용자 곡, 숨긴 트랙·접힌 스택, 악기 음색이나 청취 품질을 검증하지 않습니다. 테스트용 기록을 검사하는 도구이며 기록의 진위를 암호학적으로 인증하지 않습니다. 실제 실행의 성공 여부와 원본 기록을 함께 보관하세요.

2026-11-09 현재 공개 검사기는 실제 다중 리전 시험의 수정 전 기록(122개와 34개 이벤트)에 대조했습니다. 전체 저장 검사와 오류 검출은 합성 기록으로 자동 테스트했습니다. **최신 설치본의 긴 다중 리전 이동·저장·재열기 실기 시험은 아직 미완료입니다.** 이 문서는 통과 주장 대신 재현 절차를 제공합니다. 이전에 통과한 실기 범위는 [Logic 안내](logic.ko.md)에 구분되어 있습니다.
