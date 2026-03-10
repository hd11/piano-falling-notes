# Changelog

## v1.1.1 — 코드 리뷰 수정 + 문서화 (2026-03-10)

### 버그 수정
- **CLI 플래그 명시적 처리 누락**: `--key-depression`, `--comet-trail-glow` 가 `__main__.py` 의 `# Handle flags` 섹션에 없어 Config 기본값 변경 시 깨질 수 있었던 문제 수정
- **건반 눌림 시각적 빈 공간**: key_depression 활성 시 키 상단에 배경색이 노출되던 문제 → 눌린 키 색상의 어두운 그림자(×0.4/0.5)로 채워 자연스러운 눌림 표현

### 코드 품질
- **`_comet_trail_glow_enabled` 캡슐화**: 외부에서 주입하던 방식을 `VisualEffects.__init__`에서 초기화하고, `renderer.py`에서 `getattr` 대신 `config.comet_trail_glow` 직접 접근으로 변경
- **`_trail_glow_points` 무제한 성장 방지**: 긴 곡에서 리스트가 무한 증가하던 문제 → 500개 상한 추가
- **미사용 변수 제거**: `apply_c_note_rise` 내 `_CORE_COLOR` 미사용 변수 삭제
- **믹스인 클래스 docstring 추가**: `BurstEffectsMixin`, `ParticleEffectsMixin`, `AmbientEffectsMixin` 상태 초기화 의존성 명시

### 웹 UI
- **초기화 버튼 누락 항목 수정**: "혜성 잔광" 토글이 초기화 버튼에서 리셋되지 않던 문제 수정

### 문서화
- **AGENTS.md 계층 문서 추가**: 프로젝트 전체 10개 디렉토리에 AI 에이전트용 계층형 문서 생성 (root → package → submodules)

---

## v1.1.0 — 이펙트 모듈 분리 + 신규 효과 (2026-03-10)

### 구조 개선
- **effects.py 패키지 분리**: 841줄 단일 파일을 `effects/` 패키지로 분리
  - `__init__.py` — VisualEffects 파사드 (믹스인 조합)
  - `burst.py` — BurstEffectsMixin (`apply_neon_burst`)
  - `particles.py` — ParticleEffectsMixin (`apply_ascending_bubbles`, `apply_c_note_rise`, `apply_comet_trail_glow`)
  - `ambient.py` — AmbientEffectsMixin (`apply_note_glow`, `apply_wave_ripple`, `apply_pedal_glow`, `apply_starflow`)
- 기존 공개 API (`from ..rendering.effects import VisualEffects`) 변경 없음

### 새 기능
- **건반 눌림 효과** (`--key-depression`): 활성 키가 시각적으로 눌리는 효과 (흰건반 3px, 검은건반 2px 하강)
- **혜성 잔광** (`--comet-trail-glow`): 혜성이 지나간 자리에 부드러운 빛의 잔상이 ~2초간 남는 효과 (가우시안 글로우, 60프레임 수명)

### CLI / 웹 UI
- CLI: `--key-depression`, `--comet-trail-glow` 플래그 추가 (기본 OFF)
- 웹 UI: "건반 눌림 효과", "혜성 잔광" 토글 스위치 추가
- Config: `key_depression`, `comet_trail_glow` 필드 추가

---

## v1.0.0 — 안정 릴리스 (2026-03-10)

### 버그 수정
- **VideoWriter `__exit__` FFmpeg 에러 무시 문제**: context manager 종료 시 FFmpeg 비정상 종료(returncode ≠ 0)를 감지하지 못하던 문제 수정 — 정상 종료 시에만 returncode 검사, 예외 발생 중일 때는 원래 예외 우선
- **ColorScheme 기본 모드 불일치**: `ColorScheme` 기본값이 `"pitch_range"`로 되어 있어 `Config` 기본값(`"single"`)과 불일치하던 문제 수정 → `"single"`로 통일

### 안정화
- 심층 코드/로직 분석 통과 — 렌더 파이프라인, 이펙트 시스템, 에너지 색상, 타임라인 처리 전반 검증 완료
- pyproject.toml 버전 `1.0.0` 반영

