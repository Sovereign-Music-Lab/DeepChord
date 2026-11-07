#!/bin/zsh
# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/deepchord ]]; then
  printf 'Run the README installation commands first. / 먼저 README의 설치 명령을 실행하세요.\n'
  exit 1
fi
export SOVEREIGN_MUSIC_HOME="$PWD/.private"
if [[ -d ../musicRAG ]]; then
  export MUSIC_RAG_ROOT="$(cd ../musicRAG && pwd)"
fi
printf 'DeepChord · Sovereign Music Lab\n1 한국어 / 2 English [1]: '
IFS= read -r music_language
if [[ "$music_language" == 2 ]]; then
  printf 'Installed Ollama model name: '
else
  printf '설치된 Ollama 모델 이름: '
fi
IFS= read -r music_model
if [[ "$music_language" == 2 ]]; then
  printf 'Describe the piece you want to compose: '
else
  printf '만들 곡을 입력하세요: '
fi
IFS= read -r music_prompt
if [[ -n "$music_model" && -n "$music_prompt" ]]; then
  .venv/bin/deepchord compose "$music_prompt" --model "$music_model" --bars 4 --logic
fi
if [[ "$music_language" == 2 ]]; then
  printf '\nPress Enter to exit.'
else
  printf '\n종료하려면 Enter를 누르세요.'
fi
IFS= read -r music_exit
