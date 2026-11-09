# Logic 연결

[English](logic.md) · **한국어**

`deepchord logic open RUN`은 `composition.json`에서 새 MIDI를 만들고, 셸 문자열 대신 인자 배열로 macOS Launch Services에 전달합니다. 음표와 마디별 페달 이벤트를 유지합니다. 페달 데이터가 사라지는 음표 전용 실시간 스트림으로 변환하지 않습니다.

Logic은 Standard MIDI File을 새 프로젝트로 열 수 있습니다. 개발 중 GUI 검사에서는 Studio Grand가 자동 배정됐지만, 다른 환경에서도 이를 보장하지 않습니다. 프로젝트 생성이나 템포 관련 대화상자를 확인하세요. 명령만으로 음표·컨트롤러의 동일성이나 실제 소리 재생을 증명할 수 없으므로 결과 보고서의 `import_verified`, `audio_verified`는 false로 남습니다. 프로세스 성공만으로 완성된 Logic 프로젝트라고 판단하지 않습니다.

```sh
deepchord logic open /path/to/run
```

## 선택적 MCP 설정

다음 설정을 저장소 밖의 개인 TOML 파일에 저장하세요.

```toml
[logic]
command = "/path/to/LogicProMCP"
args = []

[logic.env]
LOGIC_PRO_BUNDLE_ID = "com.apple.logic10"
```

```sh
deepchord logic inspect --mcp-config /path/to/private/logic.toml
deepchord logic open /path/to/run --mcp-config /path/to/private/logic.toml
```

MCP 서버의 설치와 권한 설정은 해당 프로젝트의 안내를 따르세요. DeepChord는 선택한 TOML을 읽고 MCP 버전을 협상합니다. 자신이 만든 자식 프로세스만 종료하며 OS 권한을 변경하거나 다른 서버를 중단하지 않습니다. 기존 서버가 MIDI 포트를 사용 중이면 두 번째 인스턴스에서 CoreMIDI 사용 불가를 보고할 수 있습니다. 전체 MIDI 파일의 Launch Services 전달은 이 포트에 의존하지 않습니다.

`deepchord logic build RUN --out /path/to/new.logicx --mcp-config /path/to/logic.toml`은 필요한 경우 Logic을 실행하고, 프로젝트 선택 화면에서 새 MIDI를 연 뒤 리전 이름과 길이를 확인하고 새 프로젝트로 저장합니다. 이미 존재하는 저장 경로나 불확실한 상태에서는 중단합니다. `session --logic-project /path/to/new.logicx --mcp-config /path/to/logic.toml`은 마지막 요청이 성공한 뒤 같은 작업을 수행합니다. 기존 프로젝트를 직접 수정하지는 않습니다. 저장 경로와 리전이 확인되어도 모든 음표의 일치나 실제 소리를 증명하는 것은 아닙니다. 상태는 `logic-build.json`에 기록되며 저장 화면을 확인할 수 없으면 실패할 수 있습니다.

현재 연동 대상의 `import_file`은 서버가 등록한 임시 파일 경로만 허용합니다. DeepChord는 이 경계를 준수하며 임시 경로를 위조하거나 서버를 수정하지 않습니다. `record_sequence`는 편집 가능한 CC64 데이터를 전달하지 못하므로 전체 MIDI의 대체 수단으로 쓰지 않습니다.

