# Keypoint Labeling Tool

A GUI application for labeling and editing keypoints on images.

## Features

- Select image folder and browse through images
- Import annotation files (JSON format)
- Edit keypoints: move, add, delete
- Copy keypoints from previous frame
- Zoom in/out with mouse wheel (Ctrl + scroll)
- Skeleton visualization with connecting lines
- Keyboard shortcuts for navigation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python keypoint_labeler.py
```

## Keyboard Shortcuts

- **Arrow Keys (Up/Down/Left/Right)**: Navigate between images
- **Ctrl+C**: Copy keypoints from previous frame

## Annotation Format

The tool supports JSON annotation files with the following structure:

```json
{
  "annotations": [
    {
      "image": "DL/frames/gsp3_dl/frame_000002.jpg",
      "width": 1280,
      "height": 720,
      "keypoints": [
        [x1, y1],
        [x2, y2],
        ...
      ]
    }
  ]
}
```

The tool will automatically match annotation paths with image paths from the selected folder, handling various path formats and structures.

