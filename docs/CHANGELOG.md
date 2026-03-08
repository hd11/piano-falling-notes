# Changelog

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
