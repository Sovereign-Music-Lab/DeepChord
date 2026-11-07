#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/sovereign-music ]]; then
  printf '먼저 README의 설치 명령을 실행하세요.\n'
  exit 1
fi
export SOVEREIGN_MUSIC_HOME="$PWD/.private"
if [[ -d ../musicRAG ]]; then
  export MUSIC_RAG_ROOT="$(cd ../musicRAG && pwd)"
fi
printf 'Sovereign Music Lab\n설치된 Ollama 모델 이름: '
IFS= read -r music_model
printf '만들 곡을 입력하세요: '
IFS= read -r music_prompt
if [[ -n "$music_model" && -n "$music_prompt" ]]; then
  .venv/bin/sovereign-music compose "$music_prompt" --model "$music_model" --bars 4 --logic
fi
printf '\n종료하려면 Enter를 누르세요.'
IFS= read -r music_exit
