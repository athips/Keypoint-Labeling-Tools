# Keypoint Labeling Tool

A comprehensive GUI application for labeling and editing keypoints on images with advanced features for efficient annotation workflow.

## Features

### Core Functionality
- **Image Management**: Select image folder and browse through images with visual status indicators
- **Annotation Import/Export**: Import JSON annotation files with automatic path matching
- **Keypoint Editing**: Move, add, and delete keypoints with intuitive mouse controls
- **Skeleton Visualization**: Visualize keypoint connections with color-coded skeleton lines
- **Zoom Controls**: Zoom in/out with mouse wheel (Ctrl + scroll) or buttons
- **Undo/Redo**: Full undo/redo support for all keypoint operations (up to 50 steps)

### Advanced Features

#### Auto-Save
- Automatic saving every 30 seconds when there are unsaved changes
- Visual save indicator showing "✓ Auto-saved" or "✓ Saved"
- Tracks unsaved changes automatically

#### Progress Tracking
- Real-time progress display: "Progress: X/Y (Z%)"
- Color-coded image list:
  - 🟢 Green background = annotated images
  - 🔴 Red background = unannotated images
- Filter to show only unannotated images
- Automatic progress updates

#### Batch Operations
- **Copy to Next N Frames**: Copy keypoints to multiple consecutive frames at once
- Useful for video sequences with similar poses

#### Enhanced Navigation
- **Go to Image**: Jump directly to any image by number (Ctrl+G)
- **Image Filtering**: Show only unannotated images
- Visual status indicators in image list

#### Visual Customization
- **Toggle Skeleton**: Show/hide skeleton connection lines
- **Toggle Labels**: Show/hide keypoint name labels
- **Adjustable Keypoint Size**: Slider to change keypoint circle size (4-20 pixels)
- Real-time visual updates

#### Customizable Keypoint Names
- Edit keypoint names via Settings menu
- Support for dictionary format input:
  ```python
  KEYPOINT_LABELS = {
      0: "head",
      1: "l_eye",
      2: "r_eye",
      ...
  }
  ```
- Individual field editing option

#### Export Options
- **COCO Format**: Export to standard COCO keypoint format with visibility flags
- **YOLO Format**: Export normalized coordinates for YOLO training
- **Pascal VOC Format**: Export XML files in Pascal VOC format
- **Statistics Report**: Generate comprehensive annotation statistics report

#### Path Display
- Shows full image path and matched annotation path
- Tooltip on hover for complete paths
- Helps verify correct annotation matching

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Workflow

1. **Start the application**:
   ```bash
   python keypoint_labeler.py
   ```

2. **Select Image Folder**: Click "Select Image Folder" and choose your images directory

3. **Import Annotations** (optional): Click "Import Annotations" to load existing JSON annotation file

4. **Navigate Images**: Use arrow keys or Previous/Next buttons

5. **Edit Keypoints**:
   - **Move Mode**: Click and drag keypoints to reposition
   - **Add Mode**: Click on image to add new keypoint
   - **Delete Mode**: Click on keypoint to delete it

6. **Save**: Annotations auto-save every 30 seconds, or click "Save Annotations" manually

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Arrow Keys** (↑↓←→) | Navigate between images |
| **Ctrl+C** | Copy keypoints from previous frame |
| **Ctrl+Z** | Undo last action |
| **Ctrl+Y** | Redo last undone action |
| **Ctrl+G** | Go to specific image number |
| **Ctrl + Mouse Wheel** | Zoom in/out at mouse position |
| **Mouse Wheel** | Zoom in/out at mouse position |

### Mode Selection

Use the mode buttons to switch between:
- **Move**: Click and drag keypoints to move them
- **Add**: Click anywhere on image to add a new keypoint
- **Delete**: Click on a keypoint to delete it

### Batch Operations

1. Annotate the first frame
2. Click "Copy to Next N Frames..."
3. Enter the number of frames to copy to
4. Keypoints will be copied to consecutive frames

### Export Options

