# 개인 MLX LoRA 학습

[English](training.md) · **한국어**

`config.json`, 토크나이저 파일, `.safetensors` 가중치를 갖춘 로컬 MLX 호환 모델을 준비하세요. Ollama의 저장 형식이나 모델 태그는 학습 입력이 아닙니다. 모델은 해당 이용 조건에 따라 별도로 준비하며, 학습 명령은 모델을 다운로드하지 않습니다. 확인한 백엔드는 Apple Silicon의 `mlx-lm[train]==0.32.2`입니다.

## 추가 설치와 기본 실행

DeepChord를 설치한 가상 환경에서 실행하세요. `/path/to/...`는 자신의 로컬 경로로 바꾸세요.

```sh
python -m pip install '.[train]'
deepchord train prepare /path/to/reviewed.jsonl --out /path/to/private/dataset
deepchord train run --model /path/to/local-mlx-model --data /path/to/private/dataset --out /path/to/private/adapter --iters 100
deepchord compose '4마디 피아노 스케치' --bars 4 --model /path/to/local-mlx-model --adapter /path/to/private/adapter
```

## 예제 검토와 그룹 지정

개인 JSONL 파일의 각 줄에는 다음 필드를 가진 객체가 있어야 합니다.

- `reviewed: true`: 자료 소유자가 음표 데이터와 학습에 사용하는 것을 검토했습니다.
- `group_id`: 하나의 원곡에서 나온 수정·이조·변형에는 같은 ID를 지정합니다. 같은 그룹은 동일한 데이터 분할에 남습니다.
- `messages`: 비어 있지 않은 사용자 요청 하나와 어시스턴트 응답 하나를 정확히 포함합니다. 응답 내용은 작곡 스키마(`title`, `tempo`, `bars`, `chords`, `tracks`)에 맞는 JSON 문자열이어야 합니다. 수정 가능한 예제는 `demo` 출력에서 확인하세요.

교재 문장이나 검토하지 않은 모델 응답을 학습 자료에 복사하지 마세요. 좋은 피드백 점수만으로 학습 사용을 승인한 것은 아닙니다. 도구는 데이터를 준비하기 전에 음표와 제한된 코드 이름을 검사하지만, 사람의 음악적 판단과 자료 사용 검토를 대신하지 않습니다.

`train prepare`에는 원곡 그룹이 최소 3개 필요합니다. 시드 42를 사용해 그룹을 학습·검증·테스트로 결정적으로 분리하며, 같은 정답 작곡 데이터는 서로 다른 분할에 들어갈 수 없습니다. 유용한 평가에는 훨씬 더 많은 독립적인 곡과 적절한 곡·스타일 단위 보류가 필요합니다. 출력 폴더는 새 폴더여야 합니다. 준비 시 분할 파일의 해시를 기록하며, 이후 자료가 바뀌면 학습을 거부합니다.

## 학습과 재사용

`train run`은 배치 크기 1, LoRA 레이어 2개, 프롬프트 마스킹, 그래디언트 체크포인팅, 2,048토큰 제한과 명시적인 반복 횟수를 사용합니다. 2,048토큰보다 긴 예제는 잘라내지 않고 학습 전에 거부합니다. 규모를 키우기 전에 메모리 사용량을 확인하세요. 개인 실행 명세·로그·어댑터를 저장하고, 보류한 테스트 분할에서 손실을 계산합니다. 모델 로딩은 오프라인으로 수행하며 원격 코드 실행이나 외부 보고 서비스를 활성화하지 않습니다.

`train generate`는 같은 로컬 베이스 모델 경로에 어댑터를 다시 읽습니다. `compose --adapter`도 이 경로를 사용하고 Ollama 경로와 같은 JSON·MIDI 검증을 적용합니다. 어댑터 출력이 스키마를 만족한다고 보장하지 않으며 잘못된 출력은 거부합니다. 한 모델에서 학습한 어댑터가 다른 모델에 적용되거나, 호환 변환 없이 Ollama에서 사용된다고 가정하지 마세요.

## 실행 경로 검사

```sh
deepchord train smoke-data --out /path/to/private/smoke/reviewed.jsonl
deepchord train prepare /path/to/private/smoke/reviewed.jsonl --out /path/to/private/smoke/data
deepchord train run --model /path/to/small/local-mlx-model --data /path/to/private/smoke/data --out /path/to/private/smoke/adapter --iters 3
```

검사용 생성기는 코드로 합성 화음 연습 예제를 만듭니다. 예제끼리 유사하므로 **실행 환경 검사에만** 사용하며, 일반화나 음악적 향상의 벤치마크가 아닙니다. 실제 평가 데이터에 섞지 마세요. 3회 반복은 유용한 음악 학습을 완료한 상태가 아닙니다.

개발 검사는 `mlx-community/Qwen2.5-0.5B-Instruct-4bit`의 `a5339a4131f135d0fdc6a5c8b5bbed2753bbe0f3` 리비전으로 수행했습니다. 모델과 어댑터 모두 배포하지 않습니다. Gemma LoRA 학습이나 호환성을 주장하지 않습니다.

자료: [MLX LoRA 문서](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md), [검사에 사용한 모델 카드](https://huggingface.co/mlx-community/Qwen2.5-0.5B-Instruct-4bit).

## 공개 기초 자산과 반복 세션

[공개 기초 자산 안내](foundation.ko.md)는 이론·코드 Q&A 학습 작업, 그룹 분리, 선택적 Transformers/PEFT 백엔드와 반복 세션을 설명합니다. 기존 작곡 JSON 레코드도 계속 지원합니다.
