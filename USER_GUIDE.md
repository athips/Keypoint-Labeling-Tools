# 📖 Dual Keypoint Labeler - User Guide
# 듀얼 키포인트 라벨러 - 사용자 가이드

> A comprehensive guide for using the Dual Keypoint Labeler application  
> 듀얼 키포인트 라벨러 애플리케이션 사용을 위한 종합 가이드

---

## 📑 Table of Contents / 목차

### English
- [Quick Start](#-quick-start)
- [Interface Overview](#-interface-overview)
- [Basic Operations](#-basic-operations)
- [Keyboard Shortcuts](#-keyboard-shortcuts)
- [Advanced Features](#-advanced-features)
- [Export & Import](#-export--import)
- [Tips & Best Practices](#-tips--best-practices)
- [Troubleshooting](#-troubleshooting)

### 한국어
- [빠른 시작](#-빠른-시작)
- [인터페이스 개요](#-인터페이스-개요)
- [기본 작업](#-기본-작업)
- [키보드 단축키](#-키보드-단축키)
- [고급 기능](#-고급-기능)
- [내보내기 및 가져오기](#-내보내기-및-가져오기)
- [팁 및 모범 사례](#-팁-및-모범-사례)
- [문제 해결](#-문제-해결)

---

# 🇺🇸 English Guide

## 🚀 Quick Start

### Step 1: Launch the Application

**Windows:**
```bash
# Double-click the batch file
run_dual_labeler.bat

# Or run from command line
python labeling/dual_keypoint_labeler.py
```

**Mac/Linux:**
```bash
python labeling/dual_keypoint_labeler.py
```

### Step 2: Load Your Images

1. Click **"Select Left Folder"** → Choose your first image folder (e.g., FO - Front-On)
2. Click **"Select Right Folder"** → Choose your second image folder (e.g., DL - Diagonal)
3. Images will automatically load and display

### Step 3: Start Annotating

1. **Select Edit Mode**: Press `M` (Move), `A` (Add), or `D` (Delete)
2. **Click on image** to add/move keypoints
3. **Navigate** using arrow keys (`↑` `↓` for active side, `←` `→` for both sides)
4. **Switch sides** with `Tab` key

> 💡 **Tip**: Hover over buttons to see tooltips with keyboard shortcuts!

---

## 🖥️ Interface Overview

### Main Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Header Bar]  Select Folders | Load Annotations | Export   │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│ Sidebar  │              Left Canvas (FO)                    │
│          │                                                   │
│ • Active │                                                   │
│   Side   │                                                   │
│ • Edit   ├──────────────────────────────────────────────────┤
│   Mode   │              Right Canvas (DL)                   │
│ • Format │                                                   │
│ • Nav    │                                                   │
│ • List   │                                                   │
│          │                                                   │
├──────────┴──────────────────────────────────────────────────┤
│  [Status Bar]  Mode | Keypoint | Zoom | Unsaved Changes     │
└─────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Description |
|-----------|-------------|
| **Header Bar** | Folder selection, annotation loading, export options |
| **Sidebar** | Controls for active side, edit mode, navigation, keypoint list |
| **Left Canvas** | First image set (e.g., Front-On view) |
| **Right Canvas** | Second image set (e.g., Diagonal view) |
| **Status Bar** | Real-time information (mode, keypoint, zoom, status) |

---

## ⚙️ Basic Operations

### Selecting Active Side

**Method 1:** Click radio buttons in "ACTIVE SIDE" section  
**Method 2:** Press `Tab` key to toggle

> The active side is highlighted with a colored border

### Loading Images

| Action | Steps |
|--------|-------|
| **Load Left Images** | Click "Select Left Folder" → Choose folder |
| **Load Right Images** | Click "Select Right Folder" → Choose folder |
| **Load Annotations** | Click "Load Left/Right Annotations" → Select JSON file |

**Supported Formats:**
- Images: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`
- Annotations: Standard JSON or COCO format

### Navigation

| Shortcut | Action |
|----------|--------|
| `↑` | Previous image (active side only) |
| `↓` | Next image (active side only) |
| `←` | Previous image (both sides) |
| `→` | Next image (both sides) |
| `◄ Previous` | Previous image button |
| `Next ►` | Next image button |
| `◄◄ First` | Jump to first image |
| `Last ►►` | Jump to last image |

### Image Synchronization

Enable these features for aligned sequences:

- ✅ **Sync Navigation**: Navigate both sides together
- ✅ **Match by Filename**: Auto-align images with matching filenames

---

## ⌨️ Keyboard Shortcuts

### Edit Modes

| Key | Mode | Description |
|-----|------|-------------|
| `M` | **Move** | Move existing keypoints |
| `A` | **Add** | Add new keypoints |
| `D` | **Delete** | Delete keypoints |

### Navigation

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate (active side) |
| `←` `→` | Navigate (both sides) |
| `Tab` | Switch active side |

### Actions

| Shortcut | Action |
|----------|--------|
| `Space` | Toggle skeleton display |
| `Esc` | Deselect keypoint |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+C` | Copy from previous (active side) |
| `Ctrl+B` | Copy from previous (both sides) |

### Quick Reference Card

```
┌─────────────────────────────────────────┐
│  EDIT MODES                             │
│  M = Move  |  A = Add  |  D = Delete   │
│                                          │
│  NAVIGATION                             │
│  ↑↓ = Active Side  |  ←→ = Both Sides  │
│                                          │
│  ACTIONS                                │
│  Space = Skeleton  |  Tab = Switch Side │
│  Esc = Deselect    |  Ctrl+Z/Y = Undo  │
└─────────────────────────────────────────┘
```

---

## 🎯 Keypoint Editing

### Edit Modes Explained

#### 1. Move Mode (`M`)

- **Click** near a keypoint to select it (highlighted in yellow)
- **Drag** to move the keypoint
- **Click** on canvas to deselect

#### 2. Add Mode (`A`)

- **Click** anywhere on canvas to add a new keypoint
- Keypoints are added in sequence
- Each keypoint has a unique color

#### 3. Delete Mode (`D`)

- **Click** on a keypoint to delete it
- Confirmation may be required

### Keypoint Visibility (COCO Mode)

When using COCO format, each keypoint has a visibility value:

| Visibility | Value | Appearance | Description |
|------------|-------|------------|-------------|
| **Not Labeled** | `v=0` | Gray | Keypoint not annotated |
| **Labeled, Not Visible** | `v=1` | Red outline | Keypoint exists but not visible |
| **Labeled, Visible** | `v=2` | Normal color | Keypoint is visible and annotated |

**Change visibility:**
- Use radio buttons in sidebar (COCO mode)
- Right-click keypoint → Set visibility

### Right-Click Context Menu

#### On Keypoint:
- 📋 View keypoint information
- 👁️ Set visibility (COCO mode)
- 📄 Copy coordinates
- 🗑️ Delete keypoint

#### On Canvas:
- 📋 Paste keypoint (if coordinates copied)
- 🧹 Clear all keypoints

---

## 🚀 Advanced Features

### Undo/Redo System

- **Undo**: `Ctrl+Z` - Revert last action
- **Redo**: `Ctrl+Y` - Restore undone action
- **History**: Up to 50 states per side

### Copy from Previous Frame

Perfect for video sequences:

- `Ctrl+C`: Copy keypoints from previous frame (active side)
- `Ctrl+B`: Copy keypoints from previous frame (both sides)

> 💡 **Use Case**: Annotating similar frames in a sequence

### Zoom and Pan

| Action | Method |
|--------|--------|
| **Zoom In/Out** | Scroll mouse wheel |
| **Enable Zoom Mode** | Click "Zoom" button |
| **Reset Zoom** | Click "Reset Zoom" |

### Customizing Keypoint Names

1. Go to **Settings → Edit Keypoint Names**
2. Choose editing mode:
   - **Dictionary Format**: Paste/edit Python dictionary
   - **Individual Fields**: Edit each name separately
3. Click **"Save"** to apply
4. Click **"Reset to Default"** to restore

**Default Keypoints (19 total):**

```
Body (15):
  head, l_ear, r_ear
  l_shoulder, r_shoulder
  l_elbow, r_elbow
  l_wrist, r_wrist
  l_hip, r_hip
  l_knee, r_knee
  l_foot, r_foot

Golf Club (4):
  club_grip, hand, club_shaft, club_hosel
```

### Format Modes

#### Standard Mode
- Simple format: `[x, y]` or `[x, y, visibility]`
- Basic annotation structure

#### COCO Mode
- Full COCO format support
- Visibility values (0, 1, 2)
- Export-ready format
- Includes bounding boxes and areas

---

## 📤 Export & Import

### Export to COCO Format

**Steps:**
1. Click **Export** button (top right)
2. Select **"Export Left to COCO..."** or **"Export Right to COCO..."**
3. Choose save location
4. Done! ✅

**Exported File Includes:**
- ✅ Image information
- ✅ Annotations with keypoints
- ✅ Bounding boxes
- ✅ Categories and skeleton
- ✅ Visibility states

### Export Statistics

**Steps:**
1. Click **Export → Export Statistics...**
2. Choose save location
3. Statistics saved as JSON

**Statistics Include:**
```json
{
  "total_images": 100,
  "annotated_images": 75,
  "total_keypoints": 1425,
  "average_keypoints_per_image": 19.0,
  "visibility_counts": {
    "0": 50,
    "1": 200,
    "2": 1175
  },
  "completion_percentage": 75.0
}
```

### Save Annotations

- **Auto-save**: Every 30 seconds automatically
- **Manual save**: Click "Save" button in sidebar
- **Location**: Same folder as images or specified annotation file

---

## 💡 Tips & Best Practices

### Efficient Workflow

1. **Use Keyboard Shortcuts**
   - Learn `M`, `A`, `D` for quick mode switching
   - Use arrow keys for navigation
   - `Tab` to switch sides quickly

2. **Enable Sync Navigation**
   - For aligned sequences
   - Saves time when navigating

3. **Copy from Previous Frame**
   - Use `Ctrl+C` or `Ctrl+B` for similar frames
   - Adjust keypoints instead of re-annotating

### Quality Control

1. **Check Visibility** (COCO mode)
   - Verify visibility states are correct
   - Use right-click menu for quick changes

2. **Review Keypoint List**
   - Check sidebar list for completeness
   - Ensure all keypoints are present

3. **Use Progress Indicator**
   - Track completion percentage
   - Identify missing annotations

### Performance Tips

- ✅ Application uses image caching (faster display)
- ✅ Redraws are throttled (smooth interaction)
- ✅ Large image sets handled efficiently

---

## 🔧 Troubleshooting

### Images Not Loading

**Problem:** Images don't appear after selecting folder

**Solutions:**
- ✅ Check file format (supports: jpg, jpeg, png, bmp, gif)
- ✅ Verify folder path is correct
- ✅ Check file permissions
- ✅ Ensure images are in the selected folder (not subfolders)

### Keypoints Not Visible

**Problem:** Can't see keypoints on canvas

**Solutions:**
- ✅ Check if skeleton display is enabled (`Space` key)
- ✅ Verify keypoint visibility settings (COCO mode)
- ✅ Check zoom level (try resetting zoom)
- ✅ Ensure you're in the correct edit mode

### Export Errors

**Problem:** Export fails or creates invalid files

**Solutions:**
- ✅ Ensure annotations exist before exporting
- ✅ Check file write permissions
- ✅ Verify JSON format compatibility
- ✅ Try exporting to a different location

### Performance Issues

**Problem:** Application is slow or laggy

**Solutions:**
- ✅ Close other applications
- ✅ Reduce image resolution if possible
- ✅ Check available memory
- ✅ Restart the application

### Keyboard Shortcuts Not Working

**Problem:** Keyboard shortcuts don't respond

**Solutions:**
- ✅ Click on canvas to focus it
- ✅ Check if another application has focus
- ✅ Try clicking on the application window first

---

# 🇰🇷 한국어 가이드

## 🚀 빠른 시작

### 1단계: 애플리케이션 실행

**Windows:**
```bash
# 배치 파일 더블 클릭
run_dual_labeler.bat

# 또는 명령줄에서 실행
python labeling/dual_keypoint_labeler.py
```

**Mac/Linux:**
```bash
python labeling/dual_keypoint_labeler.py
```

### 2단계: 이미지 로드

1. **"Select Left Folder"** 클릭 → 첫 번째 이미지 폴더 선택 (예: FO - 정면)
2. **"Select Right Folder"** 클릭 → 두 번째 이미지 폴더 선택 (예: DL - 대각선)
3. 이미지가 자동으로 로드되고 표시됩니다

### 3단계: 주석 시작

1. **편집 모드 선택**: `M` (이동), `A` (추가), 또는 `D` (삭제) 키 누르기
2. **이미지 클릭**하여 키포인트 추가/이동
3. **화살표 키**로 탐색 (`↑` `↓` 활성 측면, `←` `→` 양쪽 모두)
4. **`Tab` 키**로 측면 전환

> 💡 **팁**: 버튼 위에 마우스를 올리면 키보드 단축키가 포함된 도구 설명이 표시됩니다!

---

## 🖥️ 인터페이스 개요

### 주요 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  [헤더 바]  폴더 선택 | 주석 로드 | 내보내기                 │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│ 사이드바 │              왼쪽 캔버스 (FO)                      │
│          │                                                   │
│ • 활성   │                                                   │
│   측면   │                                                   │
│ • 편집   ├──────────────────────────────────────────────────┤
│   모드   │              오른쪽 캔버스 (DL)                   │
│ • 형식   │                                                   │
│ • 탐색   │                                                   │
│ • 목록   │                                                   │
│          │                                                   │
├──────────┴──────────────────────────────────────────────────┤
│  [상태 표시줄]  모드 | 키포인트 | 확대/축소 | 저장 안 됨     │
└─────────────────────────────────────────────────────────────┘
```

### 구성 요소 설명

| 구성 요소 | 설명 |
|-----------|------|
| **헤더 바** | 폴더 선택, 주석 로드, 내보내기 옵션 |
| **사이드바** | 활성 측면, 편집 모드, 탐색, 키포인트 목록 컨트롤 |
| **왼쪽 캔버스** | 첫 번째 이미지 세트 (예: 정면 뷰) |
| **오른쪽 캔버스** | 두 번째 이미지 세트 (예: 대각선 뷰) |
| **상태 표시줄** | 실시간 정보 (모드, 키포인트, 확대/축소, 상태) |

---

## ⚙️ 기본 작업

### 활성 측면 선택

**방법 1:** "ACTIVE SIDE" 섹션의 라디오 버튼 클릭  
**방법 2:** `Tab` 키를 눌러 전환

> 활성 측면은 색상 테두리로 강조 표시됩니다

### 이미지 로드

| 작업 | 단계 |
|--------|-------|
| **왼쪽 이미지 로드** | "Select Left Folder" 클릭 → 폴더 선택 |
| **오른쪽 이미지 로드** | "Select Right Folder" 클릭 → 폴더 선택 |
| **주석 로드** | "Load Left/Right Annotations" 클릭 → JSON 파일 선택 |

**지원 형식:**
- 이미지: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`
- 주석: 표준 JSON 또는 COCO 형식

### 탐색

| 단축키 | 작업 |
|----------|--------|
| `↑` | 이전 이미지 (활성 측면만) |
| `↓` | 다음 이미지 (활성 측면만) |
| `←` | 이전 이미지 (양쪽 모두) |
| `→` | 다음 이미지 (양쪽 모두) |
| `◄ Previous` | 이전 이미지 버튼 |
| `Next ►` | 다음 이미지 버튼 |
| `◄◄ First` | 첫 번째 이미지로 이동 |
| `Last ►►` | 마지막 이미지로 이동 |

### 이미지 동기화

정렬된 시퀀스에 대해 다음 기능을 활성화하세요:

- ✅ **Sync Navigation**: 양쪽을 함께 탐색
- ✅ **Match by Filename**: 일치하는 파일 이름으로 이미지 자동 정렬

---

## ⌨️ 키보드 단축키

### 편집 모드

| 키 | 모드 | 설명 |
|-----|------|-------------|
| `M` | **이동** | 기존 키포인트 이동 |
| `A` | **추가** | 새 키포인트 추가 |
| `D` | **삭제** | 키포인트 삭제 |

### 탐색

| 키 | 작업 |
|-----|--------|
| `↑` `↓` | 탐색 (활성 측면) |
| `←` `→` | 탐색 (양쪽 모두) |
| `Tab` | 활성 측면 전환 |

### 작업

| 단축키 | 작업 |
|----------|--------|
| `Space` | 스켈레톤 표시 토글 |
| `Esc` | 키포인트 선택 해제 |
| `Ctrl+Z` | 실행 취소 |
| `Ctrl+Y` | 다시 실행 |
| `Ctrl+C` | 이전에서 복사 (활성 측면) |
| `Ctrl+B` | 이전에서 복사 (양쪽 모두) |

### 빠른 참조 카드

```
┌─────────────────────────────────────────┐
│  편집 모드                               │
│  M = 이동  |  A = 추가  |  D = 삭제     │
│                                          │
│  탐색                                    │
│  ↑↓ = 활성 측면  |  ←→ = 양쪽 모두     │
│                                          │
│  작업                                    │
│  Space = 스켈레톤  |  Tab = 측면 전환   │
│  Esc = 선택 해제  |  Ctrl+Z/Y = 실행 취소│
└─────────────────────────────────────────┘
```

---

## 🎯 키포인트 편집

### 편집 모드 설명

#### 1. 이동 모드 (`M`)

- **클릭**하여 키포인트 근처를 선택 (노란색으로 강조)
- **드래그**하여 키포인트 이동
- **캔버스 클릭**하여 선택 해제

#### 2. 추가 모드 (`A`)

- **캔버스 어디든 클릭**하여 새 키포인트 추가
- 키포인트는 순차적으로 추가됩니다
- 각 키포인트는 고유한 색상을 가집니다

#### 3. 삭제 모드 (`D`)

- **키포인트 클릭**하여 삭제
- 확인이 필요할 수 있습니다

### 키포인트 가시성 (COCO 모드)

COCO 형식을 사용할 때 각 키포인트에는 가시성 값이 있습니다:

| 가시성 | 값 | 모양 | 설명 |
|------------|-------|------------|-------------|
| **레이블 없음** | `v=0` | 회색 | 키포인트가 주석 처리되지 않음 |
| **레이블 있음, 보이지 않음** | `v=1` | 빨간색 테두리 | 키포인트가 존재하지만 보이지 않음 |
| **레이블 있음, 보임** | `v=2` | 일반 색상 | 키포인트가 보이고 주석 처리됨 |

**가시성 변경:**
- 사이드바의 라디오 버튼 사용 (COCO 모드)
- 키포인트 우클릭 → 가시성 설정

### 우클릭 컨텍스트 메뉴

#### 키포인트에서:
- 📋 키포인트 정보 보기
- 👁️ 가시성 설정 (COCO 모드)
- 📄 좌표 복사
- 🗑️ 키포인트 삭제

#### 캔버스에서:
- 📋 키포인트 붙여넣기 (좌표가 복사된 경우)
- 🧹 모든 키포인트 지우기

---

## 🚀 고급 기능

### 실행 취소/다시 실행 시스템

- **실행 취소**: `Ctrl+Z` - 마지막 작업 되돌리기
- **다시 실행**: `Ctrl+Y` - 되돌린 작업 복원
- **기록**: 측면당 최대 50개 상태

### 이전 프레임에서 복사

비디오 시퀀스에 완벽합니다:

- `Ctrl+C`: 이전 프레임에서 키포인트 복사 (활성 측면)
- `Ctrl+B`: 이전 프레임에서 키포인트 복사 (양쪽 모두)

> 💡 **사용 사례**: 시퀀스에서 유사한 프레임 주석 처리

### 확대/축소 및 팬

| 작업 | 방법 |
|--------|--------|
| **확대/축소** | 마우스 휠 스크롤 |
| **확대 모드 활성화** | "Zoom" 버튼 클릭 |
| **확대/축소 재설정** | "Reset Zoom" 클릭 |

### 키포인트 이름 사용자 지정

1. **Settings → Edit Keypoint Names**로 이동
2. 편집 모드 선택:
   - **Dictionary Format**: Python 딕셔너리 붙여넣기/편집
   - **Individual Fields**: 각 이름을 개별적으로 편집
3. **"Save"** 클릭하여 적용
4. **"Reset to Default"** 클릭하여 복원

**기본 키포인트 (총 19개):**

```
신체 (15개):
  head, l_ear, r_ear
  l_shoulder, r_shoulder
  l_elbow, r_elbow
  l_wrist, r_wrist
  l_hip, r_hip
  l_knee, r_knee
  l_foot, r_foot

골프 클럽 (4개):
  club_grip, hand, club_shaft, club_hosel
```

### 형식 모드

#### 표준 모드
- 간단한 형식: `[x, y]` 또는 `[x, y, visibility]`
- 기본 주석 구조

#### COCO 모드
- 전체 COCO 형식 지원
- 가시성 값 (0, 1, 2)
- 내보내기 준비 형식
- 경계 상자 및 영역 포함

---

## 📤 내보내기 및 가져오기

### COCO 형식으로 내보내기

**단계:**
1. **Export** 버튼 클릭 (오른쪽 상단)
2. **"Export Left to COCO..."** 또는 **"Export Right to COCO..."** 선택
3. 저장 위치 선택
4. 완료! ✅

**내보낸 파일 포함:**
- ✅ 이미지 정보
- ✅ 키포인트가 있는 주석
- ✅ 경계 상자
- ✅ 카테고리 및 스켈레톤
- ✅ 가시성 상태

### 통계 내보내기

**단계:**
1. **Export → Export Statistics...** 클릭
2. 저장 위치 선택
3. 통계가 JSON으로 저장됨

**통계 포함:**
```json
{
  "total_images": 100,
  "annotated_images": 75,
  "total_keypoints": 1425,
  "average_keypoints_per_image": 19.0,
  "visibility_counts": {
    "0": 50,
    "1": 200,
    "2": 1175
  },
  "completion_percentage": 75.0
}
```

### 주석 저장

- **자동 저장**: 30초마다 자동으로 저장
- **수동 저장**: 사이드바의 "Save" 버튼 클릭
- **위치**: 이미지와 같은 폴더 또는 지정된 주석 파일

---

## 💡 팁 및 모범 사례

### 효율적인 워크플로우

1. **키보드 단축키 사용**
   - 빠른 모드 전환을 위해 `M`, `A`, `D` 학습
   - 탐색에 화살표 키 사용
   - 빠른 측면 전환을 위해 `Tab` 사용

2. **동기화 탐색 활성화**
   - 정렬된 시퀀스에 대해
   - 탐색 시 시간 절약

3. **이전 프레임에서 복사**
   - 유사한 프레임에 대해 `Ctrl+C` 또는 `Ctrl+B` 사용
   - 다시 주석 처리하는 대신 키포인트 조정

### 품질 관리

1. **가시성 확인** (COCO 모드)
   - 가시성 상태가 올바른지 확인
   - 빠른 변경을 위해 우클릭 메뉴 사용

2. **키포인트 목록 검토**
   - 완전성을 위해 사이드바 목록 확인
   - 모든 키포인트가 있는지 확인

3. **진행률 표시기 사용**
   - 완료율 추적
   - 누락된 주석 식별

### 성능 팁

- ✅ 애플리케이션은 이미지 캐싱을 사용합니다 (더 빠른 표시)
- ✅ 다시 그리기가 제한됩니다 (부드러운 상호 작용)
- ✅ 대용량 이미지 세트가 효율적으로 처리됩니다

---

## 🔧 문제 해결

### 이미지가 로드되지 않음

**문제:** 폴더 선택 후 이미지가 나타나지 않음

**해결 방법:**
- ✅ 파일 형식 확인 (지원: jpg, jpeg, png, bmp, gif)
- ✅ 폴더 경로가 올바른지 확인
- ✅ 파일 권한 확인
- ✅ 이미지가 선택한 폴더에 있는지 확인 (하위 폴더 아님)

### 키포인트가 보이지 않음

**문제:** 캔버스에서 키포인트를 볼 수 없음

**해결 방법:**
- ✅ 스켈레톤 표시가 활성화되어 있는지 확인 (`Space` 키)
- ✅ 키포인트 가시성 설정 확인 (COCO 모드)
- ✅ 확대/축소 수준 확인 (확대/축소 재설정 시도)
- ✅ 올바른 편집 모드에 있는지 확인

### 내보내기 오류

**문제:** 내보내기가 실패하거나 잘못된 파일 생성

**해결 방법:**
- ✅ 내보내기 전에 주석이 있는지 확인
- ✅ 파일 쓰기 권한 확인
- ✅ JSON 형식 호환성 확인
- ✅ 다른 위치로 내보내기 시도

### 성능 문제

**문제:** 애플리케이션이 느리거나 지연됨

**해결 방법:**
- ✅ 다른 애플리케이션 닫기
- ✅ 가능하면 이미지 해상도 줄이기
- ✅ 사용 가능한 메모리 확인
- ✅ 애플리케이션 재시작

### 키보드 단축키가 작동하지 않음

**문제:** 키보드 단축키가 응답하지 않음

**해결 방법:**
- ✅ 캔버스를 클릭하여 포커스 설정
- ✅ 다른 애플리케이션이 포커스를 가지고 있는지 확인
- ✅ 먼저 애플리케이션 창을 클릭해 보세요

---

## 📞 Support / 지원

For issues or questions, please refer to the code documentation or contact the development team.

문제나 질문이 있으시면 코드 문서를 참조하거나 개발팀에 문의하세요.

---

**Version**: 1.0  
**Last Updated**: 2024