---

## v0.10.0 — 렌더 파이프라인 리팩토링 (2026-03-10)

### 리팩토링
- **공유 렌더 모듈** (`core/renderer.py`): CLI·웹 변환·웹 프리뷰 3곳에 복사되어 있던 렌더 루프를 `render_frame()`, `compute_energy_profile()`, `make_background_frame()` 공유 함수로 통합
- **에너지 색상 계산 통합**: 3곳에 중복되던 에너지 프로파일 계산 + 팔레트 보간을 `compute_energy_profile()` + `apply_energy_color()`로 추출
- **코드 361줄 삭제**: 중복 렌더 코드, 죽은 코드 제거로 유지보수성 대폭 향상

### 버그 수정
- **CLI glow 무조건 렌더**: `glow_enabled` 플래그 체크 없이 항상 글로우가 렌더되던 문제 수정
- **웹 프리뷰 energy color 모드 누락**: 에너지 색상 적용 시 `color_scheme.mode = "key_type"` 미설정 문제 수정
- **웹 변환 ascending_bubbles 누락**: `run_conversion()`에서 상승 파티클 이펙트가 빠져있던 문제 수정
- **CLI에 `neon_burst` 누락**: 키 스트라이크 스플래시가 CLI에서 빠져있던 문제 수정 (v0.9.1)
- **웹 변환에 `energy_color` 누락**: 웹 변환 경로에서 미적용되던 문제 수정 (v0.9.1)
- **외부 오디오 파일 존재 확인**: `Path.exists()` 검사 추가 (v0.9.1)
- **빈 soundfont 경로 정규화**: 빈 문자열 → `None` 변환 (v0.9.1)

### 클린업
- **죽은 코드 제거**: `apply_dj_eq` 이펙트 (미사용), `note_style` 설정 필드/CLI 인수 삭제
- **import 정리**: `effects.py` 내 4곳 인라인 `import math` → 모듈 레벨 통합

---

## v0.9.0 — MIDI 지원, 외부 오디오, 세로 모드, 배경 이미지 (2026-03-10)

### 새 기능: 입력 포맷 확장
- **MIDI 파일 지원**: `.mid`/`.midi` 파일을 MusicXML과 동등하게 처리 (CLI, 웹 UI 모두)
- **외부 오디오 파일** (`--audio-file`): 사용자 제공 오디오 사용 (fluidsynth 합성 대신)
- **커스텀 사운드폰트** (`--soundfont`): .sf2/.sf3 파일 지정하여 오디오 생성

### 새 기능: 시각 개선
- **세로 모드** (`--vertical`): 세로 영상 생성 (1080×1920 / 720×1280)
- **배경 이미지** (`--background-image`): 커스텀 배경 이미지 오버레이
- **velocity 기반 밝기** (`--velocity-effect`): 노트 밝기가 키 velocity에 비례
- **페달 시각화** (`--pedal`): 서스테인 페달 활성화 시 따뜻한 호박색 글로우

### 새 기능: 오디오 처리
- **리버브 이펙트** (`--reverb`): FluidSynth 리버브 적용 (기본 OFF)

### 새 기능: 웹 UI 확장
- **MIDI 파일 업로드**: 파일 업로드가 MIDI 포맷 지원
- **외부 오디오/배경 업로드**: 오디오 파일 및 이미지 파일 입력 필드 추가
- **타임라인 스크러버**: 재생 위치 선택용 프리뷰 시간 슬라이더 (0~100%)
- **새 토글**: 세로 모드, velocity 이펙트, 페달 시각화, 리버브
- **배치 처리**: 웹 UI에서 다중 파일 변환 (진행률 표시)

---

## v0.8.2 — Energy color 버그 수정, CLI 이펙트 플래그 추가 (2026-03-10)

### 버그 수정
- **Energy color가 single 모드에서 미적용**: energy color 시스템이 `white_key_note_color`/`black_key_note_color`만 업데이트하여 기본 `single` 모드에서 색 변화가 없던 문제 수정
- **수정 방식**: energy color 활성화 시 자동으로 `key_type` 모드로 전환하여 흰건반/검은건반 색 구분 유지

