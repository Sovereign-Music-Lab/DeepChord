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

MCP 서버의 설치와 권한 설정은 해당 프로젝트의 안내를 따르세요. DeepChord는 선택한 TOML을 읽고, MCP 버전을 협상한 뒤 읽기 전용 상태·세션·리전 도구를 호출합니다. 자신이 만든 자식 프로세스만 종료하며 OS 권한을 변경하거나 다른 서버를 중단하지 않습니다. 기존 서버가 MIDI 포트를 사용 중이면 두 번째 인스턴스에서 CoreMIDI 사용 불가를 보고할 수 있습니다. 전체 MIDI 파일의 Launch Services 전달은 이 포트에 의존하지 않습니다.

현재 연동 대상의 `import_file`은 서버가 등록한 임시 파일 경로만 허용합니다. DeepChord는 이 경계를 준수하며 임시 경로를 위조하거나 서버를 수정하지 않습니다. `record_sequence`는 편집 가능한 CC64 데이터를 전달하지 못하므로 전체 MIDI의 대체 수단으로 쓰지 않습니다.

자료: [Logic Pro MCP](https://github.com/MongLong0214/logic-pro-mcp), [MCP 수명 주기](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle).

## 공개 기초 자산과 반복 세션

[공개 기초 자산 안내](foundation.ko.md)는 Linux·Windows의 MIDI 내보내기와 Mac의 반복 세션 전달을 설명합니다. 기존 작곡 JSON 레코드도 계속 지원합니다.
