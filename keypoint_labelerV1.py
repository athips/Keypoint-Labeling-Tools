"""
Keypoint Labeling Tool
A GUI application for labeling and editing keypoints on images.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import copy
import ast
from pathlib import Path
from PIL import Image, ImageTk
import math
from datetime import datetime


class KeypointLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("Keypoint Labeler")
        self.root.geometry("1400x900")
        
        # Data storage
        self.image_folder = None
        self.annotation_file = None
        self.annotations_data = None
        self.annotation_dict = {}  # Initialize annotation lookup dict
        self.current_image_index = 0
        self.image_list = []
        self.current_annotation = None
        self.current_image_path = None
        self.current_image = None
        self.photo_image = None  # PhotoImage object for display
        self.scale_factor = 1.0
        self.base_scale_factor = 1.0  # Base scale for fitting
        self.zoom_mode = False  # Track if we're in zoom mode
        self.offset_x = 0
        self.offset_y = 0
        
        # Keypoint editing state
        self.selected_keypoint = None
        self.keypoint_radius = 8
        
        # Undo/Redo system
        self.undo_stack = []  # List of keypoint states for undo
        self.redo_stack = []  # List of keypoint states for redo
        self.max_history = 50  # Maximum history entries
        
        # Auto-save system
        self.auto_save_enabled = True
        self.auto_save_interval = 30  # seconds
        self.last_save_time = 0
        self.unsaved_changes = False
        self.auto_save_job = None
        
        # Progress tracking
        self.annotation_status = {}  # Track which images have annotations
        self.show_only_unannotated = False
        
        # Visual settings
        self.show_skeleton = True
        self.show_keypoint_labels = True
        self.keypoint_size = 8
        self.keypoint_colors = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
            '#FF8000', '#8000FF', '#FF0080', '#80FF00', '#0080FF', '#FF8080',
            '#80FF80', '#8080FF', '#FFFF80', '#FF80FF', '#80FFFF', '#FF4040',
            '#40FF40'
        ]
        self.keypoint_names = [
            'KP0', 'KP1', 'KP2', 'KP3', 'KP4', 'KP5', 'KP6', 'KP7', 'KP8',
            'KP9', 'KP10', 'KP11', 'KP12', 'KP13', 'KP14', 'KP15', 'KP16',
            'KP17', 'KP18'
        ]
        
        # Skeleton connections (pairs of keypoint indices)
        self.skeleton = [
            (0, 1), (0, 2),  # head to eyes
            (3, 4), (4, 10), (3, 9), (9, 10),  # shoulders and hips
            (3, 5), (5, 7), (4, 6), (6, 8),  # arms
            (9, 11), (11, 13), (10, 12), (12, 14),  # legs
            (15, 16), (16, 17), (17, 18)  # club
        ]
        
        # UI Setup
        self.setup_ui()
        
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Edit Keypoint Names...", command=self.edit_keypoint_names)
        
        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Export to COCO Format...", command=self.export_to_coco)
        export_menu.add_separator()
        export_menu.add_command(label="Export to YOLO Format...", command=self.export_to_yolo)
        export_menu.add_command(label="Export to Pascal VOC Format...", command=self.export_to_pascal_voc)
        export_menu.add_separator()
        export_menu.add_command(label="Export Statistics Report...", command=self.export_statistics)
        
        # Top frame for controls
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # Folder selection
        ttk.Button(top_frame, text="Select Image Folder", 
                  command=self.select_image_folder).pack(side=tk.LEFT, padx=5)
        self.image_folder_label = ttk.Label(top_frame, text="No folder selected")
        self.image_folder_label.pack(side=tk.LEFT, padx=5)
        
        # Annotation file selection
        ttk.Button(top_frame, text="Import Annotations", 
                  command=self.import_annotations).pack(side=tk.LEFT, padx=5)
        self.annotation_label = ttk.Label(top_frame, text="No annotation file")
        self.annotation_label.pack(side=tk.LEFT, padx=5)
        
        # Save button with auto-save indicator
        save_frame = ttk.Frame(top_frame)
        save_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="Save Annotations", 
                  command=self.save_annotations).pack(side=tk.LEFT)
        self.save_indicator = ttk.Label(save_frame, text="", foreground="green")
        self.save_indicator.pack(side=tk.LEFT, padx=5)
        
        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - image list and controls
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Image navigation
        nav_frame = ttk.LabelFrame(left_panel, text="Navigation", padding="10")
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_frame, text="◀ Previous", 
                  command=self.previous_image).pack(fill=tk.X, pady=2)
        ttk.Button(nav_frame, text="Next ▶", 
                  command=self.next_image).pack(fill=tk.X, pady=2)
        
        ttk.Button(nav_frame, text="Go to Image (Ctrl+G)", 
                  command=self.go_to_image).pack(fill=tk.X, pady=2)
        
        self.image_index_label = ttk.Label(nav_frame, text="Image: 0/0")
        self.image_index_label.pack(pady=2)
        
        # Progress tracking
        self.progress_label = ttk.Label(nav_frame, text="Progress: 0/0 (0%)")
        self.progress_label.pack(pady=2)
        
        # Filter checkbox
        self.filter_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(nav_frame, text="Show only unannotated", 
                       variable=self.filter_var,
                       command=self.apply_filter).pack(pady=2)
        
        # Image list with scrollbar
        list_frame = ttk.LabelFrame(left_panel, text="Image List", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.image_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        scrollbar.config(command=self.image_listbox.yview)
        
        # Keypoint controls
        keypoint_frame = ttk.LabelFrame(left_panel, text="Keypoint Controls", padding="10")
        keypoint_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(keypoint_frame, text="Mode:").pack(anchor=tk.W, pady=(0, 5))
        mode_button_frame = ttk.Frame(keypoint_frame)
        mode_button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.edit_mode = tk.StringVar(value="move")
        self.move_button = tk.Button(mode_button_frame, text="Move", 
                                     command=lambda: self.set_mode("move"),
                                     relief=tk.RAISED, bd=2)
        self.move_button.pack(side=tk.LEFT, expand=True, padx=2)
        self.add_button = tk.Button(mode_button_frame, text="Add", 
                                    command=lambda: self.set_mode("add"),
                                    relief=tk.RAISED, bd=2)
        self.add_button.pack(side=tk.LEFT, expand=True, padx=2)
        self.delete_button = tk.Button(mode_button_frame, text="Delete", 
                                       command=lambda: self.set_mode("delete"),
                                       relief=tk.RAISED, bd=2)
        self.delete_button.pack(side=tk.LEFT, expand=True, padx=2)
        
        # Update button appearance based on mode
        self.update_mode_buttons()
        
        # Undo/Redo buttons
        undo_redo_frame = ttk.Frame(keypoint_frame)
        undo_redo_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(undo_redo_frame, text="Undo (Ctrl+Z)", 
                  command=self.undo_action).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(undo_redo_frame, text="Redo (Ctrl+Y)", 
                  command=self.redo_action).pack(side=tk.LEFT, expand=True, padx=2)
        
        ttk.Button(keypoint_frame, text="Clear All Keypoints", 
                  command=self.clear_keypoints).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(keypoint_frame, text="Copy from Previous Frame (Ctrl+C)", 
                  command=self.copy_from_previous_frame).pack(fill=tk.X, pady=(0, 5))
        
        # Batch operations
        batch_frame = ttk.LabelFrame(keypoint_frame, text="Batch Operations", padding="5")
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(batch_frame, text="Copy to Next N Frames...", 
                  command=self.batch_copy_keypoints).pack(fill=tk.X, pady=2)
        
        # Visual controls
        visual_frame = ttk.LabelFrame(keypoint_frame, text="Visual Settings", padding="5")
        visual_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.skeleton_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(visual_frame, text="Show Skeleton", 
                       variable=self.skeleton_var,
                       command=self.toggle_skeleton).pack(anchor=tk.W)
        
        self.labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(visual_frame, text="Show Keypoint Labels", 
                       variable=self.labels_var,
                       command=self.toggle_labels).pack(anchor=tk.W)
        
        size_frame = ttk.Frame(visual_frame)
        size_frame.pack(fill=tk.X, pady=2)
        ttk.Label(size_frame, text="Keypoint Size:").pack(side=tk.LEFT)
        self.size_var = tk.IntVar(value=8)
        size_scale = ttk.Scale(size_frame, from_=4, to=20, 
                             variable=self.size_var, orient=tk.HORIZONTAL,
                             command=self.update_keypoint_size)
        size_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.size_label = ttk.Label(size_frame, text="8")
        self.size_label.pack(side=tk.LEFT)
        
        # Zoom controls
        zoom_frame = ttk.Frame(keypoint_frame)
        zoom_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(zoom_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(zoom_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(zoom_frame, text="Fit", command=self.fit_image).pack(side=tk.LEFT, expand=True, padx=2)
        
        # Keypoint list
        kp_list_frame = ttk.LabelFrame(left_panel, text="Keypoints", padding="10")
        kp_list_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        kp_scrollbar = ttk.Scrollbar(kp_list_frame)
        kp_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.keypoint_listbox = tk.Listbox(kp_list_frame, yscrollcommand=kp_scrollbar.set,
                                          height=10)
        self.keypoint_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.keypoint_listbox.bind('<<ListboxSelect>>', self.on_keypoint_select)
        kp_scrollbar.config(command=self.keypoint_listbox.yview)
        
        # Right panel - canvas for image display
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        canvas_frame = ttk.Frame(right_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(canvas_frame, 
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set,
                               bg='gray90')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Canvas bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Control-Button-4>", self.on_mousewheel)
        self.canvas.bind("<Control-Button-5>", self.on_mousewheel)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.focus_set()  # Enable focus for keyboard events
        
        # Keyboard shortcuts
        self.root.bind("<Up>", lambda e: self.previous_image())
        self.root.bind("<Down>", lambda e: self.next_image())
        self.root.bind("<Left>", lambda e: self.previous_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Control-c>", lambda e: self.copy_from_previous_frame())
        self.root.bind("<Control-C>", lambda e: self.copy_from_previous_frame())
        self.root.bind("<Control-z>", lambda e: self.undo_action())
        self.root.bind("<Control-Z>", lambda e: self.undo_action())
        self.root.bind("<Control-y>", lambda e: self.redo_action())
        self.root.bind("<Control-Y>", lambda e: self.redo_action())
        self.root.bind("<Control-g>", lambda e: self.go_to_image())
        self.root.bind("<Control-G>", lambda e: self.go_to_image())
        
        # Start auto-save timer
        if self.auto_save_enabled:
            self.start_auto_save()
        
        # Status bar with coordinate display
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.coord_label = ttk.Label(status_frame, text="Coordinates: (0, 0)", relief=tk.SUNKEN, width=25)
        self.coord_label.pack(side=tk.LEFT, padx=2)
        
        # Path display label (wider to show full paths)
        self.path_label = ttk.Label(status_frame, text="Image: - | Annotation: -", relief=tk.SUNKEN, width=120)
        self.path_label.pack(side=tk.LEFT, padx=2)
        
        # Store full paths for tooltip
        self.image_full_path_stored = None
        self.annotation_full_path_stored = None
        
        # Add tooltip functionality
        self.path_label.bind("<Enter>", self.show_path_tooltip)
        self.path_label.bind("<Leave>", self.hide_path_tooltip)
        
        self.status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
    def normalize_path(self, path):
        """Normalize path to use forward slashes for consistent matching"""
        if path is None:
            return None
        return str(path).replace('\\', '/')
    
    def get_relative_path(self, full_path, base_folder):
        """Get relative path from base folder, normalized"""
        try:
            rel_path = os.path.relpath(full_path, base_folder)
            return self.normalize_path(rel_path)
        except ValueError:
            # If paths are on different drives, try to match by structure
            return None
    
    def get_base_images_path(self, image_folder):
        """Find the base images directory from the selected image folder"""
        # Look for 'images' folder in the path
        path_parts = Path(image_folder).parts
        if 'images' in path_parts:
            # Find the index of 'images'
            images_idx = path_parts.index('images')
            # Return path up to and including 'images'
            base_path = Path(*path_parts[:images_idx + 1])
            return str(base_path)
        # If no 'images' folder found, return the image_folder itself
        return image_folder
    
    def get_annotation_match_path(self, full_image_path, image_folder):
        """Get the path that should match annotation JSON (relative to base images directory)"""
        # Find base images directory
        base_images = self.get_base_images_path(image_folder)
        
        # Get relative path from base images directory
        try:
            rel_path = os.path.relpath(full_image_path, base_images)
            return self.normalize_path(rel_path)
        except ValueError:
            # If can't compute relative path, return None
            return None
    
    def match_annotation_path(self, image_rel_path, annotation_path):
        """Check if image path matches annotation path using various strategies"""
        if not image_rel_path or not annotation_path:
            return False
        
        # Normalize both paths
        img_path_norm = self.normalize_path(image_rel_path)
        ann_path_norm = self.normalize_path(annotation_path)
        
        # Exact match
        if img_path_norm == ann_path_norm:
            return True
        
        # Match by filename only
        img_filename = os.path.basename(img_path_norm)
        ann_filename = os.path.basename(ann_path_norm)
        if img_filename == ann_filename:
            return True
        
        # Match by path ending (annotation path might be a suffix of image path)
        if img_path_norm.endswith(ann_path_norm) or ann_path_norm.endswith(img_path_norm):
            return True
        
        # Match by removing common prefixes
        # e.g., "DL/frames/gsp3_dl/frame_000002.jpg" should match "frames/gsp3_dl/frame_000002.jpg"
        img_parts = img_path_norm.split('/')
        ann_parts = ann_path_norm.split('/')
        
        # Try to find where annotation parts start in image parts
        for i in range(len(img_parts)):
            if img_parts[i:] == ann_parts[-len(img_parts[i:]):]:
                return True
        
        return False
        
    def select_image_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.image_folder = folder
            self.image_folder_label.config(text=os.path.basename(folder))
            self.load_image_list()
            self.update_status(f"Loaded {len(self.image_list)} images")
            # Clear path display if no images
            if not self.image_list:
                self.update_path_display(None, None)
            
    def load_image_list(self):
        if not self.image_folder:
            return
            
        self.image_list = []
        extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        
        for root, dirs, files in os.walk(self.image_folder):
            for file in files:
                if Path(file).suffix.lower() in extensions:
                    rel_path = os.path.relpath(os.path.join(root, file), self.image_folder)
                    self.image_list.append(rel_path)
        
        self.image_list.sort()
        self.refresh_image_list()
        self.update_progress()
            
        if self.image_list:
            self.current_image_index = 0
            self.load_current_image()
            
    def import_annotations(self):
        file = filedialog.askopenfilename(
            title="Import Annotation File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            try:
                with open(file, 'r') as f:
                    self.annotations_data = json.load(f)
                self.annotation_file = file
                self.annotation_label.config(text=os.path.basename(file))
                self.update_status(f"Loaded annotations for {len(self.annotations_data.get('annotations', []))} images")
                
                # Create annotation lookup dictionary
                # Key: normalized annotation path, Value: annotation object
                self.annotation_dict = {}
                for ann in self.annotations_data.get('annotations', []):
                    ann_path = ann.get('image', '')
                    if ann_path:
                        # Store with normalized path
                        normalized = self.normalize_path(ann_path)
                        self.annotation_dict[normalized] = ann
                        
                        # Also store with just filename for fallback
                        filename = os.path.basename(normalized)
                        if filename not in self.annotation_dict:
                            self.annotation_dict[filename] = ann
                    
                # Load current image if available
                if self.current_image_path:
                    self.load_current_image()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load annotations: {str(e)}")
                
    def load_current_image(self):
        if not self.image_list or self.current_image_index >= len(self.image_list):
            return
            
        if not self.image_folder:
            return
            
        image_path = self.image_list[self.current_image_index]
        full_path = os.path.join(self.image_folder, image_path)
        
        if not os.path.exists(full_path):
            self.update_status(f"Image not found: {full_path}")
            return
            
        try:
            # Load image
            self.current_image_path = image_path
            img = Image.open(full_path)
            if img is None:
                raise ValueError("Failed to open image file")
            self.current_image = img.copy()
            
            # Get relative path from image folder (normalized)
            image_rel_path = self.get_relative_path(full_path, self.image_folder)
            
            # Get path for matching against annotation (relative to base images directory)
            # This is the key: if image folder is C:\...\images\DL\frames\gsp3_dl
            # and image is frame_000002.jpg, we need to construct DL/frames/gsp3_dl/frame_000002.jpg
            annotation_match_path = self.get_annotation_match_path(full_path, self.image_folder)
            
            # Get or create annotation
            if self.annotations_data:
                if not hasattr(self, 'annotation_dict'):
                    self.annotation_dict = {}
                
                # Try to find matching annotation
                matched_annotation = None
                original_ann_path = None  # Store original annotation path
                
                # Strategy 1: Try exact match with annotation match path (relative to base images)
                if annotation_match_path and annotation_match_path in self.annotation_dict:
                    matched_annotation = self.annotation_dict[annotation_match_path]
                    original_ann_path = annotation_match_path
                
                # Strategy 2: Try exact match with normalized relative path (from selected folder)
                if not matched_annotation and image_rel_path and image_rel_path in self.annotation_dict:
                    matched_annotation = self.annotation_dict[image_rel_path]
                    original_ann_path = image_rel_path
                
                # Strategy 3: Try matching by filename
                if not matched_annotation:
                    filename = os.path.basename(image_rel_path) if image_rel_path else os.path.basename(image_path)
                    if filename in self.annotation_dict:
                        matched_annotation = self.annotation_dict[filename]
                        # Find the original annotation path that has this filename
                        for ann_path, ann in self.annotation_dict.items():
                            if os.path.basename(ann_path) == filename:
                                original_ann_path = ann_path
                                break
                
                # Strategy 4: Try path matching using match_annotation_path with annotation_match_path
                if not matched_annotation and annotation_match_path:
                    for ann_path, ann in self.annotation_dict.items():
                        if self.match_annotation_path(annotation_match_path, ann_path):
                            matched_annotation = ann
                            original_ann_path = ann_path
                            break
                
                # Strategy 5: Try path matching with image_rel_path as fallback
                if not matched_annotation and image_rel_path:
                    for ann_path, ann in self.annotation_dict.items():
                        if self.match_annotation_path(image_rel_path, ann_path):
                            matched_annotation = ann
                            original_ann_path = ann_path
                            break
                
                if matched_annotation:
                    self.current_annotation = matched_annotation
                    # Store original annotation path before updating
                    if original_ann_path is None:
                        original_ann_path = matched_annotation.get('image', 'unknown')
                    
                    # Update the image path in annotation to match current format
                    if self.current_annotation.get('image') != image_rel_path:
                        self.current_annotation['image'] = image_rel_path
                    
                    # Update path display with full paths
                    self.update_path_display(full_path, original_ann_path)
                    
                    # Debug: show keypoint count
                    kp_count = len(self.current_annotation.get('keypoints', []))
                    if kp_count > 0:
                        self.update_status(f"Loaded image with {kp_count} keypoints")
                    else:
                        self.update_status(f"Loaded image, no keypoints found")
                else:
                    # Create new annotation
                    self.current_annotation = {
                        'image': image_rel_path if image_rel_path else image_path,
                        'width': img.width,
                        'height': img.height,
                        'keypoints': []
                    }
                    if 'annotations' not in self.annotations_data:
                        self.annotations_data['annotations'] = []
                    self.annotations_data['annotations'].append(self.current_annotation)
                    # Add to lookup dict
                    if image_rel_path:
                        self.annotation_dict[image_rel_path] = self.current_annotation
                        filename = os.path.basename(image_rel_path)
                    if filename not in self.annotation_dict:
                        self.annotation_dict[filename] = self.current_annotation
                    # Update path display (no annotation match)
                    self.update_path_display(full_path, None)
                    self.update_status(f"Created new annotation for image")
            else:
                # No annotation data loaded, create temporary annotation
                self.current_annotation = {
                    'image': image_rel_path if image_rel_path else image_path,
                    'width': img.width,
                    'height': img.height,
                    'keypoints': []
                }
                # Update path display (no annotation file loaded)
                self.update_path_display(full_path, None)
            
            # Debug output
            kp_count = len(self.current_annotation.get('keypoints', []))
            if kp_count > 0:
                print(f"Loaded annotation for {image_rel_path} with {kp_count} keypoints")
                print(f"  Image folder relative: {image_rel_path}")
                if 'annotation_match_path' in locals():
                    print(f"  Annotation match path: {annotation_match_path}")
                if self.annotations_data and hasattr(self, 'current_annotation'):
                    matched_path = self.current_annotation.get('image', 'N/A')
                    print(f"  Matched annotation path: {matched_path}")
            else:
                print(f"No keypoints found for {image_rel_path}")
                print(f"  Image folder relative: {image_rel_path}")
                if 'annotation_match_path' in locals():
                    print(f"  Annotation match path: {annotation_match_path}")
                if self.annotations_data:
                    print(f"  Searched in annotation_dict with {len(self.annotation_dict)} entries")
            
            # Reset zoom and selection when loading new image
            self.zoom_mode = False
            self.selected_keypoint = None
            # Clear undo/redo stacks when loading new image
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.display_image()
            self.update_keypoint_list()
            self.update_image_index_label()
            self.update_progress()
            
        except Exception as e:
            error_msg = f"Failed to load image: {str(e)}"
            messagebox.showerror("Error", error_msg)
            import traceback
            print(f"Full error traceback:\n{traceback.format_exc()}")
            
    def display_image(self, preserve_zoom=False):
        if not self.current_image:
            return
            
        # Calculate display size (fit to canvas)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, lambda: self.display_image(preserve_zoom))
            return
            
        img = self.current_image.copy()
        img_width, img_height = img.size
        
        # Calculate scale to fit (only if not preserving zoom)
        if not preserve_zoom and not self.zoom_mode:
            scale_w = (canvas_width - 40) / img_width
            scale_h = (canvas_height - 40) / img_height
            self.scale_factor = min(scale_w, scale_h, 1.0)  # Don't scale up
            self.base_scale_factor = self.scale_factor
        
        display_width = int(img_width * self.scale_factor)
        display_height = int(img_height * self.scale_factor)
        
        # Use compatible resampling method for different Pillow versions
        try:
            # Pillow >= 9.0.0
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            # Pillow < 9.0.0
            try:
                resample = Image.LANCZOS
            except AttributeError:
                resample = Image.ANTIALIAS
        
        img = img.resize((display_width, display_height), resample)
        self.photo_image = ImageTk.PhotoImage(img)
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Display image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Draw keypoints
        self.draw_keypoints()
        
    def draw_keypoints(self):
        if not self.current_annotation:
            return
            
        keypoints = self.current_annotation.get('keypoints', [])
        if not keypoints:
            return
        
        # First, collect valid keypoint positions
        valid_keypoints = {}
        for idx, kp in enumerate(keypoints):
            if not kp or len(kp) < 2:
                continue
                
            try:
                x, y = float(kp[0]), float(kp[1])
                
                # Skip invalid coordinates
                if x < 0 or y < 0 or not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    continue
                
                # Scale coordinates
                display_x = x * self.scale_factor
                display_y = y * self.scale_factor
                valid_keypoints[idx] = (display_x, display_y)
            except (ValueError, TypeError, IndexError) as e:
                # Skip invalid keypoint data
                print(f"Warning: Invalid keypoint {idx}: {kp}, error: {e}")
                continue
        
        # Draw skeleton connections (lines between keypoints)
        if self.show_skeleton:
            for connection in self.skeleton:
                idx1, idx2 = connection
                if idx1 in valid_keypoints and idx2 in valid_keypoints:
                    x1, y1 = valid_keypoints[idx1]
                    x2, y2 = valid_keypoints[idx2]
                    
                    # Use a color based on the connection type
                    # Different colors for different body parts
                    if connection in [(0, 1), (0, 2)]:  # head
                        line_color = '#FF6B6B'
                    elif connection in [(3, 4), (4, 10), (3, 9), (9, 10)]:  # torso
                        line_color = '#4ECDC4'
                    elif connection in [(3, 5), (5, 7), (4, 6), (6, 8)]:  # arms
                        line_color = '#45B7D1'
                    elif connection in [(9, 11), (11, 13), (10, 12), (12, 14)]:  # legs
                        line_color = '#96CEB4'
                    elif connection in [(15, 16), (16, 17), (17, 18)]:  # club
                        line_color = '#FFEAA7'
                    else:
                        line_color = '#DDA0DD'  # default purple
                    
                    self.canvas.create_line(
                        x1, y1, x2, y2,
                        fill=line_color, width=2,
                        tags="skeleton"
                    )
        
        # Draw keypoints (circles)
        for idx, (display_x, display_y) in valid_keypoints.items():
            # Color
            color = self.keypoint_colors[idx % len(self.keypoint_colors)]
            
            # Draw circle
            radius = self.keypoint_radius
            self.canvas.create_oval(
                display_x - radius, display_y - radius,
                display_x + radius, display_y + radius,
                fill=color, outline='black', width=2,
                tags=f"keypoint_{idx}"
            )
            
            # Draw label
            if self.show_keypoint_labels:
                label = self.keypoint_names[idx % len(self.keypoint_names)]
                self.canvas.create_text(
                    display_x, display_y - radius - 10,
                    text=label, fill=color, font=('Arial', 8, 'bold'),
                    tags=f"keypoint_{idx}"
                )
                
    def save_state(self):
        """Save current keypoint state for undo/redo"""
        if not self.current_annotation:
            return
        
        # Deep copy current keypoints
        current_keypoints = copy.deepcopy(self.current_annotation.get('keypoints', []))
        
        # Add to undo stack
        self.undo_stack.append(current_keypoints)
        
        # Limit undo stack size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        # Clear redo stack when new action is performed
        self.redo_stack.clear()
    
    def undo_action(self):
        """Undo last keypoint change"""
        if not self.undo_stack or not self.current_annotation:
            self.update_status("Nothing to undo")
            return
        
        # Save current state to redo stack
        current_keypoints = copy.deepcopy(self.current_annotation.get('keypoints', []))
        self.redo_stack.append(current_keypoints)
        
        # Restore previous state
        previous_keypoints = self.undo_stack.pop()
        self.current_annotation['keypoints'] = copy.deepcopy(previous_keypoints)
        
        # Update display
        self.update_keypoint_list()
        self.display_image()
        self.update_status("Undo: Restored previous keypoint state")
    
    def redo_action(self):
        """Redo last undone keypoint change"""
        if not self.redo_stack or not self.current_annotation:
            self.update_status("Nothing to redo")
            return
        
        # Save current state to undo stack
        current_keypoints = copy.deepcopy(self.current_annotation.get('keypoints', []))
        self.undo_stack.append(current_keypoints)
        
        # Restore next state
        next_keypoints = self.redo_stack.pop()
        self.current_annotation['keypoints'] = copy.deepcopy(next_keypoints)
        
        # Update display
        self.update_keypoint_list()
        self.display_image()
        self.update_status("Redo: Restored next keypoint state")
    
    def set_mode(self, mode):
        """Set edit mode and update button appearance"""
        self.edit_mode.set(mode)
        self.update_mode_buttons()
    
    def update_mode_buttons(self):
        """Update button appearance based on current mode"""
        mode = self.edit_mode.get()
        
        # Reset all buttons
        self.move_button.config(relief=tk.RAISED)
        self.add_button.config(relief=tk.RAISED)
        self.delete_button.config(relief=tk.RAISED)
        
        # Highlight active mode button (pressed appearance)
        if mode == "move":
            self.move_button.config(relief=tk.SUNKEN)
        elif mode == "add":
            self.add_button.config(relief=tk.SUNKEN)
        elif mode == "delete":
            self.delete_button.config(relief=tk.SUNKEN)
    
    def on_canvas_click(self, event):
        # Restore focus to canvas for keyboard shortcuts
        self.canvas.focus_set()
        
        if not self.current_annotation:
            return
        
        if self.scale_factor <= 0:
            return
            
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates
        img_x = canvas_x / self.scale_factor
        img_y = canvas_y / self.scale_factor
        
        mode = self.edit_mode.get()
        
        if mode == "move":
            # Find nearest keypoint
            min_dist = float('inf')
            nearest_idx = None
            keypoints = self.current_annotation.get('keypoints', [])
            
            for idx, kp in enumerate(keypoints):
                if len(kp) >= 2:
                    kp_x, kp_y = kp[0], kp[1]
                    dist = math.sqrt((img_x - kp_x)**2 + (img_y - kp_y)**2)
                    if dist < min_dist and dist < 30:  # 30 pixel threshold
                        min_dist = dist
                        nearest_idx = idx
            
            self.selected_keypoint = nearest_idx
            
        elif mode == "add":
            # Save state before adding
            self.save_state()
            # Add new keypoint
            if 'keypoints' not in self.current_annotation:
                self.current_annotation['keypoints'] = []
            self.current_annotation['keypoints'].append([img_x, img_y])
            self.unsaved_changes = True
            self.update_keypoint_list()
            self.update_progress()
            self.display_image()
            
        elif mode == "delete":
            # Delete nearest keypoint
            min_dist = float('inf')
            nearest_idx = None
            keypoints = self.current_annotation.get('keypoints', [])
            
            for idx, kp in enumerate(keypoints):
                if len(kp) >= 2:
                    kp_x, kp_y = kp[0], kp[1]
                    dist = math.sqrt((img_x - kp_x)**2 + (img_y - kp_y)**2)
                    if dist < min_dist and dist < 30:
                        min_dist = dist
                        nearest_idx = idx
                        
            if nearest_idx is not None:
                # Save state before deleting
                self.save_state()
                self.current_annotation['keypoints'].pop(nearest_idx)
                self.selected_keypoint = None
                self.unsaved_changes = True
                self.update_keypoint_list()
                self.update_progress()
                self.display_image()
                
    def on_canvas_drag(self, event):
        if self.selected_keypoint is not None and self.edit_mode.get() == "move":
            if self.scale_factor <= 0:
                return
            
            # Save state on first drag (only once per drag operation)
            if not hasattr(self, '_drag_state_saved'):
                self.save_state()
                self._drag_state_saved = True
            
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            img_x = canvas_x / self.scale_factor
            img_y = canvas_y / self.scale_factor
            
            # Update keypoint
            keypoints = self.current_annotation.get('keypoints', [])
            if self.selected_keypoint < len(keypoints):
                keypoints[self.selected_keypoint] = [img_x, img_y]
                self.unsaved_changes = True
                self.display_image(preserve_zoom=True)
                
    def on_canvas_release(self, event):
        # Clear drag state flag
        if hasattr(self, '_drag_state_saved'):
            delattr(self, '_drag_state_saved')
        self.selected_keypoint = None
        
    def on_mousewheel(self, event):
        # Zoom functionality (Windows uses delta, Linux uses num)
        # Check if Ctrl is pressed (for Ctrl+scroll zoom)
        ctrl_pressed = (event.state & 0x4) != 0 if hasattr(event, 'state') else False
        
        # Zoom on mouse wheel (with or without Ctrl)
        if hasattr(event, 'delta'):
            if event.delta > 0:
                self.zoom_in_at_position(event.x, event.y)
            else:
                self.zoom_out_at_position(event.x, event.y)
        elif event.num == 4:
            self.zoom_in_at_position(event.x, event.y)
        elif event.num == 5:
            self.zoom_out_at_position(event.x, event.y)
            
    def on_canvas_motion(self, event):
        # Display coordinates
        if self.current_image:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            img_x = canvas_x / self.scale_factor if self.scale_factor > 0 else 0
            img_y = canvas_y / self.scale_factor if self.scale_factor > 0 else 0
            
            # Clamp to image bounds
            if self.current_image:
                img_x = max(0, min(img_x, self.current_image.width))
                img_y = max(0, min(img_y, self.current_image.height))
            
            self.coord_label.config(text=f"Image: ({img_x:.1f}, {img_y:.1f})")
            
    def zoom_in_at_position(self, mouse_x, mouse_y):
        """Zoom in centered on mouse position"""
        if not self.current_image:
            return
            
        # Get current mouse position in image coordinates
        canvas_x = self.canvas.canvasx(mouse_x)
        canvas_y = self.canvas.canvasy(mouse_y)
        
        if self.scale_factor < 5.0:  # Max zoom limit
            old_scale = self.scale_factor
            self.scale_factor *= 1.2
            self.zoom_mode = True
            self.display_image(preserve_zoom=True)
            
            # Adjust scroll to keep mouse position centered
            new_canvas_x = canvas_x * (self.scale_factor / old_scale)
            new_canvas_y = canvas_y * (self.scale_factor / old_scale)
            self.canvas.xview_moveto((new_canvas_x - mouse_x) / self.canvas.winfo_width())
            self.canvas.yview_moveto((new_canvas_y - mouse_y) / self.canvas.winfo_height())
    
    def zoom_out_at_position(self, mouse_x, mouse_y):
        """Zoom out centered on mouse position"""
        if not self.current_image:
            return
            
        # Get current mouse position in image coordinates
        canvas_x = self.canvas.canvasx(mouse_x)
        canvas_y = self.canvas.canvasy(mouse_y)
        
        if self.scale_factor > 0.1:  # Min zoom limit
            old_scale = self.scale_factor
            self.scale_factor /= 1.2
            
            # If zooming out below base scale, reset to fit
            if self.scale_factor < self.base_scale_factor:
                self.scale_factor = self.base_scale_factor
                self.zoom_mode = False
            
            self.display_image(preserve_zoom=True)
            
            # Adjust scroll to keep mouse position centered
            if old_scale > 0:
                new_canvas_x = canvas_x * (self.scale_factor / old_scale)
                new_canvas_y = canvas_y * (self.scale_factor / old_scale)
                self.canvas.xview_moveto((new_canvas_x - mouse_x) / self.canvas.winfo_width())
                self.canvas.yview_moveto((new_canvas_y - mouse_y) / self.canvas.winfo_height())
    
    def zoom_in(self):
        """Zoom in at center"""
        if self.current_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.zoom_in_at_position(canvas_width // 2, canvas_height // 2)
            
    def zoom_out(self):
        """Zoom out at center"""
        if self.current_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.zoom_out_at_position(canvas_width // 2, canvas_height // 2)
            
    def fit_image(self):
        # Reset to fit image
        if self.current_image:
            self.zoom_mode = False
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_width, img_height = self.current_image.size
                scale_w = (canvas_width - 40) / img_width
                scale_h = (canvas_height - 40) / img_height
                self.scale_factor = min(scale_w, scale_h, 1.0)
                self.base_scale_factor = self.scale_factor
                self.display_image(preserve_zoom=False)
            
    def on_image_select(self, event):
        selection = self.image_listbox.curselection()
        if selection:
            # Get the image name from listbox
            selected_img = self.image_listbox.get(selection[0])
            # Find its index in the full image list
            if selected_img in self.image_list:
                self.current_image_index = self.image_list.index(selected_img)
            else:
                self.current_image_index = selection[0]
            self.load_current_image()
            
    def on_keypoint_select(self, event):
        selection = self.keypoint_listbox.curselection()
        if selection:
            idx = selection[0]
            keypoints = self.current_annotation.get('keypoints', [])
            if idx < len(keypoints):
                kp = keypoints[idx]
                # Highlight the keypoint
                self.canvas.delete("highlight")
                if len(kp) >= 2:
                    x, y = kp[0] * self.scale_factor, kp[1] * self.scale_factor
                    self.canvas.create_oval(
                        x - 15, y - 15, x + 15, y + 15,
                        outline='yellow', width=3, tags="highlight"
                    )
                    
    def update_keypoint_list(self):
        self.keypoint_listbox.delete(0, tk.END)
        if self.current_annotation:
            keypoints = self.current_annotation.get('keypoints', [])
            for idx, kp in enumerate(keypoints):
                if len(kp) >= 2:
                    label = self.keypoint_names[idx % len(self.keypoint_names)]
                    self.keypoint_listbox.insert(tk.END, f"{label}: ({kp[0]:.1f}, {kp[1]:.1f})")
                    
    def clear_keypoints(self):
        if self.current_annotation:
            # Save state before clearing
            self.save_state()
            self.current_annotation['keypoints'] = []
            self.unsaved_changes = True
            self.update_keypoint_list()
            self.update_progress()
            self.display_image()
    
    def copy_from_previous_frame(self):
        """Copy keypoints from the previous image to the current image"""
        if not self.current_annotation:
            messagebox.showwarning("Warning", "No current annotation to copy to")
            return
        
        if self.current_image_index == 0:
            messagebox.showwarning("Warning", "This is the first image. No previous frame to copy from.")
            return
        
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotation data loaded")
            return
        
        # Get previous image path
        prev_image_path = self.image_list[self.current_image_index - 1]
        prev_full_path = os.path.join(self.image_folder, prev_image_path)
        prev_rel_path = self.get_relative_path(prev_full_path, self.image_folder)
        
        # Find previous annotation using same matching logic
        prev_annotation = None
        
        # Try exact match
        if prev_rel_path and prev_rel_path in self.annotation_dict:
            prev_annotation = self.annotation_dict[prev_rel_path]
        else:
            # Try filename match
            filename = os.path.basename(prev_rel_path) if prev_rel_path else os.path.basename(prev_image_path)
            if filename in self.annotation_dict:
                prev_annotation = self.annotation_dict[filename]
            else:
                # Try path matching
                if prev_rel_path:
                    for ann_path, ann in self.annotation_dict.items():
                        if self.match_annotation_path(prev_rel_path, ann_path):
                            prev_annotation = ann
                            break
        
        if not prev_annotation:
            messagebox.showwarning("Warning", "No annotation found for previous image")
            return
        
        # Get keypoints from previous annotation
        prev_keypoints = prev_annotation.get('keypoints', [])
        if not prev_keypoints:
            messagebox.showinfo("Info", "Previous image has no keypoints to copy")
            return
        
        # Copy keypoints (create a deep copy)
        self.current_annotation['keypoints'] = copy.deepcopy(prev_keypoints)
        self.unsaved_changes = True
        
        # Update display
        self.update_keypoint_list()
        self.update_progress()
        self.display_image()
        self.update_status(f"Copied {len(prev_keypoints)} keypoints from previous frame")
        
        # Restore focus to canvas so keyboard shortcuts continue to work
        self.canvas.focus_set()
            
    def previous_image(self, event=None):
        if self.image_list and self.current_image_index > 0:
            self.current_image_index -= 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_image_index)
            self.image_listbox.see(self.current_image_index)
            self.load_current_image()
            # Restore focus to canvas
            self.canvas.focus_set()
            
    def next_image(self, event=None):
        if self.image_list and self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_image_index)
            self.image_listbox.see(self.current_image_index)
            self.load_current_image()
            # Restore focus to canvas
            self.canvas.focus_set()
            
    def update_image_index_label(self):
        if self.image_list:
            self.image_index_label.config(
                text=f"Image: {self.current_image_index + 1}/{len(self.image_list)}"
            )
            
    def save_annotations(self):
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotations to save")
            return
            
        if self.annotation_file:
            # Save to existing file
            file_path = self.annotation_file
        else:
            # Ask for new file
            file_path = filedialog.asksaveasfilename(
                title="Save Annotations",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
        if file_path:
            try:
                # Update info
                if 'info' in self.annotations_data:
                    self.annotations_data['info']['num_images'] = len(self.annotations_data['annotations'])
                    if self.annotations_data['annotations']:
                        max_kp = max(len(ann.get('keypoints', [])) for ann in self.annotations_data['annotations'])
                        self.annotations_data['info']['num_keypoints'] = max_kp
                
                with open(file_path, 'w') as f:
                    json.dump(self.annotations_data, f, indent=2)
                    
                self.annotation_file = file_path
                self.annotation_label.config(text=os.path.basename(file_path))
                self.unsaved_changes = False
                import time
                self.last_save_time = time.time()
                self.save_indicator.config(text="✓ Saved", foreground="green")
                self.root.after(2000, lambda: self.save_indicator.config(text=""))
                self.update_status(f"Saved annotations to {file_path}")
                self.update_progress()
                messagebox.showinfo("Success", "Annotations saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
                
    def update_path_display(self, image_full_path, annotation_path):
        """Update the path display label with full paths"""
        # Store full paths for tooltip
        self.image_full_path_stored = os.path.abspath(image_full_path) if image_full_path else None
        
        # For annotation path, show the path as stored in JSON
        ann_text = annotation_path if annotation_path else "-"
        ann_full_path = None
        
        # If annotation path is relative and we have annotation file, try to resolve it
        if ann_text != "-" and self.annotation_file and not os.path.isabs(ann_text):
            # Try to construct full path based on annotation file location
            # Common pattern: if annotation is in annotations/ folder, images might be in images/ folder
            ann_file_dir = os.path.dirname(self.annotation_file)
            # Try resolving relative to annotation file's parent directory
            if "annotations" in ann_file_dir:
                # Try images folder at same level
                possible_base = ann_file_dir.replace("annotations", "images")
                possible_full = os.path.join(possible_base, ann_text.replace("/", os.sep))
                if os.path.exists(possible_full):
                    ann_full_path = os.path.abspath(possible_full)
                    ann_text = ann_full_path
                else:
                    # Store the annotation path from JSON
                    ann_full_path = ann_text
                    ann_text = f"{ann_text} (JSON path)"
            else:
                ann_full_path = ann_text
                ann_text = f"{ann_text} (JSON path)"
        elif ann_text != "-" and os.path.isabs(ann_text):
            ann_full_path = os.path.abspath(ann_text)
            ann_text = ann_full_path
        else:
            ann_full_path = None
        
        self.annotation_full_path_stored = ann_full_path
        
        # Get image text for display
        img_text = self.image_full_path_stored if self.image_full_path_stored else "-"
        
        # Truncate very long paths for display (show last part)
        max_len = 80
        if len(img_text) > max_len:
            img_text = "..." + img_text[-max_len:]
        if len(ann_text) > max_len:
            ann_text = "..." + ann_text[-max_len:]
        
        self.path_label.config(text=f"Image: {img_text} | Annotation: {ann_text}")
    
    def show_path_tooltip(self, event):
        """Show full paths in a tooltip"""
        tooltip_text = []
        if self.image_full_path_stored:
            tooltip_text.append(f"Image:\n{self.image_full_path_stored}")
        if self.annotation_full_path_stored:
            tooltip_text.append(f"\nAnnotation:\n{self.annotation_full_path_stored}")
        
        if tooltip_text:
            # Create tooltip window
            x, y = self.root.winfo_pointerxy()
            tooltip = tk.Toplevel(self.root)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x+10}+{y+10}")
            label = tk.Label(tooltip, text="\n".join(tooltip_text), 
                           background="yellow", relief=tk.SOLID, borderwidth=1,
                           font=("Courier", 9), justify=tk.LEFT, padx=5, pady=5)
            label.pack()
            self.path_tooltip = tooltip
    
    def hide_path_tooltip(self, event):
        """Hide the tooltip"""
        if hasattr(self, 'path_tooltip'):
            self.path_tooltip.destroy()
            delattr(self, 'path_tooltip')
    
    def edit_keypoint_names(self):
        """Open dialog to edit keypoint names"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Keypoint Names")
        dialog.geometry("600x700")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Dictionary format input
        dict_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dict_frame, text="Dictionary Format")
        
        ttk.Label(dict_frame, text="Paste or edit dictionary format:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        # Text area for dictionary input
        text_frame = ttk.Frame(dict_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        dict_text = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10), height=20)
        dict_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=dict_text.yview)
        dict_text.configure(yscrollcommand=dict_scrollbar.set)
        
        # Pre-fill with current dictionary format
        dict_content = "KEYPOINT_LABELS = {\n"
        for i, name in enumerate(self.keypoint_names):
            dict_content += f'    {i}: "{name}",\n'
        dict_content = dict_content.rstrip(',\n') + "\n}"
        dict_text.insert('1.0', dict_content)
        
        dict_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dict_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 2: Individual fields
        fields_frame = ttk.Frame(notebook, padding="10")
        notebook.add(fields_frame, text="Individual Fields")
        
        # Scrollable frame for individual fields
        canvas = tk.Canvas(fields_frame)
        scrollbar = ttk.Scrollbar(fields_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Entry fields for each keypoint
        entry_vars = []
        for i in range(len(self.keypoint_names)):
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(row_frame, text=f"KP{i}:", width=8).pack(side=tk.LEFT, padx=5)
            var = tk.StringVar(value=self.keypoint_names[i])
            entry = ttk.Entry(row_frame, textvariable=var, width=30)
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            entry_vars.append(var)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def parse_dictionary(text_content):
            """Parse dictionary format from text"""
            try:
                # Remove KEYPOINT_LABELS = if present
                text_content = text_content.strip()
                if 'KEYPOINT_LABELS' in text_content:
                    # Extract just the dictionary part
                    start = text_content.find('{')
                    end = text_content.rfind('}') + 1
                    if start >= 0 and end > start:
                        text_content = text_content[start:end]
                
                # Use ast.literal_eval for safe parsing
                labels_dict = ast.literal_eval(text_content)
                
                if not isinstance(labels_dict, dict):
                    return False, "Content is not a dictionary"
                
                # Update keypoint names
                updated = False
                for idx, name in labels_dict.items():
                    if isinstance(idx, int) and 0 <= idx < len(self.keypoint_names):
                        if isinstance(name, str):
                            self.keypoint_names[idx] = name
                            updated = True
                
                if not updated:
                    return False, "No valid keypoint labels found in dictionary"
                
                return True, None
            except SyntaxError as e:
                return False, f"Syntax error: {str(e)}"
            except ValueError as e:
                return False, f"Value error: {str(e)}"
            except Exception as e:
                return False, f"Error: {str(e)}"
        
        def save_from_dict():
            """Save names from dictionary format"""
            text_content = dict_text.get('1.0', tk.END)
            success, error = parse_dictionary(text_content)
            
            if success:
                # Update individual fields
                for i, var in enumerate(entry_vars):
                    if i < len(self.keypoint_names):
                        var.set(self.keypoint_names[i])
                
                # Refresh display
                self.update_keypoint_list()
                self.display_image()
                dialog.destroy()
                self.update_status("Keypoint names updated from dictionary")
            else:
                messagebox.showerror("Error", f"Failed to parse dictionary:\n{error}")
        
        def save_from_fields():
            """Save names from individual fields"""
            # Update keypoint names
            for i, var in enumerate(entry_vars):
                name = var.get().strip()
                if name:
                    self.keypoint_names[i] = name
                else:
                    self.keypoint_names[i] = f"KP{i}"
            
            # Update dictionary text
            dict_content = "KEYPOINT_LABELS = {\n"
            for i, name in enumerate(self.keypoint_names):
                dict_content += f'    {i}: "{name}",\n'
            dict_content = dict_content.rstrip(',\n') + "\n}"
            dict_text.delete('1.0', tk.END)
            dict_text.insert('1.0', dict_content)
            
            # Refresh display
            self.update_keypoint_list()
            self.display_image()
            dialog.destroy()
            self.update_status("Keypoint names updated")
        
        def load_from_dict():
            """Load dictionary into individual fields"""
            text_content = dict_text.get('1.0', tk.END)
            success, error = parse_dictionary(text_content)
            
            if success:
                # Update individual fields
                for i, var in enumerate(entry_vars):
                    if i < len(self.keypoint_names):
                        var.set(self.keypoint_names[i])
                messagebox.showinfo("Success", "Dictionary loaded into individual fields")
            else:
                messagebox.showerror("Error", f"Failed to parse dictionary:\n{error}")
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)
        
        # Dictionary tab buttons
        dict_button_frame = ttk.Frame(dict_frame)
        dict_button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(dict_button_frame, text="Load from Dictionary", command=load_from_dict).pack(side=tk.LEFT, padx=5)
        ttk.Button(dict_button_frame, text="Save from Dictionary", command=save_from_dict).pack(side=tk.LEFT, padx=5)
        
        # Fields tab buttons
        fields_button_frame = ttk.Frame(fields_frame)
        fields_button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(fields_button_frame, text="Save", command=save_from_fields).pack(side=tk.LEFT, padx=5)
        
        # Common buttons
        ttk.Button(button_frame, text="Save", command=save_from_fields).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Default", 
                  command=lambda: self.reset_keypoint_names(entry_vars, dict_text)).pack(side=tk.LEFT, padx=5)
    
    def reset_keypoint_names(self, entry_vars, dict_text=None):
        """Reset keypoint names to default"""
        default_names = [
            'KP0', 'KP1', 'KP2', 'KP3', 'KP4', 'KP5', 'KP6', 'KP7', 'KP8',
            'KP9', 'KP10', 'KP11', 'KP12', 'KP13', 'KP14', 'KP15', 'KP16',
            'KP17', 'KP18'
        ]
        for i, var in enumerate(entry_vars):
            if i < len(default_names):
                var.set(default_names[i])
        
        # Update dictionary text if provided
        if dict_text:
            dict_content = "KEYPOINT_LABELS = {\n"
            for i, name in enumerate(default_names):
                dict_content += f'    {i}: "{name}",\n'
            dict_content = dict_content.rstrip(',\n') + "\n}"
            dict_text.delete('1.0', tk.END)
            dict_text.insert('1.0', dict_content)
    
    # ========== Auto-save functionality ==========
    def start_auto_save(self):
        """Start the auto-save timer"""
        if self.auto_save_enabled and self.annotation_file:
            self.check_auto_save()
            self.auto_save_job = self.root.after(self.auto_save_interval * 1000, self.start_auto_save)
    
    def check_auto_save(self):
        """Check if auto-save is needed and perform it"""
        import time
        current_time = time.time()
        
        if self.unsaved_changes and self.annotation_file:
            if current_time - self.last_save_time >= self.auto_save_interval:
                self.auto_save()
    
    def auto_save(self):
        """Perform auto-save without user interaction"""
        if not self.annotations_data or not self.annotation_file:
            return
        
        try:
            with open(self.annotation_file, 'w') as f:
                json.dump(self.annotations_data, f, indent=2)
            self.unsaved_changes = False
            import time
            self.last_save_time = time.time()
            self.save_indicator.config(text="✓ Auto-saved", foreground="green")
            self.root.after(2000, lambda: self.save_indicator.config(text=""))
        except Exception as e:
            print(f"Auto-save failed: {e}")
    
    # ========== Progress tracking ==========
    def update_progress(self):
        """Update progress display"""
        if not self.image_list:
            self.progress_label.config(text="Progress: 0/0 (0%)")
            return
        
        total = len(self.image_list)
        annotated = sum(1 for img in self.image_list 
                       if self.is_image_annotated(img))
        percentage = (annotated / total * 100) if total > 0 else 0
        
        self.progress_label.config(
            text=f"Progress: {annotated}/{total} ({percentage:.1f}%)"
        )
    
    def is_image_annotated(self, image_path):
        """Check if an image has annotations"""
        if not self.annotations_data:
            return False
        
        # Try to find annotation for this image
        image_rel_path = self.get_relative_path(
            os.path.join(self.image_folder, image_path), 
            self.image_folder
        )
        annotation_match_path = self.get_annotation_match_path(
            os.path.join(self.image_folder, image_path),
            self.image_folder
        )
        
        # Check if annotation exists and has keypoints
        for ann_path, ann in self.annotation_dict.items():
            if (ann_path == image_rel_path or 
                ann_path == annotation_match_path or
                os.path.basename(ann_path) == os.path.basename(image_path)):
                keypoints = ann.get('keypoints', [])
                return len(keypoints) > 0
        
        return False
    
    def apply_filter(self):
        """Apply filter to show only unannotated images"""
        self.show_only_unannotated = self.filter_var.get()
        self.refresh_image_list()
    
    def refresh_image_list(self):
        """Refresh image list based on filter"""
        if not self.image_list:
            return
        
        self.image_listbox.delete(0, tk.END)
        
        filtered_list = []
        for img in self.image_list:
            if self.show_only_unannotated:
                if not self.is_image_annotated(img):
                    filtered_list.append(img)
                    self.image_listbox.insert(tk.END, img)
            else:
                filtered_list.append(img)
                self.image_listbox.insert(tk.END, img)
        
        # Update listbox colors to show annotation status
        for i in range(self.image_listbox.size()):
            img = self.image_listbox.get(i)
            if self.is_image_annotated(img):
                self.image_listbox.itemconfig(i, {'bg': '#E8F5E9'})  # Light green
            else:
                self.image_listbox.itemconfig(i, {'bg': '#FFEBEE'})  # Light red
    
    # ========== Enhanced navigation ==========
    def go_to_image(self):
        """Open dialog to jump to specific image"""
        if not self.image_list:
            messagebox.showinfo("Info", "No images loaded")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Go to Image")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"Enter image number (1-{len(self.image_list)}):").pack(pady=5)
        
        entry_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=entry_var, width=20)
        entry.pack(pady=5)
        entry.focus()
        
        def jump():
            try:
                num = int(entry_var.get())
                if 1 <= num <= len(self.image_list):
                    self.current_image_index = num - 1
                    self.image_listbox.selection_clear(0, tk.END)
                    self.image_listbox.selection_set(self.current_image_index)
                    self.image_listbox.see(self.current_image_index)
                    self.load_current_image()
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", f"Number must be between 1 and {len(self.image_list)}")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Go", command=jump).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", lambda e: jump())
    
    # ========== Batch operations ==========
    def batch_copy_keypoints(self):
        """Copy keypoints to next N frames"""
        if not self.current_annotation:
            messagebox.showwarning("Warning", "No keypoints to copy")
            return
        
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotation data loaded")
            return
        
        current_keypoints = self.current_annotation.get('keypoints', [])
        if not current_keypoints:
            messagebox.showwarning("Warning", "Current image has no keypoints")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Batch Copy Keypoints")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"Copy to next N frames (max {len(self.image_list) - self.current_image_index - 1}):").pack(pady=5)
        
        entry_var = tk.StringVar(value="10")
        entry = ttk.Entry(frame, textvariable=entry_var, width=20)
        entry.pack(pady=5)
        entry.focus()
        
        def copy_batch():
            try:
                n = int(entry_var.get())
                max_frames = len(self.image_list) - self.current_image_index - 1
                if n <= 0:
                    messagebox.showerror("Error", "Number must be greater than 0")
                    return
                if n > max_frames:
                    n = max_frames
                
                copied = 0
                for i in range(1, n + 1):
                    idx = self.current_image_index + i
                    if idx >= len(self.image_list):
                        break
                    
                    # Get image path and find/create annotation
                    img_path = self.image_list[idx]
                    full_path = os.path.join(self.image_folder, img_path)
                    image_rel_path = self.get_relative_path(full_path, self.image_folder)
                    annotation_match_path = self.get_annotation_match_path(full_path, self.image_folder)
                    
                    # Find or create annotation
                    ann = None
                    if annotation_match_path and annotation_match_path in self.annotation_dict:
                        ann = self.annotation_dict[annotation_match_path]
                    elif image_rel_path and image_rel_path in self.annotation_dict:
                        ann = self.annotation_dict[image_rel_path]
                    else:
                        # Create new annotation
                        ann = {
                            'image': annotation_match_path if annotation_match_path else image_rel_path,
                            'width': self.current_image.width if self.current_image else 1280,
                            'height': self.current_image.height if self.current_image else 720,
                            'keypoints': []
                        }
                        if 'annotations' not in self.annotations_data:
                            self.annotations_data['annotations'] = []
                        self.annotations_data['annotations'].append(ann)
                        if annotation_match_path:
                            self.annotation_dict[annotation_match_path] = ann
                        if image_rel_path:
                            self.annotation_dict[image_rel_path] = ann
                    
                    # Copy keypoints
                    ann['keypoints'] = copy.deepcopy(current_keypoints)
                    copied += 1
                
                self.unsaved_changes = True
                dialog.destroy()
                messagebox.showinfo("Success", f"Copied keypoints to {copied} frame(s)")
                self.update_progress()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Copy", command=copy_batch).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", lambda e: copy_batch())
    
    # ========== Visual improvements ==========
    def toggle_skeleton(self):
        """Toggle skeleton visibility"""
        self.show_skeleton = self.skeleton_var.get()
        self.display_image(preserve_zoom=True)
    
    def toggle_labels(self):
        """Toggle keypoint label visibility"""
        self.show_keypoint_labels = self.labels_var.get()
        self.display_image(preserve_zoom=True)
    
    def update_keypoint_size(self, value=None):
        """Update keypoint size"""
        self.keypoint_radius = int(self.size_var.get())
        self.keypoint_size = self.keypoint_radius
        self.size_label.config(text=str(self.keypoint_radius))
        self.display_image(preserve_zoom=True)
    
    # ========== Export Functions ==========
    def export_to_coco(self):
        """Export annotations to COCO format"""
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotations to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export to COCO Format",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            coco_data = {
                "info": {
                    "description": "Exported from Keypoint Labeler",
                    "version": "1.0",
                    "year": 2024
                },
                "licenses": [],
                "images": [],
                "annotations": [],
                "categories": [{
                    "id": 1,
                    "name": "person",
                    "supercategory": "person",
                    "keypoints": self.keypoint_names,
                    "skeleton": self.skeleton
                }]
            }
            
            image_id_map = {}  # Map image path to image_id
            image_id = 1
            annotation_id = 1
            
            for ann in self.annotations_data.get('annotations', []):
                img_path = ann.get('image', '')
                if not img_path:
                    continue
                
                # Get or create image entry
                if img_path not in image_id_map:
                    image_id_map[img_path] = image_id
                    coco_data["images"].append({
                        "id": image_id,
                        "file_name": img_path,
                        "width": ann.get('width', 0),
                        "height": ann.get('height', 0)
                    })
                    image_id += 1
                
                img_id = image_id_map[img_path]
                keypoints = ann.get('keypoints', [])
                
                # Convert keypoints to COCO format: [x1, y1, v1, x2, y2, v2, ...]
                coco_keypoints = []
                for kp in keypoints:
                    if len(kp) >= 2:
                        x, y = float(kp[0]), float(kp[1])
                        v = int(kp[2]) if len(kp) >= 3 else 2  # visibility: 0=not labeled, 1=occluded, 2=visible
                        coco_keypoints.extend([x, y, v])
                
                if coco_keypoints:
                    # Calculate bounding box from keypoints
                    xs = [kp[0] for kp in keypoints if len(kp) >= 2]
                    ys = [kp[1] for kp in keypoints if len(kp) >= 2]
                    
                    if xs and ys:
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        bbox_width = x_max - x_min
                        bbox_height = y_max - y_min
                        
                        # Add padding
                        padding = 10
                        x_min = max(0, x_min - padding)
                        y_min = max(0, y_min - padding)
                        bbox_width = min(ann.get('width', 0) - x_min, bbox_width + 2 * padding)
                        bbox_height = min(ann.get('height', 0) - y_min, bbox_height + 2 * padding)
                        
                        coco_data["annotations"].append({
                            "id": annotation_id,
                            "image_id": img_id,
                            "category_id": 1,
                            "keypoints": coco_keypoints,
                            "num_keypoints": len(keypoints),
                            "bbox": [x_min, y_min, bbox_width, bbox_height],
                            "area": bbox_width * bbox_height,
                            "iscrowd": 0
                        })
                        annotation_id += 1
            
            with open(file_path, 'w') as f:
                json.dump(coco_data, f, indent=2)
            
            self.update_status(f"Exported {len(coco_data['annotations'])} annotations to COCO format")
            messagebox.showinfo("Success", f"Exported to COCO format!\n\n"
                                          f"Images: {len(coco_data['images'])}\n"
                                          f"Annotations: {len(coco_data['annotations'])}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export to COCO format: {str(e)}")
    
    def export_to_yolo(self):
        """Export annotations to YOLO format (normalized coordinates)"""
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotations to export")
            return
        
        output_dir = filedialog.askdirectory(title="Select Output Directory for YOLO Format")
        if not output_dir:
            return
        
        try:
            # Create labels directory
            labels_dir = os.path.join(output_dir, "labels")
            os.makedirs(labels_dir, exist_ok=True)
            
            exported = 0
            for ann in self.annotations_data.get('annotations', []):
                img_path = ann.get('image', '')
                if not img_path:
                    continue
                
                keypoints = ann.get('keypoints', [])
                if not keypoints:
                    continue
                
                width = ann.get('width', 1)
                height = ann.get('height', 1)
                
                # Get filename without extension
                filename = os.path.splitext(os.path.basename(img_path))[0]
                label_file = os.path.join(labels_dir, f"{filename}.txt")
                
                # YOLO format: class_id x1 y1 x2 y2 x3 y3 ... (normalized 0-1)
                with open(label_file, 'w') as f:
                    line = "0 "  # class_id = 0 for person
                    for kp in keypoints:
                        if len(kp) >= 2:
                            x_norm = kp[0] / width
                            y_norm = kp[1] / height
                            line += f"{x_norm:.6f} {y_norm:.6f} "
                    f.write(line.strip() + "\n")
                    exported += 1
            
            self.update_status(f"Exported {exported} annotations to YOLO format")
            messagebox.showinfo("Success", f"Exported to YOLO format!\n\n"
                                          f"Labels saved to: {labels_dir}\n"
                                          f"Files exported: {exported}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export to YOLO format: {str(e)}")
    
    def export_to_pascal_voc(self):
        """Export annotations to Pascal VOC XML format"""
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotations to export")
            return
        
        output_dir = filedialog.askdirectory(title="Select Output Directory for Pascal VOC Format")
        if not output_dir:
            return
        
        try:
            # Create annotations directory
            annotations_dir = os.path.join(output_dir, "annotations")
            os.makedirs(annotations_dir, exist_ok=True)
            
            exported = 0
            for ann in self.annotations_data.get('annotations', []):
                img_path = ann.get('image', '')
                if not img_path:
                    continue
                
                keypoints = ann.get('keypoints', [])
                if not keypoints:
                    continue
                
                width = ann.get('width', 0)
                height = ann.get('height', 0)
                
                # Get filename without extension
                filename = os.path.splitext(os.path.basename(img_path))[0]
                xml_file = os.path.join(annotations_dir, f"{filename}.xml")
                
                # Create XML content
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<annotation>
    <folder>images</folder>
    <filename>{os.path.basename(img_path)}</filename>
    <path>{img_path}</path>
    <source>
        <database>Keypoint Labeler</database>
    </source>
    <size>
        <width>{width}</width>
        <height>{height}</height>
        <depth>3</depth>
    </size>
    <segmented>0</segmented>
    <object>
        <name>person</name>
        <pose>Unspecified</pose>
        <truncated>0</truncated>
        <difficult>0</difficult>
        <keypoints>
