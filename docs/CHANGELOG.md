# Changelog

## v0.8.2 — Energy color 버그 수정, CLI 이펙트 플래그 추가 (2026-03-09)

### 버그 수정
- **Energy color가 single 모드에서 미적용**: energy color 시스템이 `white_key_note_color`/`black_key_note_color`만 업데이트하여 기본 `single` 모드에서 색 변화가 없던 문제 수정
- **수정 방식**: energy color 활성화 시 자동으로 `key_type` 모드로 전환하여 흰건반/검은건반 색 구분 유지

### 새 기능
- **`--no-comet` CLI 플래그**: 혜성 이펙트 비활성화
- **`--no-energy-color` CLI 플래그**: 에너지 기반 색상 변환 비활성화

---

## v0.8.1 — 웹 UI 이펙트 토글 (2026-03-09)

### 새 기능
- **웹 UI 이펙트 토글**: comet, energy color, starflow 효과를 웹에서 개별 ON/OFF
- 설정 로직 확장으로 모든 이펙트를 웹에서 제어 가능

---

## v0.8.0 — 혜성 효과, 에너지 기반 색상 (2026-03-09)

### 새 기능
- **혜성(comet) 이펙트**: 노트에 혜성 꼬리 시각 효과 추가
- **에너지 기반 색상 시스템**: 연주 강도(energy)에 따라 노트 색상이 동적으로 변화
- **노트별 색상 캐싱**: 렌더링 성능 최적화

### 개선
- `effects.py` 대규모 리팩토링 (이펙트 시스템 구조 개선)

---

## v0.7.x — 이펙트 시스템 구축 및 반복 개선 (2026-03-09)

### v0.7.4: C음 효과 안정화
- C음 가이드라인 효과를 깜빡임 없는 **부드러운 단일 상승 도트**로 개선

### v0.7.3: 반딧불 → C음 가이드라인 효과로 교체
- 반딧불(firefly) 이펙트를 **C음 경계 가이드라인 상승 효과**로 전면 교체

### v0.7.2: 반딧불 크기 확대
- 반딧불을 더 크고 눈에 잘 띄게 수정

### v0.7.1: 반딧불 + 별흐름 리디자인
- 반딧불/별흐름 이펙트의 시각적 개선

### v0.7.0: 반딧불 상승 + 별흐름 효과 추가
- **반딧불 상승 파티클**: 건반 위로 반딧불이 올라가는 파티클 효과
- **ambient starflow**: 배경에 별이 흐르는 분위기 효과
- 웹 UI에 이펙트 토글 추가

---

## v0.6.0 — numpy 렌더링 최적화, key_type 컬러 모드 (2026-03-09)

### 새 기능
- **key_type 컬러 모드**: 흰건반/검은건반별 다른 색상 적용
- 웹 UI에 컬러 모드 선택 옵션 추가

### 개선
- **numpy 기반 노트 렌더링**: 렌더링 파이프라인 성능 최적화
- `colors.py`에 새 컬러 유틸리티 함수 추가

---

## v0.5.0 — 네온 시안 기본색, 풀하이트 그라데이션 (2026-03-08)

### 새 기능
- **기본 색상 변경**: 네온 시안 `(0, 255, 200)` 적용
- **풀하이트 흰색 그라데이션**: 노트 상단 흰색 → 하단 순수 색상 페이드
- **글리터 효과**: `--glitter` CLI 플래그 (기본 OFF)
- **웹 프리뷰**: `/preview` 엔드포인트로 미리보기 이미지 제공

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