### 새 기능
- **`--no-comet` CLI 플래그**: 혜성 이펙트 비활성화
- **`--no-energy-color` CLI 플래그**: 에너지 기반 색상 변환 비활성화

---

## v0.8.1 — 웹 UI 이펙트 토글 추가 (2026-03-10)

### 새 기능
- **혜성 이펙트 토글** (`comet_effect`): 웹 UI에서 혜성 효과 ON/OFF (기본 ON)
- **에너지 색 전환 토글** (`energy_color`): 음악 강도 기반 동적 색상 변환 ON/OFF (기본 ON)
- **별빛흐름 토글** (`starflow`): 배경 별빛 파티클 효과 ON/OFF (기본 ON)
- **미리보기에 에너지 색상 반영**: `/preview` 엔드포인트에서도 에너지 기반 색상 계산 적용

### 구현 상세
- `Config` 데이터클래스에 `comet_effect`, `energy_color`, `starflow` 필드 추가
- `index.html`에 3개 토글 행 추가, JS FormData로 `/convert`·`/preview` 양쪽 전송
- `app.py`의 `/convert`, `/preview` 라우트에서 새 필드 파싱 및 조건부 이펙트 렌더링
- `generator.py`에서 `config.energy_color`, `config.comet_effect`, `config.starflow` 플래그 확인

---

## v0.8.0 — 혜성 이펙트, 에너지 기반 색상, 노트별 색상 캐싱 (2026-03-09)

### 새 기능: 혜성(Comet) 이펙트
- **별 모양 헤드**: 4-spike 회전 가우시안 (0/45/90/135°) + 밝은 원형 코어
- **불규칙 경로**: sin + cos + clamped-tan 3중 오실레이터 (가이드라인을 벗어나는 큰 진폭)
- **별가루 트레일**: 혜성 꼬리에서 작은 붉은 파티클이 떨어짐 (14 trail points, 35% 스폰율)
- **색상 순환**: 3~4개 혜성마다 랜덤 색상 변경 (6가지 팔레트: orange/pink/cyan/purple/mint/yellow)
- **트리거**: 현재 연주 중인 건반에서 1~3초 간격으로 발생

### 새 기능: 에너지 기반 동적 노트 색상
- **에너지 프로파일 사전 계산**: 4초 슬라이딩 윈도우, `density(notes/sec) × 0.5 + avg_velocity × 0.5`
- **5-point 스무딩** 후 곡 자체의 min/max 기준 상대 정규화 (항상 전체 팔레트 활용)
- **3단계 팔레트 분배**: 파랑 60% (`_e < 0.60`) / 초록 30% (`0.60~0.90`) / 주황-빨강 10% (`> 0.90`)
- **팔레트 색상**: PAL_LOW `(80,130,255)/(160,80,255)`, PAL_MID `(0,255,128)/(0,140,255)`, PAL_HIGH `(255,160,0)/(255,60,40)`

### 새 기능: 노트별 색상 캐싱
- `FallingNotesRenderer._note_color_cache = {(midi, start_seconds): rgb}`
- 각 노트는 최초 렌더 시 색상이 1회 할당되어 이후 프레임에서 재사용
- 에너지 변화 시 새로 떨어지는 노트부터 새 색상이 적용되어 **자연스러운 색상 전환 웨이브** 생성

### 개선
- **네온 버스트 강화**: splash 높이 260→480px, 파티클 속도 50~130→90~220px/s
- **렌더 순서 수정**: starflow → c_note_rise (혜성이 별 위에 표시)
- **c_note_rise 항상 호출**: `if newly_active:` 게이트 제거 → 매 프레임 렌더링 (깜빡임 해결)
- `effects.py` 대규모 리팩토링 (이펙트 시스템 구조 개선)