"""
                
                for idx, kp in enumerate(keypoints):
                    if len(kp) >= 2:
                        kp_name = self.keypoint_names[idx % len(self.keypoint_names)]
                        x, y = float(kp[0]), float(kp[1])
                        v = int(kp[2]) if len(kp) >= 3 else 2
                        visibility = "visible" if v == 2 else ("occluded" if v == 1 else "not_labeled")
                        xml_content += f"            <keypoint name=\"{kp_name}\" x=\"{x:.2f}\" y=\"{y:.2f}\" visibility=\"{visibility}\"/>\n"
                
                xml_content += """        </keypoints>
    </object>
</annotation>"""
                
                with open(xml_file, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                exported += 1
            
            self.update_status(f"Exported {exported} annotations to Pascal VOC format")
            messagebox.showinfo("Success", f"Exported to Pascal VOC format!\n\n"
                                          f"XML files saved to: {annotations_dir}\n"
                                          f"Files exported: {exported}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export to Pascal VOC format: {str(e)}")
    
    def export_statistics(self):
        """Export statistics report"""
        if not self.annotations_data:
            messagebox.showwarning("Warning", "No annotations to analyze")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Statistics Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            annotations = self.annotations_data.get('annotations', [])
            total_images = len(annotations)
            
            # Calculate statistics
            annotated_count = sum(1 for ann in annotations if len(ann.get('keypoints', [])) > 0)
            unannotated_count = total_images - annotated_count
            
            keypoint_counts = [len(ann.get('keypoints', [])) for ann in annotations if len(ann.get('keypoints', [])) > 0]
            avg_keypoints = sum(keypoint_counts) / len(keypoint_counts) if keypoint_counts else 0
            max_keypoints = max(keypoint_counts) if keypoint_counts else 0
            min_keypoints = min(keypoint_counts) if keypoint_counts else 0
            
            # Keypoint distribution
            kp_distribution = {}
            for ann in annotations:
                kp_count = len(ann.get('keypoints', []))
                kp_distribution[kp_count] = kp_distribution.get(kp_count, 0) + 1
            
            # Image dimensions
            widths = [ann.get('width', 0) for ann in annotations if ann.get('width', 0) > 0]
            heights = [ann.get('height', 0) for ann in annotations if ann.get('height', 0) > 0]
            avg_width = sum(widths) / len(widths) if widths else 0
            avg_height = sum(heights) / len(heights) if heights else 0
            
            # Generate report
            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append("KEYPOINT ANNOTATION STATISTICS REPORT")
            report_lines.append("=" * 60)
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"Source File: {os.path.basename(self.annotation_file) if self.annotation_file else 'Unknown'}")
            report_lines.append("")
            
            report_lines.append("OVERVIEW")
            report_lines.append("-" * 60)
            report_lines.append(f"Total Images: {total_images}")
            report_lines.append(f"Annotated Images: {annotated_count} ({annotated_count/total_images*100:.1f}%)")
            report_lines.append(f"Unannotated Images: {unannotated_count} ({unannotated_count/total_images*100:.1f}%)")
            report_lines.append("")
            
            if keypoint_counts:
                report_lines.append("KEYPOINT STATISTICS")
                report_lines.append("-" * 60)
                report_lines.append(f"Average Keypoints per Image: {avg_keypoints:.2f}")
                report_lines.append(f"Maximum Keypoints: {max_keypoints}")
                report_lines.append(f"Minimum Keypoints: {min_keypoints}")
                report_lines.append(f"Total Keypoints: {sum(keypoint_counts)}")
                report_lines.append("")
                
                report_lines.append("KEYPOINT DISTRIBUTION")
                report_lines.append("-" * 60)
                for kp_count in sorted(kp_distribution.keys()):
                    count = kp_distribution[kp_count]
                    percentage = count / annotated_count * 100 if annotated_count > 0 else 0
                    report_lines.append(f"  {kp_count} keypoints: {count} images ({percentage:.1f}%)")
                report_lines.append("")
            
            if widths and heights:
                report_lines.append("IMAGE DIMENSIONS")
                report_lines.append("-" * 60)
                report_lines.append(f"Average Width: {avg_width:.0f}px")
                report_lines.append(f"Average Height: {avg_height:.0f}px")
                report_lines.append(f"Unique Widths: {len(set(widths))}")
                report_lines.append(f"Unique Heights: {len(set(heights))}")
                report_lines.append("")
            
            report_lines.append("KEYPOINT NAMES")
            report_lines.append("-" * 60)
            for idx, name in enumerate(self.keypoint_names):
                report_lines.append(f"  {idx}: {name}")
            report_lines.append("")
            
            report_lines.append("SKELETON CONNECTIONS")
            report_lines.append("-" * 60)
            for connection in self.skeleton:
                idx1, idx2 = connection
                name1 = self.keypoint_names[idx1 % len(self.keypoint_names)]
                name2 = self.keypoint_names[idx2 % len(self.keypoint_names)]
                report_lines.append(f"  {name1} <-> {name2}")
            report_lines.append("")
            
            report_lines.append("=" * 60)
            
            # Write report
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            self.update_status(f"Exported statistics report to {file_path}")
            messagebox.showinfo("Success", f"Statistics report exported!\n\nFile: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export statistics: {str(e)}")
    
    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.after(5000, lambda: self.status_bar.config(text="Ready"))


def main():
    root = tk.Tk()
    app = KeypointLabeler(root)
    root.mainloop()


if __name__ == "__main__":
    main()