자료: [Logic Pro MCP](https://github.com/MongLong0214/logic-pro-mcp), [MCP 수명 주기](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle).

## 공개 기초 자산과 반복 세션

[공개 기초 자산 안내](foundation.ko.md)는 Linux·Windows의 MIDI 내보내기와 Mac의 반복 세션 전달을 설명합니다. 기존 작곡 JSON 레코드도 계속 지원합니다.

## 기존 곡의 음표 편집

현재는 **음표 하나를 높이거나 낮추기**, **리전 하나를 다른 마디로 옮기기**를 지원합니다. 저장된 곡의 사본에서 작업하며, Codex를 켤 필요는 없습니다. 영어로 표시되는 Logic의 이벤트 목록을 대상으로 검사합니다.

처음 한 번은 확장 도구를 설치하세요. Mac의 Xcode 개발 도구가 필요하며, 소스를 내려받아 만들기 때문에 몇 분 걸릴 수 있습니다. 기존 MCP 설치는 덮어쓰지 않습니다.

```sh
deepchord logic setup --out "$HOME/Music/DeepChord-Logic"
```

완료되면 그 폴더에 `logic.toml` 설정 파일이 생깁니다. macOS가 손쉬운 사용 권한을 요청하면 시스템 설정에서 허용하세요. 이 설치 과정은 AI 모델을 내려받지 않습니다. Ollama와 로컬 Gemma는 따로 준비해야 합니다.

먼저 원본 곡을 저장하세요. 다음 명령에서 `song.logicx`를 실제 곡으로, `song-edited.logicx`를 아직 없는 새 이름으로 바꿉니다. `Piano`는 곡에 있는 리전 이름입니다.

```sh
deepchord logic edit-note "$HOME/Music/song.logicx" 'Piano 리전의 첫 음표를 온음 올려줘' \
  --out "$HOME/Music/song-edited.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

리전을 옮길 때는 아래 명령을 사용합니다. `5마디`는 새로 시작할 위치입니다. 리전 길이와 트랙은 그대로 두고, 안에 있는 음표와 페달이 함께 이동합니다.

```sh
deepchord logic move-region "$HOME/Music/song.logicx" 'Piano 리전을 5마디 시작으로 옮겨줘' \
  --out "$HOME/Music/song-moved.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

DeepChord는 저장된 원본에서 사본을 만들고, 필요한 경우 Logic을 실행합니다. Gemma가 요청한 리전을 찾아 변경합니다. 음표 수정에서는 페달이 그대로인지, 리전 이동에서는 페달도 같은 거리만큼 이동했는지 검사합니다. 화면에서 확인한 다른 MIDI 리전도 전후로 비교합니다. 저장한 파일을 다시 읽기까지 통과해야 성공으로 표시합니다. 작업 중에는 Mac 화면을 잠그지 않고 Logic을 조작하지 마세요. DeepChord가 편집 전에 Logic을 앞으로 가져옵니다. 긴 목록은 모든 행을 두 번씩 확인하므로 몇 분 걸릴 수 있습니다.

현재 검사는 Logic이 보여 주는 리전과 이벤트 목록을 기준으로 합니다. 숨긴 트랙이나 접힌 스택이 있는 복잡한 프로젝트는 아직 지원 범위 밖입니다.

완료되면 저장한 곡의 위치가 표시됩니다. 수정된 곡 옆의 `song-edited.deepchord` 폴더에는 수정 전후 기록과 저장 검사용 사본이 남습니다. 실패하면 이 기록과 작업 사본을 확인하세요. 확인되지 않은 변경은 자동 저장하지 않고, 같은 사본에 수정 명령을 자동 반복하지 않습니다. 원본의 저장하지 않은 변경, 패키지 내부의 연결 파일, 같은 이름의 여러 리전, 리전 늘이기·자르기·복제, 여러 음표 수정은 현재 지원 범위 밖입니다. 소리나 믹스 품질을 검사한 것은 아니므로 최종 청취는 별도로 하세요.

개발 검사에서는 122개 이벤트(음표 96개, 페달 25개, 프로그램 변경 1개)가 있는 프로젝트 사본으로 Gemma의 음표 선택, MCP 수정, 전체 이벤트 비교, 저장 파일 재열기를 통과했습니다. 원본 파일 해시도 동일했습니다. 이 결과가 모든 Logic 버전이나 프로젝트에 대한 보장은 아닙니다. 확장 소스는 고정한 MIT 라이선스의 Logic Pro MCP 버전에 적용하며, 코드와 라이선스는 패키지에 포함합니다.

두 리전이 있는 사본에서도 Gemma가 반주 리전을 골라 1마디에서 3마디로 옮기는 시험을 통과했습니다. 반주의 12개 이벤트가 함께 이동했고, 선율의 14개 이벤트는 유지됐습니다. 저장 파일 재열기와 원본 파일 비교도 통과했습니다. 검사는 Logic Pro 13.0의 영어 화면에서 수행했습니다.

개발자가 같은 조건을 다시 시험하려면 [시험용 MIDI 생성과 독립 검사 절차](logic-testing.ko.md)를 사용하세요. 개인 곡이나 비공개 실행 기록은 필요하지 않습니다.