### 버그 수정
- **C노트 이펙트 깜빡임**: `if newly_active:` 게이트가 새 노트 없는 프레임에서 렌더링을 건너뜀 → 항상 호출로 수정
- **별이 혜성 위에 그려짐**: starflow가 c_note_rise 이후 렌더링되어 혜성을 덮음 → 순서 교체
- **페이드아웃 깜빡임**: 페이드아웃 윈도우(20px)가 rise_speed(16px/frame) 대비 너무 짧아 1프레임에 급격한 알파 변화 → 페이드아웃 제거
- **전체 노트 주황색 문제**: 절대 에너지 정규화(`/8.0 notes/sec`)가 대부분 곡에서 높은 에너지로 매핑 → 곡별 상대 정규화로 수정
- **주황 편향 문제**: 팔레트 분배 0.35/0.65가 너무 공격적 → 0.60/0.90 (60/30/10 비율)로 조정

---

## v0.7.x — 이펙트 시스템 구축 및 반복 개선 (2026-03-09)

### v0.7.4: C음 효과 안정화
- C음 가이드라인 효과를 깜빡임 없는 **부드러운 단일 상승 도트**로 개선
- 이중 레이어 가우시안(inner core + outer halo) 제거 → 단일 가우시안으로 교체

### v0.7.3: 반딧불 → C음 가이드라인 효과로 교체
- 반딧불(firefly) 이펙트를 **C음 경계 가이드라인 상승 효과**로 전면 교체
- 가이드라인 위를 따라 올라가는 빛점 효과

### v0.7.2: 반딧불 크기 확대
- 반딧불을 더 크고 눈에 잘 띄게 수정

### v0.7.1: 반딧불 + 별흐름 리디자인
- 반딧불/별흐름 이펙트의 시각적 개선

### v0.7.0: 반딧불 상승 + 별흐름 효과 추가
- **반딧불 상승 파티클**: 건반 위로 반딧불이 올라가는 파티클 효과
- **ambient starflow**: 300개 쿨톤 별 파티클이 배경에서 흐르는 효과
- 웹 UI에 이펙트 토글 추가

---

## v0.6.0 — numpy 렌더링 최적화, key_type 컬러 모드 (2026-03-09)

### 새 기능
- **key_type 컬러 모드**: 흰건반 노트 / 검은건반 노트에 각각 다른 색상 적용
  - 흰건반 기본 `(0, 255, 128)` 초록 네온, 검은건반 기본 `(0, 128, 255)` 파랑 네온
  - 웹 UI에 흰건반/검은건반 개별 컬러 피커 추가
- 웹 UI에 컬러 모드 선택 드롭다운 추가 (단색/여러색/네온/파트별/건반별)

### 개선
- **numpy 기반 노트 렌더링**: Pillow pixel-by-pixel → numpy 배열 연산으로 성능 대폭 개선
  - 노트 영역 crop → numpy float32 → 마스크 생성 → 그라데이션 적용 → paste back
- `colors.py`에 `ColorScheme.white_key_note_color`, `black_key_note_color` mutable 속성 추가

---

## v0.5.0 — 네온 시안 기본색, 풀하이트 그라데이션, 글리터, 웹 프리뷰 (2026-03-08)

### 새 기능
- **기본 색상 변경**: 네온 시안 `(0, 255, 200)` 적용 (기존 레인보우 팔레트 → 단색)
- **풀하이트 흰색 그라데이션**: 노트 바 상단에서 흰색(70% mix) → 하단으로 갈수록 순수 색상으로 페이드
  - numpy 배열 연산으로 구현, `white_mix = 0.7 * (1.0 - t)` 세로 그라데이션
- **글리터 효과**: 노트 바 위에 반짝이는 파티클 효과 (`--glitter` CLI 플래그, 기본 OFF)
  - 벡터화 해시 함수로 결정론적 스파클 위치 생성, `sin(current_time * 6.0 + phase)` 기반 트윈클
- **웹 프리뷰**: `/preview` 엔드포인트 추가 — 곡의 ~10% 지점에서 단일 프레임 PNG 생성
  - 설정 변경 후 영상 변환 없이 빠르게 결과물 스타일 확인 가능

---

## v0.4.1 — 네온 버스트 가시성, 옥타브 가이드라인, 노트 분리 조정 (2026-03-08)

