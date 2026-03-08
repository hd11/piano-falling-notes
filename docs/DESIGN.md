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

## 색상 체계
- **pitch_range** (기본): MIDI 번호 기반 HSV 그라데이션 (저음=따뜻, 고음=차가운 색)
- rainbow_octave: 옥타브별 무지개
- part_based: 파트별 색상 구분

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

### Phase 3: 테스트/검증 - 완료
- [x] Golden.musicxml → Golden_v2.mp4 생성 성공 (720p, 30fps)
- [x] 시각적 품질 확인: 색상 다양성, 건반 활성화, 글로우 효과 확인
- [x] 렌더링 성능: ~30-90 it/s (720p@30fps), 5600 프레임 약 2분

### 사용법
```bash
# 가상환경 활성화
source .venv/bin/activate

# 기본 사용 (1080p, 60fps)
python -m piano_falling_notes input.musicxml -o output.mp4

# 빠른 미리보기 (720p, 30fps)
python -m piano_falling_notes input.musicxml -o preview.mp4 --width 1280 --height 720 --fps 30

# 색상 모드 변경
python -m piano_falling_notes input.musicxml --color-mode pitch_range

# 글로우 비활성화
python -m piano_falling_notes input.musicxml --no-glow
```
