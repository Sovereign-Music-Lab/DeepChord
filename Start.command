#!/bin/zsh
# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/deepchord ]]; then
  printf 'Install first using README. / README의 설치 과정을 먼저 실행하세요.\n'
  exit 1
fi
printf 'Installed local model [gemma4:12b-mlx]: '
IFS= read -r music_model
music_model=${music_model:-gemma4:12b-mlx}
.venv/bin/deepchord session --name studio --model "$music_model" --bars 4