### 버그 수정
- **네온 버스트 가시성 개선**: 가우시안 빛 폭발이 배경에 묻히는 문제 수정
- **가이드라인 옥타브 단위로 변경**: 모든 흰건반 경계 → C음(도)과 F음(파) 위치만 표시
- **노트 분리 비율 조정**: `note_duration_ratio` 0.95 → 0.92 (연타음 간격 약간 확대)

---

## v0.4.0 — 시각 이펙트 및 색상 커스터마이징 (2026-03-08)

### 새 기능
- **노트 색상 모드 시스템**: 기본 단색(cyan) + 사용자 선택 가능
  - `single` (기본): 모든 노트 동일 색상 (사용자 지정 가능)
  - `rainbow`: 크로매틱 12음 팔레트 (기존 rainbow_octave)
  - `neon`: 비비드 네온 컬러
  - `part`: 파트별 색상 (왼손/오른손 구분)
- **네온 버스트 이펙트**: 건반 타격 시 가우시안 방사형 빛 폭발 (PianiCast 스타일)
  - velocity 비례 강도, 건반 2배 폭 확산, 가법 블렌딩
- **DJ EQ Max 시각화**: 이퀄라이저 스타일 수직 바
  - `--note-style djeq` 또는 웹 UI 드롭다운으로 활성화
  - velocity 비례 높이, 수직 밝기 그라데이션, 25/50/75% 그리드 라인
- **배경 가이드라인**: 피아니캐스트 스타일 흰건반 경계 수직선
  - `--no-guide-lines`로 비활성화 가능

### 개선
- **연타음 시각적 분리**: 3px 고정 갭 → 95% 비율 렌더링 (음길이 비례 갭)
  - `note_duration_ratio` 설정으로 조절 가능 (기본 0.95)
- **CLI 새 옵션**: `--color-mode`, `--note-color`, `--note-style`, `--no-neon-burst`, `--no-guide-lines`
- **웹 UI 확장**: 노트 색상 드롭다운, 시각화 스타일, 네온 버스트/가이드라인 토글

---

## v0.3.1 — 코드 품질 및 보안 개선 (2026-03-08)

### 버그 수정
- **[CRITICAL] FFmpeg 파이프 데드락**: `stderr=subprocess.PIPE` → `subprocess.DEVNULL`
  - 원인: FFmpeg stderr 버퍼 가득 참 → FFmpeg 블로킹 → Python `process.wait()` 블로킹 → 교착
  - 증상: 렌더링 100% 완료 후 무한 대기 (파일 크기 증가 중단)
- **VideoWriter `__exit__` 예외 누락**: 예외 발생 시에도 `stdin.close()` 보장 (try/finally)
- **템포 감지 센티널**: `120.0` float 동등비교 → `None` 센티널 사용
- **`score.flatten()` 3회 반복 호출**: 1회 캐싱으로 파싱 성능 개선
- **노트 수직 갭**: 프레임 경계에서 클리핑된 노트에 불필요한 갭 적용 방지