#### Export to COCO Format
1. Go to **Export → Export to COCO Format...**
2. Choose save location
3. File will be saved in COCO keypoint format with:
   - Visibility flags (0=not labeled, 1=occluded, 2=visible)
   - Bounding boxes calculated from keypoints
   - Proper COCO structure

#### Export to YOLO Format
1. Go to **Export → Export to YOLO Format...**
2. Select output directory
3. Labels will be saved in `labels/` subdirectory
4. Format: normalized coordinates (0-1 range)

#### Export to Pascal VOC Format
1. Go to **Export → Export to Pascal VOC Format...**
2. Select output directory
3. XML files will be saved in `annotations/` subdirectory

#### Export Statistics Report
1. Go to **Export → Export Statistics Report...**
2. Choose save location (`.txt` or `.csv`)
3. Report includes:
   - Overview statistics
   - Keypoint distribution
   - Image dimensions
   - Keypoint names and skeleton connections

### Customizing Keypoint Names

1. Go to **Settings → Edit Keypoint Names...**
2. Use the **Dictionary Format** tab to paste your keypoint labels:
   ```python
   KEYPOINT_LABELS = {
       0: "head",
       1: "l_eye",
       2: "r_eye",
       3: "l_shoulder",
       4: "r_shoulder",
       ...
   }
   ```
3. Click "Save from Dictionary" to apply
4. Or use the **Individual Fields** tab to edit one by one

### Visual Settings

In the **Visual Settings** panel:
- **Show Skeleton**: Toggle skeleton connection lines
- **Show Keypoint Labels**: Toggle keypoint name labels
- **Keypoint Size**: Adjust slider to change keypoint circle size

### Progress Tracking

- View progress in the Navigation panel: "Progress: X/Y (Z%)"
- Check "Show only unannotated" to filter image list
- Color-coded list shows annotation status at a glance

## Annotation Format

### Input Format

The tool supports JSON annotation files with the following structure:

```json
{
  "info": {
    "description": "Dataset description",
    "num_images": 100,
    "num_keypoints": 19
  },
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

### Path Matching

The tool automatically matches annotation paths with image paths from the selected folder, handling:
- Different path separators (forward/backward slashes)
- Relative paths from base images directory
- Filename-only matching as fallback
- Full path display for verification

### COCO Export Format

When exporting to COCO format, keypoints are converted to:
```json
{
  "keypoints": [x1, y1, v1, x2, y2, v2, ...],
  "num_keypoints": 19,
  "bbox": [x, y, width, height],
  "area": width * height
}
```

Where visibility flags:
- `v=0`: Not labeled
- `v=1`: Labeled but occluded
- `v=2`: Labeled and visible

## Tips & Best Practices

1. **Use Keyboard Shortcuts**: Learn the shortcuts for faster workflow
2. **Batch Copy**: Use batch copy for video sequences with similar poses
3. **Progress Tracking**: Use the filter to focus on unannotated images
4. **Visual Settings**: Hide skeleton/labels when they clutter the view
5. **Auto-Save**: The tool auto-saves every 30 seconds - watch for the indicator
6. **Undo/Redo**: Use Ctrl+Z/Y to quickly fix mistakes
7. **Go to Image**: Use Ctrl+G to jump to specific images quickly
8. **Path Verification**: Check the path display to ensure correct annotation matching

## Troubleshooting

### Images Not Loading
- Check that image folder path is correct
- Verify image file extensions are supported (.jpg, .jpeg, .png, .bmp, .gif)

### Annotations Not Matching
- Check the path display in status bar
- Verify annotation paths in JSON match image folder structure
- Tool tries multiple matching strategies automatically

### Keypoints Not Visible
- Check "Show Keypoint Labels" in Visual Settings
- Increase keypoint size with the slider
- Verify keypoints exist in annotation data

### Export Issues
- Ensure you have write permissions to the output directory
- Check that annotations contain valid keypoint data
- Verify image dimensions are set correctly

## Requirements

- Python 3.6+
- Pillow >= 9.0.0
- tkinter (usually included with Python)

## License

This tool is provided as-is for keypoint annotation tasks.
