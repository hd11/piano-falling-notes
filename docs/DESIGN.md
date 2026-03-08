# Piano Falling Notes Video Generator - 설계 문서

## 프로젝트 개요
MusicXML 피아노 악보를 입력받아, PianiCast/Synthesia 스타일의 노트가 떨어지는 영상(MP4)을 생성하는 Python 프로그램.

## 참고 자료
- [PianiCast (나무위키)](https://namu.wiki/w/PianiCast): 어두운 배경, 컬러풀한 떨어지는 막대 노트, 글로우 이펙트
- [midi2video (GitHub)](https://github.com/ablomer/midi2video): Python MIDI→영상 변환 참고
- [SeeMusic](https://www.seemusicapp.com): 상용 피아노 시각화 도구

## 시스템 아키텍처

```
┌──────────────────────────────────────────────────┐
│                 CLI / Config Layer                │
│            (argparse + YAML config)              │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│            MusicXML Parser Module                │
│       (music21 기반 파싱 + 정규화)               │
│  Input: .musicxml  →  Output: List[NoteEvent]    │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│            Note Timeline Model                   │
│   (시간축 변환, MIDI 번호 매핑, 타이 병합)       │
│  Input: List[NoteEvent]  →  Output: Timeline     │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│            Rendering Engine                      │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ Keyboard │ │Falling Notes │ │Visual Effects│ │
│  │ Renderer │ │  Renderer    │ │(Glow/Color)  │ │
│  └──────────┘ └──────────────┘ └──────────────┘ │
│       Pillow + numpy 기반 프레임별 렌더링        │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│            Video Export Pipeline                  │
│    (FFmpeg subprocess pipe → H.264 MP4)          │
└──────────────────────────────────────────────────┘
```

## 데이터 흐름
```
MusicXML → 파싱 → NoteEvent 리스트 → 타임라인 변환 →
프레임별 렌더링 (배경 + 노트 + 건반 + 이펙트) → FFmpeg pipe → MP4
```

## 핵심 데이터 모델

### NoteEvent (파서 출력)
| 필드 | 타입 | 설명 |
|------|------|------|
| midi_number | int | MIDI 노트 번호 (21=A0 ~ 108=C8) |
| start_ticks | int | divisions 기준 시작 위치 |
| duration_ticks | int | divisions 기준 지속 시간 |
| velocity | float | 0.0~1.0 |
| part_index | int | 파트 번호 |
| tie_continue | bool | 타이 연결 여부 |

### RenderNote (렌더링 입력)
| 필드 | 타입 | 설명 |
|------|------|------|
| midi_number | int | MIDI 노트 번호 |
| start_seconds | float | 절대 시간 (초) |
| duration_seconds | float | 지속 시간 (초) |
| velocity | float | 세기 |
| part_index | int | 파트 번호 |

## 화면 레이아웃 (1920x1080)
```
┌────────────────────── 1920px ──────────────────────┐
│ y=0                                                │
│   폴링 노트 영역 (~85%)                            │
│   노트가 위→아래로 떨어짐                           │
│   lookahead: 3초 미래까지 표시                      │
│ y=918 (keyboard_top)                               │
│ ┌────────────────────────────────────────────────┐ │
│ │ 피아노 건반 영역 (~15%)                         │ │
│ │ 88건반 (A0~C8), 활성키 색상 변환 + 글로우       │ │
│ └────────────────────────────────────────────────┘ │
│ y=1080                                             │
└────────────────────────────────────────────────────┘
```

## 건반 렌더링 상세
- 88건반 (52 흰건반 + 36 검은건반) 정확한 비율 배치
- 비활성 상태: 흰건반(#F0F0F0), 검은건반(#1E1E1E)
- **활성 상태 (노트 타격 시):** 해당 노트 색상으로 건반 색 변환 + 글로우 이펙트
- 기본 건반 이미지 캐싱, 활성 키만 오버레이

## 색상 체계 및 테마

### 색상 모드
- **rainbow_octave** (기본): 크로매틱 12음 팔레트 - 반음 단위 고유 색상
- **pitch_range**: MIDI 번호 기반 HSV 그라데이션 (저음=따뜻, 고음=차가운 색)

### 테마 프리셋 (자동 선택 또는 수동 지정)
| 테마 | 배경색 | 팔레트 특성 | 자동 선택 조건 |
|------|--------|-------------|---------------|
| **auto** | 음원 분석 | 자동 결정 | 기본값 |
| classic | `(15,15,20)` 다크 그레이 | 비비드 레인보우 | - |
| midnight | `(8,8,24)` 딥 네이비 | 블루/퍼플 계열 | 단조(minor) |
| sunset | `(25,12,15)` 다크 웜 | 레드/오렌지/골드 | 장조(major) |
| ocean | `(6,16,24)` 다크 틸 | 시안/블루/그린 | 느린 곡 (<72 BPM) |
| neon | `(3,3,8)` 퓨어 블랙 | 비비드 네온 | 빠른 곡 (>140 BPM) |
| pastel | `(18,16,22)` 소프트 다크 | 파스텔 톤 | - |

### 자동 테마 선택 로직
1. 악보에서 조성(key signature) 자동 분석 (music21 `analyze('key')`)
2. 템포(BPM) 분석
3. 규칙: 빠른 곡→neon, 느린 곡→ocean, 단조→midnight, 장조→sunset

### 사용자 커스터마이징
- CLI: `--theme`, `--background #hex` 옵션
- 웹 UI: 테마 드롭다운 + 배경색 컬러 피커

## 오디오 파이프라인
```
MusicXML → MIDI (music21) → WAV (fluidsynth + soundfont) → AAC mux (FFmpeg)
```
- 사운드폰트: TimGM6mb.sf2 (General MIDI, 5.8MB)
- 오디오 오프셋: lead_in_seconds만큼 지연 (영상과 동기화)

## 웹 UI
- Flask 기반 단일 페이지 앱
- 드래그앤드롭 파일 업로드 (.musicxml, .mxl)
- 실시간 변환 진행률 표시 (파싱 → 오디오 → 렌더링 → 인코딩)
- 옵션: 테마, 배경색, 해상도, FPS, 글로우, 오디오
- 백그라운드 스레드 변환 + 1시간 후 자동 정리

## 기술 스택
| 컴포넌트 | 라이브러리 | 근거 |
|----------|-----------|------|
| MusicXML 파싱 | music21 | 타이/반복/전조 자동 처리, 테스트 파일이 music21으로 생성 |
| 2D 렌더링 | Pillow + numpy | 충분한 성능, 설치 쉬움, 알파블렌딩 |
| 비디오 인코딩 | FFmpeg (pipe) | stdin pipe로 메모리 효율적, 이미 설치됨 |
| 진행률 표시 | tqdm | |
| 설정 관리 | dataclasses + YAML | |
| CLI | argparse | |

## 성능 예측
| 곡 | 예상 길이 | 60fps 프레임 수 | 예상 렌더링 시간 |
|----|----------|----------------|-----------------|
| Golden (123BPM, 94마디) | ~3분 | ~10,800 | 3~8분 |
| IRIS OUT (136BPM, 81마디) | ~2.4분 | ~8,640 | 2~5분 |
| 꿈의 버스 (172BPM, 107마디) | ~2.5분 | ~9,000 | 3~6분 |

## 최적화 전략
1. 건반 기본 이미지 캐싱 (활성 키만 오버레이)
2. 이진 탐색 시간 인덱스 (화면 내 노트만 조회)
3. FFmpeg stdin pipe (디스크 I/O 없음)
4. 프레임당 메모리: ~6MB (1920x1080x3)

## 테스트 데이터
- `test-scores/Golden.musicxml` (123 BPM, 4/4, 94마디)
- `test-scores/IRIS OUT.musicxml` (136 BPM, 4/4, 81마디)
- `test-scores/꿈의 버스.musicxml` (172 BPM, 4/4, 107마디)
- 공통: divisions=10080, 단일 파트(Melody), 옥타브 3~6

---

## 진행 상황

### Phase 1: 분석/설계 - 완료
- [x] MusicXML 테스트 파일 탐색 및 복사
- [x] PianiCast 스타일 조사
- [x] 기존 도구 조사 (midi2video, SeeMusic)
- [x] MusicXML 구조 분석 (divisions, tempo, tie, dynamics)
- [x] 시스템 아키텍처 설계
- [x] 설계 문서 작성

### Phase 2: 구현 - 완료
- [x] 프로젝트 구조 생성 (pyproject.toml, 디렉토리)
- [x] MusicXML 파서 모듈 (music21 기반, 342 노트 파싱 성공)
- [x] Note Timeline 모듈 (타이 병합: 342→318 노트)
- [x] 건반 렌더러 (88건반, 활성 키 색상 변환)
- [x] 폴링 노트 렌더러 (둥근 모서리 직사각형, 키 위치 정확 매핑)
- [x] 비주얼 이펙트 (글로우 효과, 건반 활성 색상 변환)
- [x] 비디오 출력 파이프라인 (FFmpeg pipe, H.264)
- [x] CLI 인터페이스 (argparse)
- [x] 설정 시스템 (YAML + CLI 오버라이드)
- [x] 색상 개선: 크로매틱 12음 팔레트 (PianiCast 스타일)
- [x] 글로우 효과 강화 (가우시안 블러 배치 처리)

### Phase 3: 오디오 + 레퍼런스 악보 - 완료
- [x] 양손 레퍼런스 악보 테스트 (Golden_ref.mxl: 590+911=1501노트, 2파트)
- [x] 오디오 파이프라인 구현 (MusicXML→MIDI→WAV→AAC mux)
- [x] fluidsynth + TimGM6mb.sf2 사운드폰트 연동
- [x] 88건반 정확도 검증 (52 흰건반 + 36 검은건반)
- [x] 글로우 이펙트 최적화 (전체 이미지 RGBA → numpy 로컬 스트립 40px)

### Phase 4: 웹 UI - 완료
- [x] Flask 웹 서버 구현 (드래그앤드롭 업로드, 백그라운드 변환)
- [x] 옵션 패널 (색상 모드, 해상도, FPS, 글로우, 오디오)
- [x] 실시간 진행률 표시 + MP4 다운로드
- [x] 다크 테마 UI (한국어/영어 병행)

### Phase 5: 테마 시스템 - 완료
- [x] 6개 테마 프리셋 (classic, midnight, sunset, ocean, neon, pastel)
- [x] 음원 자동 분석 (조성 + 템포) → 테마 자동 선택
- [x] 웹 UI 테마 드롭다운 + 배경색 커스텀 컬러 피커
- [x] CLI --theme, --background 옵션 추가
- [x] Golden_ref.mxl 테스트: G major, 183 BPM → Neon 테마 자동 선택

### Phase 6: 동기화 수정 및 품질 개선 - 완료
- [x] [CRITICAL] 템포 beat-unit 변환 버그 수정 (♩.=122 → 183 QN BPM)
- [x] 템포 맵 기반 시간 변환 (다중 MetronomeMark 지원)
- [x] 웹 UI 테마 미적용 버그 수정 (run_conversion 내 팔레트 적용)
- [x] 조성 감지 센티널 버그 수정 (key_found 불리언)
- [x] 검은건반 위치 수정 (경계 중앙 센터링)
- [x] 연타음 3px 수직 갭 추가
- [x] MuseScore vs fluidsynth 음원 차이 분석

### 사용법
```bash
# 가상환경 활성화
source .venv/bin/activate

# 기본 사용 (1080p, 60fps, 자동 테마)
python -m piano_falling_notes input.musicxml -o output.mp4

# 테마 지정
python -m piano_falling_notes input.musicxml --theme neon
python -m piano_falling_notes input.musicxml --theme midnight

# 배경색 커스텀
python -m piano_falling_notes input.musicxml --theme classic --background "#1A0A2E"

# 빠른 미리보기 (720p, 30fps)
python -m piano_falling_notes input.musicxml -o preview.mp4 --width 1280 --height 720 --fps 30

# 오디오 없이 빠른 렌더링
python -m piano_falling_notes input.musicxml --no-audio

# 웹 서버 시작
python -m piano_falling_notes --web --port 5000
```