### 보안 개선
- **스레드 풀 제한**: 무제한 `threading.Thread` → `ThreadPoolExecutor(max_workers=3)`
- **Job ID 검증**: UUID 형식 정규식 검증 추가 (경로 탐색 차단)
- **에러 메시지 정제**: 내부 경로 노출 방지 (파일 경로 포함 시 일반 메시지로 대체)
- **Flask SECRET_KEY**: 환경변수 또는 랜덤 토큰 자동 생성
- **보안 헤더**: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection` 추가
- **기본 호스트**: `0.0.0.0` → `127.0.0.1` (로컬 전용 바인딩)
- **`/status` 레이스 컨디션**: 락 내부에서 값 스냅샷 후 락 외부에서 응답 구성
- **중복 import 제거**: `run_conversion` 내 `sys.path` 조작 및 중복 `build_timeline` import 삭제

---

## v0.3.0 — 동기화 수정 및 품질 개선 (2026-03-08)

### 핵심 수정
- **[CRITICAL] 템포 beat-unit 변환 버그**: 점4분음표 템포(♩.=122)에서 실효 BPM 미변환
  - 원인: `el.number`(122)만 저장, `el.referent.quarterLength`(1.5) 미반영
  - 결과: 영상이 오디오보다 ~50% 느림 (277.4s vs 190.8s), 86.6초 드리프트
  - 수정: `effective_bpm = el.number * el.referent.quarterLength` (122*1.5=183 QN BPM)
- **노트/소리 동기화 수정**: 단일 BPM 대신 템포 맵(tempo map) 기반 시간 변환
  - `musicxml_parser.py`: 모든 MetronomeMark를 추출하여 tempo_map 생성
  - `builder.py`: `_ticks_to_seconds()` 함수가 tempo_map 세그먼트 적분 사용
- **웹 UI 테마 미적용 버그**: `run_conversion()`에서 테마 해석/팔레트 적용 누락 수정
- **조성 감지 센티널 버그**: `key_signature == "C major"` 비교 대신 `key_found` 불리언 사용

### UI/렌더링 수정
- **검은건반 위치**: 흰건반 65% 오프셋 → 흰건반 경계 중앙 센터링
- **연타음 시각적 분리**: 연속 동일음 간 3px 수직 갭 추가
- **업로드 제한**: 웹 UI MAX_CONTENT_LENGTH 50MB 설정

### 분석: MuseScore vs 생성 음원 차이
- **사운드폰트**: MuseScore_General.sf3 (141MB) vs TimGM6mb.sf2 (5.8MB) → 음색 차이
- **다이나믹스**: MuseScore는 크레센도/디크레센도/pp/ff 세밀 처리, fluidsynth는 velocity만
- **아티큘레이션**: 스타카토/레가토/페달 처리 정교도 차이
- **이펙트**: MuseScore 리버브/코러스 내장 vs fluidsynth 드라이 출력
- **해결 방향**: FluidR3_GM.sf2 또는 Salamander Grand Piano sf2로 교체 시 개선 가능

---

## v0.2.0 — 테마 시스템 (2026-03-08)

### 추가
- **자동 테마 선택**: 악보의 조성(key)과 템포(BPM) 분석으로 테마 자동 결정
  - 장조(major) → Sunset, 단조(minor) → Midnight
  - 빠른 곡(>140 BPM) → Neon, 느린 곡(<72 BPM) → Ocean
- **6개 테마 프리셋**: classic, midnight, sunset, ocean, neon, pastel
  - 각 테마별 고유 배경색 + 12음 컬러 팔레트
- **배경색 커스터마이징**: CLI `--background #hex`, 웹 UI 컬러 피커
- **테마 선택**: CLI `--theme`, 웹 UI 드롭다운
- **조성 분석**: music21 `analyze('key')` 활용한 자동 조성 감지

### 변경
- 웹 UI에 테마 드롭다운 + 배경색 커스텀 토글 추가
- `ColorScheme`이 커스텀 팔레트 수용하도록 확장

---

## v0.1.0 — 최초 릴리스 (2026-03-08)

### 기능
- **MusicXML 파싱**: music21 기반, .musicxml/.mxl 지원, 양손(2파트) 처리
- **88건반 피아노 렌더링**: 52 흰건반 + 36 검은건반, 활성 키 색상 변환
- **폴링 노트 영상 생성**: 1080p/720p, 60/30fps, H.264 인코딩
- **크로매틱 12음 팔레트**: PianiCast 스타일 비비드 색상
- **글로우 이펙트**: numpy 기반 로컬 스트립 처리 (40px, 고속)
- **오디오 생성**: MusicXML → MIDI (music21) → WAV (fluidsynth + TimGM6mb.sf2)
- **영상+오디오 합성**: FFmpeg AAC mux, lead-in 동기화
- **웹 UI**: Flask 기반, 드래그앤드롭 업로드, 실시간 진행률, MP4 다운로드
- **CLI**: argparse, YAML 설정 오버라이드
- **타이 병합**: 연결된 음표 자동 합산
- **이진 탐색 시간 인덱스**: O(log N + K) 가시 노트 조회
