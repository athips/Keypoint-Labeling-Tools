"""
Dual Keypoint Labeling Tool
A GUI application for labeling and editing keypoints on two images simultaneously (e.g., FO/DL).
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


class DualKeypointLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Keypoint Labeler (FO/DL)")
        self.root.geometry("1800x1000")
        
        # Data storage for both views
        self.image_folders = {"left": None, "right": None}  # FO and DL folders
        self.annotation_files = {"left": None, "right": None}
        self.coco_annotation_files = {"left": None, "right": None}
        self.annotations_data = {"left": None, "right": None}
        self.annotation_dicts = {"left": {}, "right": {}}
        self.current_image_indices = {"left": 0, "right": 0}
        self.image_lists = {"left": [], "right": []}
        self.current_annotations = {"left": None, "right": None}
        self.current_image_paths = {"left": None, "right": None}
        self.current_images = {"left": None, "right": None}
        self.photo_images = {"left": None, "right": None}
        self.scale_factors = {"left": 1.0, "right": 1.0}
        self.base_scale_factors = {"left": 1.0, "right": 1.0}
        self.zoom_modes = {"left": False, "right": False}
        
        # Active side (which side is currently being edited)
        self.active_side = "left"  # "left" or "right"
        
        # Keypoint editing state
        self.selected_keypoints = {"left": None, "right": None}
        self.keypoint_radius = 8
        
        # Undo/Redo system for both sides
        self.undo_stacks = {"left": [], "right": []}
        self.redo_stacks = {"left": [], "right": []}
        self.max_history = 50
        
        # Auto-save system
        self.auto_save_enabled = True
        self.auto_save_interval = 30
        self.last_save_times = {"left": 0, "right": 0}
        self.unsaved_changes = {"left": False, "right": False}
        self.auto_save_job = None
        
        # Progress tracking
        self.annotation_status = {"left": {}, "right": {}}
        self.show_only_unannotated = False
        
        # Format mode (COCO vs Standard)
        self.format_mode = "standard"
        self.default_visibility = 2
        
        # Edit mode (move/add/delete) - initialize early
        self.edit_mode = tk.StringVar(value="move")
        
        # Image synchronization
        self.sync_navigation = False  # Sync both sides when navigating
        self.match_by_filename = False  # Match frames by filename
        
        # Performance optimization
        self._last_redraw_time = {"left": 0, "right": 0}
        self._redraw_throttle_ms = 50  # Throttle redraws to every 50ms
        self._image_cache = {"left": None, "right": None}  # Cache resized images
        
        # Clipboard for coordinates
        self._clipboard_coords = None
        
        # Settings persistence
        self.settings_file = os.path.join(os.path.expanduser("~"), ".dual_keypoint_labeler_settings.json")
        self.load_settings()
        
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
            'head', 'l_ear', 'r_ear', 'l_shoulder', 'r_shoulder',
            'l_elbow', 'r_elbow', 'l_wrist', 'r_wrist',
            'l_hip', 'r_hip', 'l_knee', 'r_knee', 'l_foot', 'r_foot',
            'club_grip', 'hand', 'club_shaft', 'club_hosel'
        ]
        
        # Skeleton connections
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
        # Configure root window with professional styling
        self.root.config(bg='#FFFFFF')
        
        # Header bar - professional top bar
        header_frame = tk.Frame(self.root, bg='#F8F9FA', height=50, relief=tk.FLAT, bd=0)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # App title in header
        title_label = tk.Label(header_frame, text="Dual Keypoint Labeler", 
                              font=('Segoe UI', 14, 'bold'), 
                              bg='#F8F9FA', fg='#212529', anchor='w')
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Utility buttons in header (Settings, Export)
        header_btn_frame = tk.Frame(header_frame, bg='#F8F9FA')
        header_btn_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        settings_btn = tk.Button(header_btn_frame, text="Settings", 
                                font=('Segoe UI', 9), bg='#FFFFFF', fg='#495057',
                                activebackground='#E9ECEF', activeforeground='#212529',
                                relief=tk.FLAT, bd=1, padx=12, pady=6, cursor='hand2',
                                command=self.edit_keypoint_names)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
        # Export button with dropdown menu
        export_menu_btn = tk.Menubutton(header_btn_frame, text="Export", 
                                        font=('Segoe UI', 9), bg='#FFFFFF', fg='#495057',
                                        activebackground='#E9ECEF', activeforeground='#212529',
                                        relief=tk.FLAT, bd=1, padx=12, pady=6, cursor='hand2',
                                        direction='below')
        export_menu_btn.pack(side=tk.LEFT, padx=5)
        
        export_dropdown = tk.Menu(export_menu_btn, tearoff=0)
        export_menu_btn.config(menu=export_dropdown)
        export_dropdown.add_command(label="Export Left to COCO...", command=lambda: self.export_to_coco("left"))
        export_dropdown.add_command(label="Export Right to COCO...", command=lambda: self.export_to_coco("right"))
        export_dropdown.add_separator()
        export_dropdown.add_command(label="Export Statistics...", command=self.export_statistics)
        
        # Menu bar (hidden, accessible via header)
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Edit Keypoint Names...", command=self.edit_keypoint_names)
        
        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Export Left to COCO Format...", command=lambda: self.export_to_coco("left"))
        export_menu.add_command(label="Export Right to COCO Format...", command=lambda: self.export_to_coco("right"))
        export_menu.add_separator()
        export_menu.add_command(label="Export Statistics...", command=self.export_statistics)
        export_menu.add_separator()
        export_menu.add_command(label="Export Left to YOLO Format...", command=lambda: self.export_to_yolo("left"))
        export_menu.add_command(label="Export Right to YOLO Format...", command=lambda: self.export_to_yolo("right"))
        
        # Top frame for file controls - professional styling
        top_frame = tk.Frame(self.root, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        top_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Remove top frame - controls will be in each canvas area
        
        # Main content area - professional layout
        main_frame = tk.Frame(self.root, bg='#FFFFFF')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar - professional sidebar with sections (compact)
        left_panel = tk.Frame(main_frame, width=240, bg='#F8F9FA', relief=tk.FLAT, bd=0)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        # Sidebar scrollable area
        sidebar_scroll = tk.Frame(left_panel, bg='#F8F9FA')
        sidebar_scroll.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Sidebar sections - professional styling (compact)
        section_style = {
            'font': ('Segoe UI', 7, 'bold'),
            'bg': '#F8F9FA',
            'fg': '#6C757D',
            'anchor': 'w'
        }
        
        # Reduce sidebar width for more compact layout
        left_panel.config(width=240)
        
        # Active Side Section
        side_section_label = tk.Label(sidebar_scroll, text="ACTIVE SIDE", **section_style)
        side_section_label.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        side_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        side_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.active_side_var = tk.StringVar(value="left")
        tk.Radiobutton(side_frame, text="Left (FO)", 
                      variable=self.active_side_var, value="left",
                      command=self.on_active_side_change,
                      font=('Segoe UI', 8), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(anchor=tk.W, padx=12, pady=6)
        tk.Radiobutton(side_frame, text="Right (DL)", 
                      variable=self.active_side_var, value="right",
                      command=self.on_active_side_change,
                      font=('Segoe UI', 8), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(anchor=tk.W, padx=12, pady=(0, 6))
        
        # Navigation Section - compact
        nav_section_label = tk.Label(sidebar_scroll, text="NAVIGATION", **section_style)
        nav_section_label.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        nav_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        nav_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        # Professional button style
        # Navigation buttons - compact, same line with icons
        nav_btn_row = tk.Frame(nav_frame, bg='#FFFFFF')
        nav_btn_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        nav_btn_style = {
            'font': ('Segoe UI', 9),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 8,
            'pady': 6,
            'bd': 0,
            'bg': '#212529',
            'fg': '#FFFFFF',
            'activebackground': '#495057',
            'activeforeground': '#FFFFFF'
        }
        
        prev_btn = tk.Button(nav_btn_row, text="◄ Prev", 
                            command=self.previous_image,
                            **nav_btn_style)
        prev_btn.pack(side=tk.LEFT, expand=True, padx=2, ipady=4)
        
        next_btn = tk.Button(nav_btn_row, text="Next ►", 
                            command=self.next_image,
                            **nav_btn_style)
        next_btn.pack(side=tk.LEFT, expand=True, padx=2, ipady=4)
        
        # Fast navigation buttons - icon only, smaller
        fast_nav_frame = tk.Frame(nav_frame, bg='#FFFFFF')
        fast_nav_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        fast_btn_style = {
            'font': ('Segoe UI', 10),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 6,
            'pady': 4,
            'bd': 0,
            'bg': '#E9ECEF',
            'fg': '#212529',
            'activebackground': '#DEE2E6',
            'activeforeground': '#212529',
            'width': 3
        }
        
        first_btn = tk.Button(fast_nav_frame, text="◄◄", 
                             command=lambda: self.jump_to_image(0),
                             **fast_btn_style)
        first_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=2)
        
        prev_fast_btn = tk.Button(fast_nav_frame, text="◄", 
                                 command=self.previous_image,
                                 **fast_btn_style)
        prev_fast_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=2)
        
        next_fast_btn = tk.Button(fast_nav_frame, text="►", 
                                 command=self.next_image,
                                 **fast_btn_style)
        next_fast_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=2)
        
        last_btn = tk.Button(fast_nav_frame, text="►►", 
                            command=lambda: self.jump_to_image(-1),
                            **fast_btn_style)
        last_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=2)
        
        # Index and progress info
        info_frame = tk.Frame(nav_frame, bg='#F8F9FA')
        info_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        
        self.image_index_labels = {
            "left": tk.Label(info_frame, text="Left: 0/0", 
                            font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w'),
            "right": tk.Label(info_frame, text="Right: 0/0", 
                             font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w')
        }
        self.image_index_labels["left"].pack(fill=tk.X, pady=4)
        self.image_index_labels["right"].pack(fill=tk.X, pady=2)
        
        self.progress_labels = {
            "left": tk.Label(info_frame, text="Progress: 0/0 (0%)", 
                            font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w'),
            "right": tk.Label(info_frame, text="Progress: 0/0 (0%)", 
                             font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w')
        }
        self.progress_labels["left"].pack(fill=tk.X, pady=2)
        self.progress_labels["right"].pack(fill=tk.X, pady=2)
        
        # Edit Mode Section - compact
        mode_section_label = tk.Label(sidebar_scroll, text="EDIT MODE", **section_style)
        mode_section_label.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        mode_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        mode_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        mode_button_frame = tk.Frame(mode_frame, bg='#FFFFFF')
        mode_button_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # Professional mode button style - readable size
        mode_btn_style = {
            'font': ('Segoe UI', 9),
            'relief': tk.FLAT,
            'bd': 0,
            'padx': 6,
            'pady': 5,
            'cursor': 'hand2'
        }
        
        self.move_button = tk.Button(mode_button_frame, text="⇄ Move", 
                                     command=lambda: self.set_mode("move"),
                                     bg='#212529', fg='#FFFFFF',
                                     activebackground='#495057', activeforeground='#FFFFFF',
                                     **mode_btn_style)
        self.move_button.pack(side=tk.LEFT, expand=True, padx=1, ipady=3)
        
        self.add_button = tk.Button(mode_button_frame, text="+ Add", 
                                    command=lambda: self.set_mode("add"),
                                    bg='#FFFFFF', fg='#212529',
                                    activebackground='#F8F9FA', activeforeground='#212529',
                                    **mode_btn_style)
        self.add_button.pack(side=tk.LEFT, expand=True, padx=1, ipady=3)
        
        self.delete_button = tk.Button(mode_button_frame, text="Delete", 
                                       command=lambda: self.set_mode("delete"),
                                       bg='#FFFFFF', fg='#212529',
                                       activebackground='#F8F9FA', activeforeground='#212529',
                                       **mode_btn_style)
        self.delete_button.pack(side=tk.LEFT, expand=True, padx=1, ipady=3)
        
        # Update button appearance
        self.update_mode_buttons()
        
        # Format Mode Section - compact
        format_section_label = tk.Label(sidebar_scroll, text="FORMAT MODE", **section_style)
        format_section_label.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        format_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        format_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        self.format_mode_var = tk.StringVar(value="standard")
        format_button_frame = tk.Frame(format_frame, bg='#FFFFFF')
        format_button_frame.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Radiobutton(format_button_frame, text="Standard", 
                      variable=self.format_mode_var, value="standard",
                      command=self.on_format_mode_change,
                      font=('Segoe UI', 9), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(side=tk.LEFT, expand=True)
        tk.Radiobutton(format_button_frame, text="COCO", 
                      variable=self.format_mode_var, value="coco",
                      command=self.on_format_mode_change,
                      font=('Segoe UI', 9), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(side=tk.LEFT, expand=True)
        
        # Visibility controls (COCO mode) - vertical list for clarity
        self.visibility_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        
        visibility_section_label = tk.Label(self.visibility_frame, text="VISIBILITY (COCO)", **section_style)
        visibility_section_label.pack(fill=tk.X, padx=15, pady=(12, 8))
        
        visibility_button_frame = tk.Frame(self.visibility_frame, bg='#FFFFFF')
        visibility_button_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.visibility_var = tk.IntVar(value=2)
        # Vertical layout with clear labels
        vis_options = [
            ("v=2: Visible", 2),
            ("v=1: Occluded", 1),
            ("v=0: Not Labeled", 0)
        ]
        
        for text, value in vis_options:
            rb = tk.Radiobutton(visibility_button_frame, text=text, 
                              variable=self.visibility_var, value=value,
                              font=('Segoe UI', 9), bg='#FFFFFF', fg='#212529',
                              activebackground='#F8F9FA', activeforeground='#212529',
                              selectcolor='#FFFFFF', anchor='w')
            rb.pack(fill=tk.X, pady=3)
        
        # Actions Section - compact
        actions_section_label = tk.Label(sidebar_scroll, text="ACTIONS", **section_style)
        actions_section_label.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        actions_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        actions_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        # Undo/Redo buttons - smaller
        undo_redo_frame = tk.Frame(actions_frame, bg='#FFFFFF')
        undo_redo_frame.pack(fill=tk.X, padx=10, pady=8)
        
        secondary_btn_style = {
            'font': ('Segoe UI', 9),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 6,
            'pady': 4,
            'bd': 0,
            'bg': '#FFFFFF',
            'fg': '#212529',
            'activebackground': '#F8F9FA',
            'activeforeground': '#212529'
        }
        
        undo_btn = tk.Button(undo_redo_frame, text="Undo (Ctrl+Z)", 
                            command=self.undo_action, **secondary_btn_style)
        undo_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=3)
        
        redo_btn = tk.Button(undo_redo_frame, text="Redo (Ctrl+Y)", 
                            command=self.redo_action, **secondary_btn_style)
        redo_btn.pack(side=tk.LEFT, expand=True, padx=1, ipady=3)
        
        # Action buttons - readable size
        action_btn_style = {
            'font': ('Segoe UI', 9),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 8,
            'pady': 5,
            'bd': 0
        }
        
        clear_btn = tk.Button(actions_frame, text="Clear All Keypoints", 
                            command=self.clear_keypoints,
                            bg='#FFFFFF', fg='#212529',
                            activebackground='#F8F9FA', activeforeground='#212529',
                            **action_btn_style)
        clear_btn.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=4)
        
        copy_btn = tk.Button(actions_frame, text="Copy Previous (Ctrl+C)", 
                            command=self.copy_from_previous_frame,
                            bg='#212529', fg='#FFFFFF',
                            activebackground='#495057', activeforeground='#FFFFFF',
                            **action_btn_style)
        copy_btn.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=4)
        
        copy_both_btn = tk.Button(actions_frame, text="Copy Both (Ctrl+B)", 
                                 command=self.copy_from_previous_frame_both,
                                 bg='#212529', fg='#FFFFFF',
                                 activebackground='#495057', activeforeground='#FFFFFF',
                                 **action_btn_style)
        copy_both_btn.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=4)
        
        # Visibility Guide Section (COCO mode) - improved readability
        self.visibility_guide_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        
        guide_section_label = tk.Label(self.visibility_guide_frame, text="VISIBILITY GUIDE", **section_style)
        guide_section_label.pack(fill=tk.X, padx=15, pady=(12, 6))
        
        guide_text_frame = tk.Frame(self.visibility_guide_frame, bg='#FFFFFF')
        guide_text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        
        # Use a more readable format with better spacing
        self.visibility_guide_text = tk.Text(guide_text_frame, height=10, width=28,
                                            font=('Segoe UI', 8), wrap=tk.WORD,
                                            state=tk.DISABLED, bg='#F8F9FA', 
                                            relief=tk.FLAT, bd=1,
                                            highlightthickness=1, highlightbackground='#DEE2E6',
                                            fg='#212529', spacing1=2, spacing2=1, spacing3=2,
                                            padx=6, pady=6)
        self.visibility_guide_text.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Set guide content (compact, clear format)
        guide_content = """v=2 (Visible)
Clear: 선명하게 보임
Blurry: 잔상 있으나 위치 특정 가능

v=1 (Occluded)
Severe Blur: 추측해야 함
Occluded: 가려짐

v=0 (Not Labeled)
Out of Frame: 사진 영역 밖"""
        
        self.visibility_guide_text.config(state=tk.NORMAL)
        self.visibility_guide_text.insert('1.0', guide_content)
        self.visibility_guide_text.config(state=tk.DISABLED)
        
        # Visual Settings Section - compact
        visual_section_label = tk.Label(sidebar_scroll, text="VISUAL SETTINGS", **section_style)
        visual_section_label.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        visual_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=1)
        visual_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        self.skeleton_var = tk.BooleanVar(value=True)
        tk.Checkbutton(visual_frame, text="Show Skeleton", 
                      variable=self.skeleton_var,
                      command=self.toggle_skeleton,
                      font=('Segoe UI', 9), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(anchor=tk.W, padx=12, pady=6)
        
        self.labels_var = tk.BooleanVar(value=True)
        tk.Checkbutton(visual_frame, text="Show Keypoint Labels", 
                      variable=self.labels_var,
                      command=self.toggle_labels,
                      font=('Segoe UI', 9), bg='#FFFFFF', fg='#212529',
                      activebackground='#F8F9FA', activeforeground='#212529',
                      selectcolor='#FFFFFF').pack(anchor=tk.W, padx=12, pady=(0, 6))
        
        # Right panel - dual image display (professional styling)
        right_panel = tk.Frame(main_frame, bg='#FFFFFF')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Define button style before using it
        top_btn_style = {
            'font': ('Segoe UI', 9),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 14,
            'pady': 8,
            'bd': 1,
            'bg': '#FFFFFF',
            'fg': '#212529',
            'activebackground': '#E9ECEF',
            'activeforeground': '#212529'
        }
        
        # Create paned window for side-by-side display
        self.image_paned = ttk.PanedWindow(right_panel, orient=tk.HORIZONTAL)
        self.image_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Left image panel (FO)
        self.left_image_frame = tk.Frame(self.image_paned, bg='#FFFFFF')
        self.image_paned.add(self.left_image_frame, weight=1)
        
        # Left controls section - in its own canvas area
        left_controls_panel = tk.Frame(self.left_image_frame, bg='#F8F9FA', relief=tk.FLAT, bd=0)
        left_controls_panel.pack(fill=tk.X, padx=0, pady=0)
        
        self.left_section_label = tk.Label(left_controls_panel, text="LEFT (FO)", 
                                           font=('Segoe UI', 8, 'bold'), 
                                           bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.left_section_label.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        left_btn_frame = tk.Frame(left_controls_panel, bg='#F8F9FA')
        left_btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        left_img_btn = tk.Button(left_btn_frame, text="Select Image Folder", 
                                command=lambda: self.select_image_folder("left"),
                                **top_btn_style)
        left_img_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        left_ann_btn = tk.Button(left_btn_frame, text="Import Annotations", 
                                command=lambda: self.import_annotations("left"),
                                **top_btn_style)
        left_ann_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        save_left_btn = tk.Button(left_btn_frame, text="Save Left", 
                                 command=lambda: self.save_annotations("left"),
                                 **top_btn_style)
        save_left_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # File path labels on same line as buttons
        self.image_folder_labels = {
            "left": tk.Label(left_btn_frame, text="No folder selected", 
                            font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w'),
            "right": tk.Label(left_btn_frame, text="No folder selected", 
                             font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w')
        }
        self.image_folder_labels["left"].pack(side=tk.LEFT, padx=(8, 0))
        
        self.annotation_labels = {
            "left": tk.Label(left_btn_frame, text="No annotation file", 
                           font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w'),
            "right": tk.Label(left_btn_frame, text="No annotation file", 
                            font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D', anchor='w')
        }
        self.annotation_labels["left"].pack(side=tk.LEFT, padx=(8, 0))
        
        # Left navigation label (on top of canvas) - also show file paths
        nav_info_frame = tk.Frame(self.left_image_frame, bg='#F8F9FA')
        nav_info_frame.pack(fill=tk.X, padx=0, pady=0)
        
        self.left_nav_label = tk.Label(nav_info_frame, text="Left: 0/0", 
                                       font=('Segoe UI', 9, 'bold'), 
                                       bg='#F8F9FA', fg='#212529',
                                       relief=tk.FLAT, bd=0, anchor='w', padx=12, pady=6)
        self.left_nav_label.pack(side=tk.LEFT)
        
        # File path labels on top of canvas
        self.left_folder_label_canvas = tk.Label(nav_info_frame, text="", 
                                                 font=('Segoe UI', 8), 
                                                 bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.left_folder_label_canvas.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        
        self.left_annotation_label_canvas = tk.Label(nav_info_frame, text="", 
                                                     font=('Segoe UI', 8), 
                                                     bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.left_annotation_label_canvas.pack(side=tk.LEFT, padx=(8, 0))
        
        # Initialize save indicators
        self.save_indicators = {
            "left": tk.Label(left_btn_frame, text="", font=('Segoe UI', 9), 
                            bg='#F8F9FA', fg='#28A745'),
            "right": None  # Will be set below
        }
        self.save_indicators["left"].pack(side=tk.LEFT, padx=(8, 0))
        
        # Left canvas with scrollbars
        left_canvas_frame = ttk.Frame(self.left_image_frame)
        left_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        left_v_scrollbar = ttk.Scrollbar(left_canvas_frame, orient=tk.VERTICAL)
        left_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        left_h_scrollbar = ttk.Scrollbar(left_canvas_frame, orient=tk.HORIZONTAL)
        left_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvases = {
            "left": tk.Canvas(left_canvas_frame,
                             yscrollcommand=left_v_scrollbar.set,
                             xscrollcommand=left_h_scrollbar.set,
                             bg='gray90')
        }
        self.canvases["left"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        left_v_scrollbar.config(command=self.canvases["left"].yview)
        left_h_scrollbar.config(command=self.canvases["left"].xview)
        
        # Left keypoint list (below canvas) - shows keypoints with coordinates and visibility
        # Split into multiple columns to show all keypoints
        left_kp_list_frame = ttk.LabelFrame(self.left_image_frame, text="Keypoints (Left)", padding="6")
        left_kp_list_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Create frame for multiple columns
        left_kp_columns_frame = ttk.Frame(left_kp_list_frame)
        left_kp_columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create 4 columns for keypoints with better styling
        self.left_kp_listboxes = []
        for col in range(4):
            col_frame = ttk.Frame(left_kp_columns_frame)
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            
            listbox = tk.Listbox(col_frame, height=5, font=('Courier', 8), width=20,
                               bg='white', fg='#212121',
                               selectbackground='#BDBDBD', selectforeground='#000000',
                               relief=tk.SUNKEN, bd=1, highlightthickness=1,
                               highlightbackground='#E0E0E0', highlightcolor='#757575')
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.left_kp_listboxes.append(listbox)
        
        # Left skeleton checkbox
        left_skeleton_frame = ttk.Frame(self.left_image_frame)
        left_skeleton_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        self.left_skeleton_var = tk.BooleanVar(value=True)
        self.left_skeleton_check = ttk.Checkbutton(left_skeleton_frame, text="Show Skeleton (Left)", 
                                                   variable=self.left_skeleton_var,
                                                   command=lambda: self.toggle_skeleton_side("left"))
        self.left_skeleton_check.pack(side=tk.LEFT, padx=5)
        
        # Right image panel (DL)
        self.right_image_frame = tk.Frame(self.image_paned, bg='#FFFFFF')
        self.image_paned.add(self.right_image_frame, weight=1)
        
        # Right controls section - in its own canvas area
        right_controls_panel = tk.Frame(self.right_image_frame, bg='#F8F9FA', relief=tk.FLAT, bd=0)
        right_controls_panel.pack(fill=tk.X, padx=0, pady=0)
        
        self.right_section_label = tk.Label(right_controls_panel, text="RIGHT (DL)", 
                                            font=('Segoe UI', 8, 'bold'), 
                                            bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.right_section_label.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        right_btn_frame = tk.Frame(right_controls_panel, bg='#F8F9FA')
        right_btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        right_img_btn = tk.Button(right_btn_frame, text="Select Image Folder", 
                                 command=lambda: self.select_image_folder("right"),
                                 **top_btn_style)
        right_img_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        right_ann_btn = tk.Button(right_btn_frame, text="Import Annotations", 
                                 command=lambda: self.import_annotations("right"),
                                 **top_btn_style)
        right_ann_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        save_right_btn = tk.Button(right_btn_frame, text="Save Right", 
                                  command=lambda: self.save_annotations("right"),
                                  **top_btn_style)
        save_right_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # File path labels on same line as buttons
        self.image_folder_labels["right"].pack(side=tk.LEFT, padx=(8, 0))
        self.annotation_labels["right"].pack(side=tk.LEFT, padx=(8, 0))
        
        # Initialize right save indicator
        self.save_indicators["right"] = tk.Label(right_btn_frame, text="", font=('Segoe UI', 9), 
                                                 bg='#F8F9FA', fg='#28A745')
        self.save_indicators["right"].pack(side=tk.LEFT, padx=(8, 0))
        
        # Right navigation label (on top of canvas) - also show file paths
        nav_info_frame_right = tk.Frame(self.right_image_frame, bg='#F8F9FA')
        nav_info_frame_right.pack(fill=tk.X, padx=0, pady=0)
        
        self.right_nav_label = tk.Label(nav_info_frame_right, text="Right: 0/0", 
                                       font=('Segoe UI', 9, 'bold'), 
                                       bg='#F8F9FA', fg='#212529',
                                       relief=tk.FLAT, bd=0, anchor='w', padx=12, pady=6)
        self.right_nav_label.pack(side=tk.LEFT)
        
        # File path labels on top of canvas
        self.right_folder_label_canvas = tk.Label(nav_info_frame_right, text="", 
                                                  font=('Segoe UI', 8), 
                                                  bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.right_folder_label_canvas.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        
        self.right_annotation_label_canvas = tk.Label(nav_info_frame_right, text="", 
                                                      font=('Segoe UI', 8), 
                                                      bg='#F8F9FA', fg='#6C757D', anchor='w')
        self.right_annotation_label_canvas.pack(side=tk.LEFT, padx=(8, 0))
        
        # Right canvas with scrollbars
        right_canvas_frame = ttk.Frame(self.right_image_frame)
        right_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        right_v_scrollbar = ttk.Scrollbar(right_canvas_frame, orient=tk.VERTICAL)
        right_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        right_h_scrollbar = ttk.Scrollbar(right_canvas_frame, orient=tk.HORIZONTAL)
        right_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvases["right"] = tk.Canvas(right_canvas_frame,
                                          yscrollcommand=right_v_scrollbar.set,
                                          xscrollcommand=right_h_scrollbar.set,
                                          bg='gray90')
        self.canvases["right"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_v_scrollbar.config(command=self.canvases["right"].yview)
        right_h_scrollbar.config(command=self.canvases["right"].xview)
        
        # Right keypoint list (below canvas) - shows keypoints with coordinates and visibility
        # Split into multiple columns to show all keypoints
        right_kp_list_frame = ttk.LabelFrame(self.right_image_frame, text="Keypoints (Right)", padding="6")
        right_kp_list_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Create frame for multiple columns
        right_kp_columns_frame = ttk.Frame(right_kp_list_frame)
        right_kp_columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create 4 columns for keypoints with better styling
        self.right_kp_listboxes = []
        for col in range(4):
            col_frame = ttk.Frame(right_kp_columns_frame)
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            
            listbox = tk.Listbox(col_frame, height=5, font=('Courier', 8), width=20,
                               bg='white', fg='#212121',
                               selectbackground='#BDBDBD', selectforeground='#000000',
                               relief=tk.SUNKEN, bd=1, highlightthickness=1,
                               highlightbackground='#E0E0E0', highlightcolor='#757575')
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.right_kp_listboxes.append(listbox)
        
        # Right skeleton checkbox
        right_skeleton_frame = ttk.Frame(self.right_image_frame)
        right_skeleton_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        self.right_skeleton_var = tk.BooleanVar(value=True)
        self.right_skeleton_check = ttk.Checkbutton(right_skeleton_frame, text="Show Skeleton (Right)", 
                                                     variable=self.right_skeleton_var,
                                                     command=lambda: self.toggle_skeleton_side("right"))
        self.right_skeleton_check.pack(side=tk.LEFT, padx=5)
        
        # Canvas bindings for both sides
        for side in ["left", "right"]:
            # Bind click to set active side first, then handle keypoint operations
            self.canvases[side].bind("<Button-1>", lambda e, s=side: self.on_canvas_click(e, s))
            self.canvases[side].bind("<B1-Motion>", lambda e, s=side: self.on_canvas_drag(e, s))
            self.canvases[side].bind("<ButtonRelease-1>", lambda e, s=side: self.on_canvas_release(e, s))
            self.canvases[side].bind("<Button-3>", lambda e, s=side: self.on_canvas_right_click(e, s))
            self.canvases[side].bind("<MouseWheel>", lambda e, s=side: self.on_mousewheel(e, s))
            self.canvases[side].bind("<Motion>", lambda e, s=side: self.on_canvas_motion(e, s))
            self.canvases[side].focus_set()
        
        # Initialize active side indication
        self.update_active_side_indication()
        
        # Keyboard shortcuts
        self.root.bind("<Up>", lambda e: self.previous_image())  # Active side only
        self.root.bind("<Down>", lambda e: self.next_image())  # Active side only
        self.root.bind("<Left>", lambda e: self.previous_image_both())  # Both sides together
        self.root.bind("<Right>", lambda e: self.next_image_both())  # Both sides together
        self.root.bind("<Control-c>", lambda e: self.copy_from_previous_frame())
        self.root.bind("<Control-b>", lambda e: self.copy_from_previous_frame_both())
        self.root.bind("<Control-B>", lambda e: self.copy_from_previous_frame_both())
        self.root.bind("<Control-z>", lambda e: self.undo_action())
        self.root.bind("<Control-y>", lambda e: self.redo_action())
        
        # Additional keyboard shortcuts
        self.root.bind("<KeyPress-m>", lambda e: self.set_mode("move"))
        self.root.bind("<KeyPress-M>", lambda e: self.set_mode("move"))
        self.root.bind("<KeyPress-a>", lambda e: self.set_mode("add"))
        self.root.bind("<KeyPress-A>", lambda e: self.set_mode("add"))
        self.root.bind("<KeyPress-d>", lambda e: self.set_mode("delete"))
        self.root.bind("<KeyPress-D>", lambda e: self.set_mode("delete"))
        self.root.bind("<space>", lambda e: self.toggle_skeleton())
        self.root.bind("<Tab>", lambda e: self.switch_active_side())
        self.root.bind("<Escape>", lambda e: self.deselect_keypoint())
        
        # Status bar - professional bottom bar
        status_frame = tk.Frame(self.root, bg='#F8F9FA', height=28, relief=tk.FLAT, bd=0)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        # Divider line
        divider = tk.Frame(status_frame, bg='#DEE2E6', height=1)
        divider.pack(fill=tk.X, side=tk.TOP)
        
        status_content = tk.Frame(status_frame, bg='#F8F9FA')
        status_content.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        self.coord_labels = {
            "left": tk.Label(status_content, text="Left: (0, 0)", 
                           font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D',
                           relief=tk.FLAT, width=25, anchor='w', padx=15),
            "right": tk.Label(status_content, text="Right: (0, 0)", 
                            font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D',
                            relief=tk.FLAT, width=25, anchor='w', padx=15)
        }
        self.coord_labels["left"].pack(side=tk.LEFT)
        self.coord_labels["right"].pack(side=tk.LEFT)
        
        # Status indicator
        status_indicator = tk.Frame(status_content, bg='#28A745', width=8, height=8)
        status_indicator.pack(side=tk.RIGHT, padx=(15, 8), pady=10)
        
        self.status_bar = tk.Label(status_content, text="Ready", 
                                   font=('Segoe UI', 8), bg='#F8F9FA', fg='#6C757D',
                                   relief=tk.FLAT, anchor='e', padx=15)
        self.status_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Add tooltips to buttons
        self.add_tooltips()
        
        # Update status display periodically
        self.update_status_display()
        
        # Start auto-save timer
        if self.auto_save_enabled:
            self.start_auto_save()
        
        # Save window geometry on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def set_active_side(self, side):
        """Set active side (called when clicking on canvas)"""
        if side != self.active_side:
            self.active_side = side
            self.active_side_var.set(side)
            # Update canvas focus
            self.canvases[self.active_side].focus_set()
            # Update visual indication
            self.update_active_side_indication()
            self.update_status(f"Active side: {side.upper()}")
    
    def on_active_side_change(self):
        """Handle active side change from radio buttons"""
        self.active_side = self.active_side_var.get()
        # Update canvas focus
        self.canvases[self.active_side].focus_set()
        # Update visual indication
        self.update_active_side_indication()
        self.update_status(f"Active side: {self.active_side.upper()}")
    
    def update_active_side_indication(self):
        """Update visual indication of active side"""
        # Check if frames exist (may not be created yet during initialization)
        if not hasattr(self, 'left_image_frame') or not hasattr(self, 'right_image_frame'):
            return
        
        # Update section labels to show active side
        if hasattr(self, 'left_section_label') and hasattr(self, 'right_section_label'):
            if self.active_side == "left":
                self.left_section_label.config(text="LEFT (FO) [ACTIVE]", fg='#212529')
                self.right_section_label.config(text="RIGHT (DL)", fg='#6C757D')
            else:
                self.left_section_label.config(text="LEFT (FO)", fg='#6C757D')
                self.right_section_label.config(text="RIGHT (DL) [ACTIVE]", fg='#212529')
        
        # Update navigation labels background to show active side
        if hasattr(self, 'left_nav_label') and hasattr(self, 'right_nav_label'):
            if self.active_side == "left":
                self.left_nav_label.config(bg='#212529', fg='#FFFFFF')
                self.right_nav_label.config(bg='#F8F9FA', fg='#212529')
            else:
                self.left_nav_label.config(bg='#F8F9FA', fg='#212529')
                self.right_nav_label.config(bg='#212529', fg='#FFFFFF')
        
        # Add border highlight to active canvas
        if "left" in self.canvases and "right" in self.canvases:
            if self.active_side == "left":
                self.canvases["left"].config(highlightthickness=2, highlightbackground="#212529")
                self.canvases["right"].config(highlightthickness=1, highlightbackground="#DEE2E6")
            else:
                self.canvases["left"].config(highlightthickness=1, highlightbackground="#DEE2E6")
                self.canvases["right"].config(highlightthickness=2, highlightbackground="#212529")
    
    def select_image_folder(self, side):
        """Select image folder for left or right side"""
        folder = filedialog.askdirectory(title=f"Select {side.upper()} Image Folder")
        if folder:
            self.image_folders[side] = folder
            # Show full path, truncate if too long
            display_path = folder if len(folder) <= 50 else "..." + folder[-47:]
            self.image_folder_labels[side].config(text=f"Folder: {display_path}")
            # Also update canvas label
            if side == "left" and hasattr(self, 'left_folder_label_canvas'):
                self.left_folder_label_canvas.config(text=f"Folder: {display_path}")
            elif side == "right" and hasattr(self, 'right_folder_label_canvas'):
                self.right_folder_label_canvas.config(text=f"Folder: {display_path}")
            self.load_image_list(side)
            self.update_status(f"Loaded {len(self.image_lists[side])} images for {side}")
    
    def load_image_list(self, side):
        """Load image list for a side"""
        if not self.image_folders[side]:
            return
        
        self.image_lists[side] = []
        extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        
        for root, dirs, files in os.walk(self.image_folders[side]):
            for file in files:
                if Path(file).suffix.lower() in extensions:
                    rel_path = os.path.relpath(os.path.join(root, file), self.image_folders[side])
                    self.image_lists[side].append(rel_path)
        
        self.image_lists[side].sort()
        self.update_image_index_label(side)
        self.update_progress(side)
        
        if self.image_lists[side] and self.current_image_indices[side] == 0:
            self.load_current_image(side)
    
    def import_annotations(self, side):
        """Import annotations for a side"""
        file = filedialog.askopenfilename(
            title=f"Import {side.upper()} Annotation File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            try:
                with open(file, 'r') as f:
                    self.annotations_data[side] = json.load(f)
                self.annotation_files[side] = file
                # Show full path, truncate if too long
                display_path = file if len(file) <= 50 else "..." + file[-47:]
                self.annotation_labels[side].config(text=f"Annotation: {display_path}")
                # Also update canvas label
                if side == "left" and hasattr(self, 'left_annotation_label_canvas'):
                    self.left_annotation_label_canvas.config(text=f"Annotation: {display_path}")
                elif side == "right" and hasattr(self, 'right_annotation_label_canvas'):
                    self.right_annotation_label_canvas.config(text=f"Annotation: {display_path}")
                
                # Create annotation lookup dictionary
                self.annotation_dicts[side] = {}
                for ann in self.annotations_data[side].get('annotations', []):
                    ann_path = ann.get('image', '')
                    if ann_path:
                        normalized = self.normalize_path(ann_path)
                        self.annotation_dicts[side][normalized] = ann
                        filename = os.path.basename(normalized)
                        if filename not in self.annotation_dicts[side]:
                            self.annotation_dicts[side][filename] = ann
                
                # Auto-generate COCO file path
                base_path = os.path.splitext(file)[0]
                self.coco_annotation_files[side] = base_path + "_coco.json"
                
                self.update_status(f"Loaded annotations for {len(self.annotations_data[side].get('annotations', []))} images ({side})")
                
                if self.current_image_paths[side]:
                    self.load_current_image(side)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load annotations: {str(e)}")
    
    def normalize_path(self, path):
        """Normalize path to use forward slashes"""
        if path is None:
            return None
        return str(path).replace('\\', '/')
    
    def load_current_image(self, side):
        """Load current image for a side"""
        if not self.image_lists[side] or self.current_image_indices[side] >= len(self.image_lists[side]):
            return
        
        if not self.image_folders[side]:
            return
        
        image_path = self.image_lists[side][self.current_image_indices[side]]
        full_path = os.path.join(self.image_folders[side], image_path)
        
        if not os.path.exists(full_path):
            self.update_status(f"Image not found: {full_path}")
            return
        
        try:
            self.current_image_paths[side] = image_path
            img = Image.open(full_path)
            self.current_images[side] = img.copy()
            
            # Get or create annotation
            image_rel_path = self.get_relative_path(full_path, self.image_folders[side])
            
            if self.annotations_data[side]:
                # Try to find matching annotation
                matched_annotation = None
                if image_rel_path and image_rel_path in self.annotation_dicts[side]:
                    matched_annotation = self.annotation_dicts[side][image_rel_path]
                else:
                    filename = os.path.basename(image_rel_path) if image_rel_path else os.path.basename(image_path)
                    if filename in self.annotation_dicts[side]:
                        matched_annotation = self.annotation_dicts[side][filename]
                
                if matched_annotation:
                    self.current_annotations[side] = matched_annotation
                else:
                    # Create new annotation
                    self.current_annotations[side] = {
                        'image': image_rel_path if image_rel_path else image_path,
                        'width': img.width,
                        'height': img.height,
                        'keypoints': []
                    }
                    if 'annotations' not in self.annotations_data[side]:
                        self.annotations_data[side]['annotations'] = []
                    self.annotations_data[side]['annotations'].append(self.current_annotations[side])
                    if image_rel_path:
                        self.annotation_dicts[side][image_rel_path] = self.current_annotations[side]
            else:
                self.current_annotations[side] = {
                    'image': image_rel_path if image_rel_path else image_path,
                    'width': img.width,
                    'height': img.height,
                    'keypoints': []
                }
            
            # Reset zoom
            self.zoom_modes[side] = False
            self.selected_keypoints[side] = None
            self.undo_stacks[side].clear()
            self.redo_stacks[side].clear()
            
            self.display_image(side)
            self.update_keypoint_list(side)
            self.update_image_index_label(side)
            self.update_progress(side)
            
        except Exception as e:
            error_msg = f"Failed to load image: {str(e)}"
            messagebox.showerror("Error", error_msg)
    
    def get_relative_path(self, full_path, base_folder):
        """Get relative path from base folder"""
        try:
            rel_path = os.path.relpath(full_path, base_folder)
            return self.normalize_path(rel_path)
        except ValueError:
            return None
    
    def find_nearest_keypoint(self, side, img_x, img_y, threshold=30):
        """Find nearest keypoint to given image coordinates"""
        if not self.current_annotations[side]:
            return None
        
        min_dist = float('inf')
        nearest_idx = None
        keypoints = self.current_annotations[side].get('keypoints', [])
        
        for idx, kp in enumerate(keypoints):
            if kp is None or not isinstance(kp, (list, tuple)) or len(kp) < 2:
                continue
            try:
                kp_x, kp_y = float(kp[0]), float(kp[1])
                dist = math.sqrt((img_x - kp_x)**2 + (img_y - kp_y)**2)
                if dist < min_dist and dist < threshold:
                    min_dist = dist
                    nearest_idx = idx
            except (ValueError, TypeError):
                continue
        
        return nearest_idx if min_dist < threshold else None
    
    def display_image(self, side, force=False):
        """Display image for a side with performance throttling"""
        if not self.current_images[side]:
            return
        
        # Throttle redraws for performance
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        if not force and (current_time - self._last_redraw_time[side]) < self._redraw_throttle_ms:
            return
        
        self._last_redraw_time[side] = current_time
        
        canvas = self.canvases[side]
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, lambda: self.display_image(side, force=True))
            return
        
        img = self.current_images[side].copy()
        img_width, img_height = img.size
        
        # Use same scale for both sides to ensure consistent display
        if not self.zoom_modes[side]:
            # Get both canvas sizes
            left_canvas = self.canvases["left"]
            right_canvas = self.canvases["right"]
            left_width = left_canvas.winfo_width()
            left_height = left_canvas.winfo_height()
            right_width = right_canvas.winfo_width()
            right_height = right_canvas.winfo_height()
            
            # Use the smaller canvas dimension to calculate scale (for consistent sizing)
            if left_width > 1 and right_width > 1 and left_height > 1 and right_height > 1:
                min_canvas_width = min(left_width, right_width)
                min_canvas_height = min(left_height, right_height)
            else:
                min_canvas_width = canvas_width
                min_canvas_height = canvas_height
            
            # Calculate scale based on image size and canvas size
            scale_w = (min_canvas_width - 40) / img_width
            scale_h = (min_canvas_height - 40) / img_height
            calculated_scale = min(scale_w, scale_h, 1.0)
            
            # If both images are loaded and same size, use same scale for both
            if (self.current_images["left"] and self.current_images["right"] and
                self.current_images["left"].size == self.current_images["right"].size):
                # Use the same scale for both sides
                self.scale_factors["left"] = calculated_scale
                self.scale_factors["right"] = calculated_scale
                self.base_scale_factors["left"] = calculated_scale
                self.base_scale_factors["right"] = calculated_scale
            else:
                # Independent scaling for different image sizes
                self.scale_factors[side] = calculated_scale
                self.base_scale_factors[side] = calculated_scale
        
        # Check cache before resizing
        cache_key = (img_width, img_height, self.scale_factors[side])
        if (self._image_cache[side] is not None and 
            isinstance(self._image_cache[side], dict) and
            self._image_cache[side].get('key') == cache_key and
            self._image_cache[side].get('image') is not None):
            cached_img = self._image_cache[side]['image']
        else:
            display_width = int(img_width * self.scale_factors[side])
            display_height = int(img_height * self.scale_factors[side])
            
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                try:
                    resample = Image.LANCZOS
                except AttributeError:
                    resample = Image.ANTIALIAS
            
            cached_img = img.resize((display_width, display_height), resample)
            self._image_cache[side] = {'key': cache_key, 'image': cached_img}
        
        self.photo_images[side] = ImageTk.PhotoImage(cached_img)
        
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_images[side])
        canvas.config(scrollregion=canvas.bbox("all"))
        
        self.draw_keypoints(side)
    
    def draw_keypoints(self, side):
        """Draw keypoints for a side"""
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if not keypoints:
            return
        
        canvas = self.canvases[side]
        scale_factor = self.scale_factors[side]
        valid_keypoints = {}
        
        for idx, kp in enumerate(keypoints):
            if kp is None:
                continue
            if not isinstance(kp, (list, tuple)) or len(kp) < 2:
                continue
            
            try:
                x, y = float(kp[0]), float(kp[1])
                if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    continue
                if x < 0 or y < 0:
                    continue
                
                if self.current_images[side]:
                    max_x = self.current_images[side].width * 10
                    max_y = self.current_images[side].height * 10
                    if x > max_x or y > max_y:
                        continue
                
                display_x = x * scale_factor
                display_y = y * scale_factor
                visibility = int(kp[2]) if len(kp) >= 3 else 2
                valid_keypoints[idx] = (display_x, display_y, visibility)
            except (ValueError, TypeError):
                continue
        
        # Draw skeleton (check side-specific setting)
        show_skel = self.left_skeleton_var.get() if side == "left" else self.right_skeleton_var.get()
        if show_skel:
            for connection in self.skeleton:
                idx1, idx2 = connection
                if idx1 in valid_keypoints and idx2 in valid_keypoints:
                    x1, y1 = valid_keypoints[idx1][0], valid_keypoints[idx1][1]
                    x2, y2 = valid_keypoints[idx2][0], valid_keypoints[idx2][1]
                    
                    if connection in [(0, 1), (0, 2)]:
                        line_color = '#FF6B6B'
                    elif connection in [(3, 4), (4, 10), (3, 9), (9, 10)]:
                        line_color = '#4ECDC4'
                    elif connection in [(3, 5), (5, 7), (4, 6), (6, 8)]:
                        line_color = '#45B7D1'
                    elif connection in [(9, 11), (11, 13), (10, 12), (12, 14)]:
                        line_color = '#96CEB4'
                    elif connection in [(15, 16), (16, 17), (17, 18)]:
                        line_color = '#FFEAA7'
                    else:
                        line_color = '#DDA0DD'
                    
                    canvas.create_line(x1, y1, x2, y2, fill=line_color, width=2, tags="skeleton")
        
        # Draw keypoints
        for idx, kp_data in valid_keypoints.items():
            display_x, display_y = kp_data[0], kp_data[1]
            visibility = kp_data[2]
            
            color = self.keypoint_colors[idx % len(self.keypoint_colors)]
            
            if self.format_mode == "coco":
                if visibility == 0:
                    fill_color = '#888888'
                    outline_color = '#666666'
                    outline_width = 1
                elif visibility == 1:
                    fill_color = color
                    outline_color = '#FF0000'
                    outline_width = 2
                else:
                    fill_color = color
                    outline_color = 'black'
                    outline_width = 2
            else:
                fill_color = color
                outline_color = 'black'
                outline_width = 2
            
            # Check if this keypoint is selected (highlight it)
            is_selected = (self.selected_keypoints[side] == idx)
            
            # Highlight selected keypoint
            if is_selected:
                outline_color = '#FFFF00'  # Yellow highlight
                outline_width = 3
                # Draw larger outer circle for selected
                canvas.create_oval(
                    display_x - self.keypoint_radius - 3, display_y - self.keypoint_radius - 3,
                    display_x + self.keypoint_radius + 3, display_y + self.keypoint_radius + 3,
                    outline='#FFFF00', width=2, tags=f"keypoint_{idx}_highlight"
                )
            
            radius = self.keypoint_radius
            canvas.create_oval(
                display_x - radius, display_y - radius,
                display_x + radius, display_y + radius,
                fill=fill_color, outline=outline_color, width=outline_width,
                tags=f"keypoint_{idx}"
            )
            
            if self.show_keypoint_labels:
                label = self.keypoint_names[idx % len(self.keypoint_names)]
                canvas.create_text(
                    display_x, display_y - radius - 10,
                    text=label, fill=color, font=('Arial', 8, 'bold'),
                    tags=f"keypoint_{idx}"
                )
    
    def on_canvas_click(self, event, side):
        """Handle canvas click - both sides work simultaneously"""
        # Set active side for navigation/undo purposes, but allow operations on both sides
        if side != self.active_side:
            self.set_active_side(side)
        
        self.canvases[side].focus_set()
        
        if not self.current_annotations[side]:
            return
        
        if self.scale_factors[side] <= 0:
            return
        
        canvas_x = self.canvases[side].canvasx(event.x)
        canvas_y = self.canvases[side].canvasy(event.y)
        
        img_x = canvas_x / self.scale_factors[side]
        img_y = canvas_y / self.scale_factors[side]
        
        mode = self.edit_mode.get()
        
        if mode == "move":
            nearest_idx = self.find_nearest_keypoint(side, img_x, img_y)
            self.selected_keypoints[side] = nearest_idx
        
        elif mode == "add":
            self.save_state(side)
            if 'keypoints' not in self.current_annotations[side]:
                self.current_annotations[side]['keypoints'] = []
            
            if self.format_mode == "coco":
                visibility = self.visibility_var.get()
                self.current_annotations[side]['keypoints'].append([img_x, img_y, visibility])
            else:
                self.current_annotations[side]['keypoints'].append([img_x, img_y])
            
            self.unsaved_changes[side] = True
            self.display_image(side)
            self.update_keypoint_list(side)
            self.update_progress(side)
        
        elif mode == "delete":
            nearest_idx = self.find_nearest_keypoint(side, img_x, img_y)
            if nearest_idx is not None:
                self.save_state(side)
                self.current_annotations[side]['keypoints'].pop(nearest_idx)
                self.selected_keypoints[side] = None
                self.unsaved_changes[side] = True
                self.display_image(side)
                self.update_keypoint_list(side)
                self.update_progress(side)
    
    def on_canvas_drag(self, event, side):
        """Handle canvas drag - works on the side being dragged"""
        if self.selected_keypoints[side] is not None and self.edit_mode.get() == "move":
            if self.scale_factors[side] <= 0:
                return
            
            if not hasattr(self, '_drag_state_saved'):
                self.save_state(side)
                self._drag_state_saved = True
            
            canvas_x = self.canvases[side].canvasx(event.x)
            canvas_y = self.canvases[side].canvasy(event.y)
            
            img_x = canvas_x / self.scale_factors[side]
            img_y = canvas_y / self.scale_factors[side]
            
            keypoints = self.current_annotations[side].get('keypoints', [])
            if self.selected_keypoints[side] < len(keypoints):
                # Preserve visibility when moving in COCO mode
                old_kp = keypoints[self.selected_keypoints[side]]
                if self.format_mode == "coco" and isinstance(old_kp, (list, tuple)) and len(old_kp) >= 3:
                    # Keep existing visibility
                    keypoints[self.selected_keypoints[side]] = [img_x, img_y, int(old_kp[2])]
                else:
                    # Standard mode or no visibility
                    keypoints[self.selected_keypoints[side]] = [img_x, img_y]
                self.unsaved_changes[side] = True
                # Throttled redraw during drag
                self.display_image(side)
                self.update_keypoint_list(side)
    
    def on_canvas_release(self, event, side):
        """Handle canvas release"""
        if hasattr(self, '_drag_state_saved'):
            delattr(self, '_drag_state_saved')
        self.selected_keypoints[side] = None
    
    def on_canvas_right_click(self, event, side):
        """Handle right-click - show context menu"""
        if self.scale_factors[side] <= 0:
            return
        
        canvas_x = self.canvases[side].canvasx(event.x)
        canvas_y = self.canvases[side].canvasy(event.y)
        
        img_x = canvas_x / self.scale_factors[side]
        img_y = canvas_y / self.scale_factors[side]
        
        # Check if clicking on a keypoint
        nearest_idx = self.find_nearest_keypoint(side, img_x, img_y)
        
        if nearest_idx is not None:
            # Show keypoint context menu
            self.show_keypoint_context_menu(event.x_root, event.y_root, side, nearest_idx)
        else:
            # Show canvas context menu
            self.show_canvas_context_menu(event.x_root, event.y_root, side, img_x, img_y)
    
    def show_keypoint_context_menu(self, x, y, side, keypoint_idx):
        """Show context menu for a keypoint"""
        menu = tk.Menu(self.root, tearoff=0)
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if keypoint_idx < len(keypoints):
            kp = keypoints[keypoint_idx]
            label = self.keypoint_names[keypoint_idx % len(self.keypoint_names)]
            x_coord, y_coord = kp[0], kp[1]
            
            # Keypoint info
            menu.add_command(label=f"{label}: ({x_coord:.1f}, {y_coord:.1f})", state=tk.DISABLED)
            menu.add_separator()
            
            # Visibility options (COCO mode)
            if self.format_mode == "coco":
                current_vis = int(kp[2]) if len(kp) >= 3 else 2
                menu.add_command(
                    label=f"Visible (2) {'✓' if current_vis == 2 else ''}",
                    command=lambda: self.set_keypoint_visibility(side, keypoint_idx, 2)
                )
                menu.add_command(
                    label=f"Occluded (1) {'✓' if current_vis == 1 else ''}",
                    command=lambda: self.set_keypoint_visibility(side, keypoint_idx, 1)
                )
                menu.add_command(
                    label=f"Not Labeled (0) {'✓' if current_vis == 0 else ''}",
                    command=lambda: self.set_keypoint_visibility(side, keypoint_idx, 0)
                )
                menu.add_separator()
            
            # Copy coordinates
            menu.add_command(
                label="Copy Coordinates",
                command=lambda: self.copy_coordinates_to_clipboard(x_coord, y_coord)
            )
            menu.add_separator()
            
            # Delete
            menu.add_command(
                label="Delete Keypoint",
                command=lambda: self.delete_keypoint_at_index(side, keypoint_idx)
            )
        else:
            menu.add_command(label="Invalid keypoint", state=tk.DISABLED)
        
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    
    def show_canvas_context_menu(self, x, y, side, img_x, img_y):
        """Show context menu for canvas (no keypoint clicked)"""
        menu = tk.Menu(self.root, tearoff=0)
        
        # Paste keypoint if clipboard has coordinates
        if hasattr(self, '_clipboard_coords') and self._clipboard_coords:
            menu.add_command(
                label=f"Paste Keypoint ({self._clipboard_coords[0]:.1f}, {self._clipboard_coords[1]:.1f})",
                command=lambda: self.paste_keypoint(side, img_x, img_y)
            )
            menu.add_separator()
        
        # Clear all keypoints
        menu.add_command(
            label="Clear All Keypoints",
            command=lambda: self.clear_keypoints(side)
        )
        
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    
    def set_keypoint_visibility(self, side, keypoint_idx, visibility):
        """Set visibility for a specific keypoint"""
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if keypoint_idx >= len(keypoints):
            return
        
        self.save_state(side)
        
        kp = keypoints[keypoint_idx]
        if kp is None or not isinstance(kp, (list, tuple)) or len(kp) < 2:
            return
        
        if len(kp) >= 3:
            keypoints[keypoint_idx] = [kp[0], kp[1], visibility]
        else:
            keypoints[keypoint_idx] = [kp[0], kp[1], visibility]
        
        self.unsaved_changes[side] = True
        self.update_keypoint_list(side)
        self.display_image(side)
        
        vis_text = {0: "Not Labeled", 1: "Occluded", 2: "Visible"}.get(visibility, "Unknown")
        self.update_status(f"Set {side} keypoint {keypoint_idx} visibility to {visibility} ({vis_text})")
    
    def copy_coordinates_to_clipboard(self, x, y):
        """Copy coordinates to clipboard"""
        self._clipboard_coords = (x, y)
        self.root.clipboard_clear()
        self.root.clipboard_append(f"{x:.1f},{y:.1f}")
        self.update_status(f"Copied coordinates: ({x:.1f}, {y:.1f})")
    
    def paste_keypoint(self, side, img_x, img_y):
        """Paste keypoint at current location"""
        if not hasattr(self, '_clipboard_coords'):
            return
        
        self.save_state(side)
        if 'keypoints' not in self.current_annotations[side]:
            self.current_annotations[side]['keypoints'] = []
        
        if self.format_mode == "coco":
            visibility = self.visibility_var.get()
            self.current_annotations[side]['keypoints'].append([img_x, img_y, visibility])
        else:
            self.current_annotations[side]['keypoints'].append([img_x, img_y])
        
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_progress(side)
    
    def delete_keypoint_at_index(self, side, keypoint_idx):
        """Delete keypoint at specific index"""
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if keypoint_idx >= len(keypoints):
            return
        
        self.save_state(side)
        keypoints.pop(keypoint_idx)
        self.selected_keypoints[side] = None
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_progress(side)
    
    def set_keypoint_visibility(self, side, keypoint_idx, visibility):
        """Set visibility for a keypoint"""
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if keypoint_idx >= len(keypoints):
            return
        
        self.save_state(side)
        
        kp = keypoints[keypoint_idx]
        if kp is None or not isinstance(kp, (list, tuple)) or len(kp) < 2:
            return
        
        if len(kp) >= 3:
            keypoints[keypoint_idx] = [kp[0], kp[1], visibility]
        else:
            keypoints[keypoint_idx] = [kp[0], kp[1], visibility]
        
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_keypoint_list(side)
    
    def on_canvas_motion(self, event, side):
        """Handle canvas motion - show hover info"""
        if self.current_images[side]:
            canvas_x = self.canvases[side].canvasx(event.x)
            canvas_y = self.canvases[side].canvasy(event.y)
            
            img_x = canvas_x / self.scale_factors[side] if self.scale_factors[side] > 0 else 0
            img_y = canvas_y / self.scale_factors[side] if self.scale_factors[side] > 0 else 0
            
            if self.current_images[side]:
                img_x = max(0, min(img_x, self.current_images[side].width))
                img_y = max(0, min(img_y, self.current_images[side].height))
            
            # Check for nearby keypoint
            nearest_idx = self.find_nearest_keypoint(side, img_x, img_y, threshold=20)
            if nearest_idx is not None and self.current_annotations[side]:
                keypoints = self.current_annotations[side].get('keypoints', [])
                if nearest_idx < len(keypoints):
                    kp = keypoints[nearest_idx]
                    label = self.keypoint_names[nearest_idx % len(self.keypoint_names)]
                    if len(kp) >= 3:
                        vis_text = {0: "Not Labeled", 1: "Occluded", 2: "Visible"}.get(int(kp[2]), "?")
                        coord_text = f"{side.upper()}: ({img_x:.1f}, {img_y:.1f}) | {label} (v={kp[2]}, {vis_text})"
                    else:
                        coord_text = f"{side.upper()}: ({img_x:.1f}, {img_y:.1f}) | {label}"
                else:
                    coord_text = f"{side.upper()}: ({img_x:.1f}, {img_y:.1f})"
            else:
                coord_text = f"{side.upper()}: ({img_x:.1f}, {img_y:.1f})"
            
            if hasattr(self, 'coord_labels') and side in self.coord_labels:
                self.coord_labels[side].config(text=coord_text)
            
            # Update status bar with hover info
            if nearest_idx is not None:
                self.update_status_hover(side, nearest_idx)
    
    def on_mousewheel(self, event, side):
        """Handle mouse wheel zoom - works on the side being zoomed"""
        if hasattr(event, 'delta'):
            if event.delta > 0:
                self.zoom_in_at_position(side, event.x, event.y)
            else:
                self.zoom_out_at_position(side, event.x, event.y)
    
    def zoom_in_at_position(self, side, mouse_x, mouse_y):
        """Zoom in at position"""
        if not self.current_images[side]:
            return
        
        canvas = self.canvases[side]
        canvas_x = canvas.canvasx(mouse_x)
        canvas_y = canvas.canvasy(mouse_y)
        
        if self.scale_factors[side] < 5.0:
            old_scale = self.scale_factors[side]
            self.scale_factors[side] *= 1.2
            self.zoom_modes[side] = True
            self.display_image(side)
    
    def zoom_out_at_position(self, side, mouse_x, mouse_y):
        """Zoom out at position"""
        if not self.current_images[side]:
            return
        
        if self.scale_factors[side] > 0.1:
            old_scale = self.scale_factors[side]
            self.scale_factors[side] /= 1.2
            
            if self.scale_factors[side] < self.base_scale_factors[side]:
                self.scale_factors[side] = self.base_scale_factors[side]
                self.zoom_modes[side] = False
            
            self.display_image(side)
    
    def jump_to_image(self, index):
        """Jump to a specific image index (0 for first, -1 for last)"""
        side = self.active_side
        if not self.image_lists[side]:
            return
        
        if index == -1:
            target_index = len(self.image_lists[side]) - 1
        else:
            target_index = max(0, min(index, len(self.image_lists[side]) - 1))
        
        self.current_image_indices[side] = target_index
        self.load_current_image(side)
        self.canvases[side].focus_set()
        self.update_image_index_label(side)
        self.update_status(f"Jumped to image {self.current_image_indices[side] + 1}/{len(self.image_lists[side])}")
    
    def previous_image(self):
        """Navigate to previous image on active side only (Up/Down arrows)"""
        side = self.active_side
        if self.image_lists[side] and self.current_image_indices[side] > 0:
            self.current_image_indices[side] -= 1
            self.load_current_image(side)
            self.canvases[side].focus_set()
    
    def next_image(self):
        """Navigate to next image on active side only (Up/Down arrows)"""
        side = self.active_side
        if self.image_lists[side] and self.current_image_indices[side] < len(self.image_lists[side]) - 1:
            self.current_image_indices[side] += 1
            self.load_current_image(side)
            self.canvases[side].focus_set()
    
    def previous_image_both(self):
        """Navigate to previous image on both sides together (Left arrow)"""
        moved = False
        for side in ["left", "right"]:
            if self.image_lists[side] and self.current_image_indices[side] > 0:
                self.current_image_indices[side] -= 1
                self.load_current_image(side)
                moved = True
        
        if moved:
            # Keep focus on active side
            self.canvases[self.active_side].focus_set()
            self.update_status("Navigated both sides backward")
    
    def next_image_both(self):
        """Navigate to next image on both sides together (Right arrow)"""
        moved = False
        for side in ["left", "right"]:
            if self.image_lists[side] and self.current_image_indices[side] < len(self.image_lists[side]) - 1:
                self.current_image_indices[side] += 1
                self.load_current_image(side)
                moved = True
        
        if moved:
            # Keep focus on active side
            self.canvases[self.active_side].focus_set()
            self.update_status("Navigated both sides forward")
    
    def update_image_index_label(self, side):
        """Update image index label for a side"""
        if self.image_lists[side]:
            index_text = f"{side.upper()}: {self.current_image_indices[side] + 1}/{len(self.image_lists[side])}"
            self.image_index_labels[side].config(text=index_text)
            # Also update navigation label on canvas
            if side == "left":
                self.left_nav_label.config(text=index_text)
            else:
                self.right_nav_label.config(text=index_text)
        else:
            # No images loaded
            if side == "left":
                self.left_nav_label.config(text="Left: 0/0")
            else:
                self.right_nav_label.config(text="Right: 0/0")
    
    def update_progress(self, side):
        """Update progress for a side"""
        if not self.image_lists[side]:
            self.progress_labels[side].config(text=f"Progress: 0/0 (0%)")
            return
        
        total = len(self.image_lists[side])
        annotated = sum(1 for img in self.image_lists[side] 
                       if self.is_image_annotated(side, img))
        percentage = (annotated / total * 100) if total > 0 else 0
        
        self.progress_labels[side].config(
            text=f"Progress: {annotated}/{total} ({percentage:.1f}%)"
        )
    
    def is_image_annotated(self, side, image_path):
        """Check if image has annotations"""
        if not self.annotations_data[side]:
            return False
        
        image_rel_path = self.get_relative_path(
            os.path.join(self.image_folders[side], image_path),
            self.image_folders[side]
        )
        
        for ann_path, ann in self.annotation_dicts[side].items():
            if (ann_path == image_rel_path or
                os.path.basename(ann_path) == os.path.basename(image_path)):
                keypoints = ann.get('keypoints', [])
                return len(keypoints) > 0
        
        return False
    
    def save_state(self, side):
        """Save state for undo/redo"""
        if not self.current_annotations[side]:
            return
        
        current_keypoints = copy.deepcopy(self.current_annotations[side].get('keypoints', []))
        self.undo_stacks[side].append(current_keypoints)
        
        if len(self.undo_stacks[side]) > self.max_history:
            self.undo_stacks[side].pop(0)
        
        self.redo_stacks[side].clear()
    
    def undo_action(self):
        """Undo last action on active side"""
        side = self.active_side
        if not self.undo_stacks[side] or not self.current_annotations[side]:
            self.update_status("Nothing to undo")
            return
        
        current_keypoints = copy.deepcopy(self.current_annotations[side].get('keypoints', []))
        self.redo_stacks[side].append(current_keypoints)
        
        previous_keypoints = self.undo_stacks[side].pop()
        self.current_annotations[side]['keypoints'] = copy.deepcopy(previous_keypoints)
        
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_status("Undo: Restored previous keypoint state")
    
    def redo_action(self):
        """Redo last undone action on active side"""
        side = self.active_side
        if not self.redo_stacks[side] or not self.current_annotations[side]:
            self.update_status("Nothing to redo")
            return
        
        current_keypoints = copy.deepcopy(self.current_annotations[side].get('keypoints', []))
        self.undo_stacks[side].append(current_keypoints)
        
        next_keypoints = self.redo_stacks[side].pop()
        self.current_annotations[side]['keypoints'] = copy.deepcopy(next_keypoints)
        
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_status("Redo: Restored next keypoint state")
    
    def set_mode(self, mode):
        """Set edit mode"""
        self.edit_mode.set(mode)
        self.update_mode_buttons()
    
    def update_mode_buttons(self):
        """Update mode button appearance"""
        mode = self.edit_mode.get()
        
        # Reset all buttons to default state (white)
        self.move_button.config(bg='#FFFFFF', fg='#212529', relief=tk.FLAT)
        self.add_button.config(bg='#FFFFFF', fg='#212529', relief=tk.FLAT)
        self.delete_button.config(bg='#FFFFFF', fg='#212529', relief=tk.FLAT)
        
        # Highlight active button with dark background
        if mode == "move":
            self.move_button.config(bg='#212529', fg='#FFFFFF', relief=tk.FLAT)
        elif mode == "add":
            self.add_button.config(bg='#212529', fg='#FFFFFF', relief=tk.FLAT)
        elif mode == "delete":
            self.delete_button.config(bg='#212529', fg='#FFFFFF', relief=tk.FLAT)
    
    def on_format_mode_change(self):
        """Handle format mode change"""
        old_mode = self.format_mode
        self.format_mode = self.format_mode_var.get()
        
        if self.format_mode == "coco":
            self.visibility_frame.pack(fill=tk.X, padx=20, pady=(0, 20), before=None)
            self.visibility_guide_frame.pack(fill=tk.X, padx=20, pady=(0, 20), before=None)
            
            # Set all keypoints to visible when switching to COCO
            for side in ["left", "right"]:
                if old_mode == "standard" and self.current_annotations[side]:
                    keypoints = self.current_annotations[side].get('keypoints', [])
                    for idx, kp in enumerate(keypoints):
                        if kp is not None and isinstance(kp, (list, tuple)) and len(kp) >= 2:
                            if len(kp) < 3:
                                keypoints[idx] = [kp[0], kp[1], 2]
                            elif len(kp) >= 3:
                                try:
                                    vis = int(kp[2])
                                    if vis not in [0, 1, 2]:
                                        keypoints[idx] = [kp[0], kp[1], 2]
                                except (ValueError, TypeError):
                                    keypoints[idx] = [kp[0], kp[1], 2]
                    self.unsaved_changes[side] = True
                    self.display_image(side)
            
            if self.annotation_files["left"] and not self.coco_annotation_files["left"]:
                base_path = os.path.splitext(self.annotation_files["left"])[0]
                self.coco_annotation_files["left"] = base_path + "_coco.json"
            if self.annotation_files["right"] and not self.coco_annotation_files["right"]:
                base_path = os.path.splitext(self.annotation_files["right"])[0]
                self.coco_annotation_files["right"] = base_path + "_coco.json"
            
            self.update_status("COCO mode enabled")
        else:
            if hasattr(self, 'visibility_frame'):
                self.visibility_frame.pack_forget()
            if hasattr(self, 'visibility_guide_frame'):
                self.visibility_guide_frame.pack_forget()
            self.update_status("Standard mode enabled")
        
        # Update displays
        for side in ["left", "right"]:
            if self.current_images[side]:
                self.display_image(side)
    
    def clear_keypoints(self, side=None):
        """Clear all keypoints on specified side (or active side)"""
        if side is None:
            side = self.active_side
        if self.current_annotations[side]:
            self.save_state(side)
            self.current_annotations[side]['keypoints'] = []
            self.unsaved_changes[side] = True
            self.display_image(side)
            self.update_keypoint_list(side)
            self.update_progress(side)
    
    def copy_from_previous_frame(self):
        """Copy keypoints from previous frame on active side"""
        side = self.active_side
        if not self.current_annotations[side]:
            messagebox.showwarning("Warning", "No current annotation to copy to")
            return
        
        if self.current_image_indices[side] == 0:
            messagebox.showwarning("Warning", "This is the first image. No previous frame to copy from.")
            return
        
        if not self.annotations_data[side]:
            messagebox.showwarning("Warning", "No annotation data loaded")
            return
        
        self.save_state(side)
        
        prev_image_path = self.image_lists[side][self.current_image_indices[side] - 1]
        prev_full_path = os.path.join(self.image_folders[side], prev_image_path)
        prev_rel_path = self.get_relative_path(prev_full_path, self.image_folders[side])
        
        prev_annotation = None
        if prev_rel_path and prev_rel_path in self.annotation_dicts[side]:
            prev_annotation = self.annotation_dicts[side][prev_rel_path]
        else:
            filename = os.path.basename(prev_rel_path) if prev_rel_path else os.path.basename(prev_image_path)
            if filename in self.annotation_dicts[side]:
                prev_annotation = self.annotation_dicts[side][filename]
        
        if not prev_annotation:
            messagebox.showwarning("Warning", "No annotation found for previous image")
            return
        
        prev_keypoints = prev_annotation.get('keypoints', [])
        if not prev_keypoints:
            messagebox.showinfo("Info", "Previous image has no keypoints to copy")
            return
        
        copied_keypoints = copy.deepcopy(prev_keypoints)
        cleaned_keypoints = []
        
        for kp in copied_keypoints:
            if kp is None:
                cleaned_keypoints.append(None)
            elif isinstance(kp, (list, tuple)) and len(kp) >= 2:
                try:
                    x, y = float(kp[0]), float(kp[1])
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        if len(kp) >= 3:
                            cleaned_keypoints.append([x, y, int(kp[2])])
                        elif self.format_mode == "coco":
                            cleaned_keypoints.append([x, y, self.default_visibility])
                        else:
                            cleaned_keypoints.append([x, y])
                    else:
                        cleaned_keypoints.append(None)
                except (ValueError, TypeError):
                    cleaned_keypoints.append(None)
            else:
                cleaned_keypoints.append(None)
        
        self.current_annotations[side]['keypoints'] = cleaned_keypoints
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_progress(side)
        
        valid_count = sum(1 for kp in cleaned_keypoints if kp and len(kp) >= 2)
        self.update_keypoint_list(side)
        self.update_status(f"Copied {valid_count} keypoints from previous frame ({side})")
    
    def copy_from_previous_frame_both(self):
        """Copy keypoints from previous frame on BOTH sides simultaneously"""
        copied_left = False
        copied_right = False
        
        # Copy for left side
        if (self.current_annotations["left"] and 
            self.current_image_indices["left"] > 0 and 
            self.annotations_data["left"]):
            try:
                self.save_state("left")
                prev_image_path = self.image_lists["left"][self.current_image_indices["left"] - 1]
                prev_full_path = os.path.join(self.image_folders["left"], prev_image_path)
                prev_rel_path = self.get_relative_path(prev_full_path, self.image_folders["left"])
                
                prev_annotation = None
                if prev_rel_path and prev_rel_path in self.annotation_dicts["left"]:
                    prev_annotation = self.annotation_dicts["left"][prev_rel_path]
                else:
                    filename = os.path.basename(prev_rel_path) if prev_rel_path else os.path.basename(prev_image_path)
                    if filename in self.annotation_dicts["left"]:
                        prev_annotation = self.annotation_dicts["left"][filename]
                
                if prev_annotation:
                    prev_keypoints = prev_annotation.get('keypoints', [])
                    if prev_keypoints:
                        copied_keypoints = copy.deepcopy(prev_keypoints)
                        cleaned_keypoints = []
                        for kp in copied_keypoints:
                            if kp is None:
                                cleaned_keypoints.append(None)
                            elif isinstance(kp, (list, tuple)) and len(kp) >= 2:
                                try:
                                    x, y = float(kp[0]), float(kp[1])
                                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                        if len(kp) >= 3:
                                            cleaned_keypoints.append([x, y, int(kp[2])])
                                        elif self.format_mode == "coco":
                                            cleaned_keypoints.append([x, y, self.default_visibility])
                                        else:
                                            cleaned_keypoints.append([x, y])
                                    else:
                                        cleaned_keypoints.append(None)
                                except (ValueError, TypeError):
                                    cleaned_keypoints.append(None)
                            else:
                                cleaned_keypoints.append(None)
                        
                        self.current_annotations["left"]['keypoints'] = cleaned_keypoints
                        self.unsaved_changes["left"] = True
                        self.display_image("left")
                        self.update_keypoint_list("left")
                        self.update_progress("left")
                        copied_left = True
            except Exception as e:
                print(f"Error copying left: {e}")
        
        # Copy for right side
        if (self.current_annotations["right"] and 
            self.current_image_indices["right"] > 0 and 
            self.annotations_data["right"]):
            try:
                self.save_state("right")
                prev_image_path = self.image_lists["right"][self.current_image_indices["right"] - 1]
                prev_full_path = os.path.join(self.image_folders["right"], prev_image_path)
                prev_rel_path = self.get_relative_path(prev_full_path, self.image_folders["right"])
                
                prev_annotation = None
                if prev_rel_path and prev_rel_path in self.annotation_dicts["right"]:
                    prev_annotation = self.annotation_dicts["right"][prev_rel_path]
                else:
                    filename = os.path.basename(prev_rel_path) if prev_rel_path else os.path.basename(prev_image_path)
                    if filename in self.annotation_dicts["right"]:
                        prev_annotation = self.annotation_dicts["right"][filename]
                
                if prev_annotation:
                    prev_keypoints = prev_annotation.get('keypoints', [])
                    if prev_keypoints:
                        copied_keypoints = copy.deepcopy(prev_keypoints)
                        cleaned_keypoints = []
                        for kp in copied_keypoints:
                            if kp is None:
                                cleaned_keypoints.append(None)
                            elif isinstance(kp, (list, tuple)) and len(kp) >= 2:
                                try:
                                    x, y = float(kp[0]), float(kp[1])
                                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                        if len(kp) >= 3:
                                            cleaned_keypoints.append([x, y, int(kp[2])])
                                        elif self.format_mode == "coco":
                                            cleaned_keypoints.append([x, y, self.default_visibility])
                                        else:
                                            cleaned_keypoints.append([x, y])
                                    else:
                                        cleaned_keypoints.append(None)
                                except (ValueError, TypeError):
                                    cleaned_keypoints.append(None)
                            else:
                                cleaned_keypoints.append(None)
                        
                        self.current_annotations["right"]['keypoints'] = cleaned_keypoints
                        self.unsaved_changes["right"] = True
                        self.display_image("right")
                        self.update_keypoint_list("right")
                        self.update_progress("right")
                        copied_right = True
            except Exception as e:
                print(f"Error copying right: {e}")
        
        if copied_left and copied_right:
            self.update_status("Copied keypoints from previous frame on both sides")
        elif copied_left:
            self.update_status("Copied keypoints from previous frame (left side only)")
        elif copied_right:
            self.update_status("Copied keypoints from previous frame (right side only)")
        else:
            messagebox.showinfo("Info", "Could not copy from previous frame on either side")
    
    def update_keypoint_list(self, side):
        """Update keypoint list display for a side (split into multiple columns)"""
        if side == "left":
            listboxes = self.left_kp_listboxes
        else:
            listboxes = self.right_kp_listboxes
        
        # Clear all columns
        for listbox in listboxes:
            listbox.delete(0, tk.END)
        
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        valid_keypoints = []
        
        # Collect valid keypoints
        for idx, kp in enumerate(keypoints):
            if kp is None or not isinstance(kp, (list, tuple)) or len(kp) < 2:
                continue
            
            label = self.keypoint_names[idx % len(self.keypoint_names)]
            x, y = kp[0], kp[1]
            
            if self.format_mode == "coco" and len(kp) >= 3:
                visibility = int(kp[2])
                vis_text = {0: "N", 1: "O", 2: "V"}.get(visibility, "?")
                text = f"{label}:({x:.1f},{y:.1f},v={visibility})"
            else:
                text = f"{label}:({x:.1f},{y:.1f})"
            
            valid_keypoints.append((idx, text))
        
        # Distribute keypoints across 4 columns
        num_columns = len(listboxes)
        items_per_column = (len(valid_keypoints) + num_columns - 1) // num_columns  # Ceiling division
        
        for col_idx, listbox in enumerate(listboxes):
            start_idx = col_idx * items_per_column
            end_idx = min(start_idx + items_per_column, len(valid_keypoints))
            
            for i in range(start_idx, end_idx):
                idx, text = valid_keypoints[i]
                listbox.insert(tk.END, text)
    
    def toggle_skeleton(self):
        """Toggle skeleton visibility (from main control)"""
        self.show_skeleton = self.skeleton_var.get()
        # Update individual side checkboxes
        self.left_skeleton_var.set(self.show_skeleton)
        self.right_skeleton_var.set(self.show_skeleton)
        for side in ["left", "right"]:
            if self.current_images[side]:
                self.display_image(side)
    
    def toggle_skeleton_side(self, side):
        """Toggle skeleton visibility for a specific side"""
        if side == "left":
            show_skel = self.left_skeleton_var.get()
        else:
            show_skel = self.right_skeleton_var.get()
        
        # Update display for that side
        if self.current_images[side]:
            self.display_image(side)
    
    def toggle_labels(self):
        """Toggle keypoint label visibility"""
        self.show_keypoint_labels = self.labels_var.get()
        for side in ["left", "right"]:
            if self.current_images[side]:
                self.display_image(side)
    
    def save_annotations(self, side):
        """Save annotations for a side"""
        if not self.annotations_data[side]:
            messagebox.showwarning("Warning", f"No annotations to save ({side})")
            return
        
        if self.format_mode == "coco":
            # Save to both files in COCO mode
            if not self.annotation_files[side]:
                messagebox.showwarning("Warning", f"No standard annotation file loaded ({side})")
                return
            
            if not self.coco_annotation_files[side]:
                base_path = os.path.splitext(self.annotation_files[side])[0]
                self.coco_annotation_files[side] = base_path + "_coco.json"
            
            try:
                if 'info' in self.annotations_data[side]:
                    self.annotations_data[side]['info']['num_images'] = len(self.annotations_data[side]['annotations'])
                    if self.annotations_data[side]['annotations']:
                        max_kp = max(len(ann.get('keypoints', [])) for ann in self.annotations_data[side]['annotations'])
                        self.annotations_data[side]['info']['num_keypoints'] = max_kp
                
                # Save to standard file
                with open(self.annotation_files[side], 'w') as f:
                    json.dump(self.annotations_data[side], f, indent=2)
                
                # Save to COCO file
                with open(self.coco_annotation_files[side], 'w') as f:
                    json.dump(self.annotations_data[side], f, indent=2)
                
                self.unsaved_changes[side] = False
                import time
                self.last_save_times[side] = time.time()
                self.save_indicators[side].config(text="✓ Saved", foreground="green")
                self.root.after(2000, lambda s=side: self.save_indicators[s].config(text=""))
                
                standard_path = self.annotation_files[side]
                coco_path = self.coco_annotation_files[side]
                # Truncate paths if too long
                std_display = standard_path if len(standard_path) <= 40 else "..." + standard_path[-37:]
                coco_display = coco_path if len(coco_path) <= 40 else "..." + coco_path[-37:]
                self.annotation_labels[side].config(text=f"Standard: {std_display} | COCO: {coco_display}")
                # Also update canvas label
                if side == "left" and hasattr(self, 'left_annotation_label_canvas'):
                    self.left_annotation_label_canvas.config(text=f"Standard: {std_display} | COCO: {coco_display}")
                elif side == "right" and hasattr(self, 'right_annotation_label_canvas'):
                    self.right_annotation_label_canvas.config(text=f"Standard: {std_display} | COCO: {coco_display}")
                
                self.update_status(f"Saved {side} to both files: {std_display} and {coco_display}")
                messagebox.showinfo("Success", f"Saved {side} to both files:\nStandard: {std_display}\nCOCO: {coco_display}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
        else:
            # Standard mode: save to standard file only
            if self.annotation_files[side]:
                file_path = self.annotation_files[side]
            else:
                file_path = filedialog.asksaveasfilename(
                    title=f"Save {side.upper()} Annotations",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if not file_path:
                    return
                self.annotation_files[side] = file_path
            
            if file_path:
                try:
                    if 'info' in self.annotations_data[side]:
                        self.annotations_data[side]['info']['num_images'] = len(self.annotations_data[side]['annotations'])
                        if self.annotations_data[side]['annotations']:
                            max_kp = max(len(ann.get('keypoints', [])) for ann in self.annotations_data[side]['annotations'])
                            self.annotations_data[side]['info']['num_keypoints'] = max_kp
                    
                    with open(file_path, 'w') as f:
                        json.dump(self.annotations_data[side], f, indent=2)
                    
                    self.annotation_files[side] = file_path
                    # Show full path, truncate if too long
                    display_path = file_path if len(file_path) <= 50 else "..." + file_path[-47:]
                    self.annotation_labels[side].config(text=f"Annotation: {display_path}")
                    # Also update canvas label
                    if side == "left" and hasattr(self, 'left_annotation_label_canvas'):
                        self.left_annotation_label_canvas.config(text=f"Annotation: {display_path}")
                    elif side == "right" and hasattr(self, 'right_annotation_label_canvas'):
                        self.right_annotation_label_canvas.config(text=f"Annotation: {display_path}")
                    
                    self.unsaved_changes[side] = False
                    import time
                    self.last_save_times[side] = time.time()
                    self.save_indicators[side].config(text="✓ Saved", foreground="green")
                    self.root.after(2000, lambda s=side: self.save_indicators[s].config(text=""))
                    
                    self.update_status(f"Saved {side} annotations to {file_path}")
                    messagebox.showinfo("Success", f"Standard annotations saved ({side})")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
    
    def export_to_coco(self, side=None):
        """Export annotations to COCO format"""
        if side is None:
            side = self.active_side
        
        if not self.annotations_data[side]:
            messagebox.showwarning("Warning", f"No annotations to export for {side} side")
            return
        
        file_path = filedialog.asksaveasfilename(
            title=f"Export {side.upper()} to COCO Format",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            coco_data = {
                "info": {
                    "description": f"Exported from Dual Keypoint Labeler ({side})",
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
            
            image_id_map = {}
            image_id = 1
            annotation_id = 1
            
            for ann in self.annotations_data[side].get('annotations', []):
                img_path = ann.get('image', '')
                if not img_path:
                    continue
                
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
                
                coco_keypoints = []
                for kp in keypoints:
                    if len(kp) >= 2:
                        x, y = float(kp[0]), float(kp[1])
                        v = int(kp[2]) if len(kp) >= 3 else 2
                        coco_keypoints.extend([x, y, v])
                
                if coco_keypoints:
                    xs = [kp[0] for kp in keypoints if len(kp) >= 2]
                    ys = [kp[1] for kp in keypoints if len(kp) >= 2]
                    
                    if xs and ys:
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        bbox_width = x_max - x_min + 20
                        bbox_height = y_max - y_min + 20
                        x_min = max(0, x_min - 10)
                        y_min = max(0, y_min - 10)
                        
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
    
    def export_to_yolo(self, side):
        """Export to YOLO format (placeholder - implement if needed)"""
        messagebox.showinfo("Info", f"YOLO export for {side} - implement as needed")
    
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
                self.update_keypoint_list("left")
                self.update_keypoint_list("right")
                self.display_image("left")
                self.display_image("right")
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
            self.update_keypoint_list("left")
            self.update_keypoint_list("right")
            self.display_image("left")
            self.display_image("right")
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
            'head', 'l_ear', 'r_ear', 'l_shoulder', 'r_shoulder',
            'l_elbow', 'r_elbow', 'l_wrist', 'r_wrist',
            'l_hip', 'r_hip', 'l_knee', 'r_knee', 'l_foot', 'r_foot',
            'club_grip', 'hand', 'club_shaft', 'club_hosel'
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
    
    def start_auto_save(self):
        """Start auto-save timer"""
        if self.auto_save_enabled:
            self.check_auto_save()
            self.auto_save_job = self.root.after(self.auto_save_interval * 1000, self.start_auto_save)
    
    def check_auto_save(self):
        """Check if auto-save is needed"""
        import time
        current_time = time.time()
        
        for side in ["left", "right"]:
            has_file = (self.format_mode == "coco" and self.coco_annotation_files[side]) or \
                      (self.format_mode == "standard" and self.annotation_files[side])
            
            if self.unsaved_changes[side] and has_file:
                if current_time - self.last_save_times[side] >= self.auto_save_interval:
                    self.auto_save(side)
    
    def auto_save(self, side):
        """Perform auto-save"""
        if not self.annotations_data[side]:
            return
        
        try:
            if self.format_mode == "coco":
                if not self.coco_annotation_files[side]:
                    return
                file_path = self.coco_annotation_files[side]
            else:
                if not self.annotation_files[side]:
                    return
                file_path = self.annotation_files[side]
            
            with open(file_path, 'w') as f:
                json.dump(self.annotations_data[side], f, indent=2)
            self.unsaved_changes[side] = False
            import time
            self.last_save_times[side] = time.time()
            self.save_indicators[side].config(text="✓ Auto-saved", foreground="green")
            self.root.after(2000, lambda s=side: self.save_indicators[s].config(text=""))
        except Exception as e:
            print(f"Auto-save failed ({side}): {e}")
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.after(5000, lambda: self.status_bar.config(text=self.get_status_text()))
    
    def get_status_text(self):
        """Get current status text with mode, keypoint info, zoom, and file status"""
        mode = self.edit_mode.get()
        mode_text = {"move": "Move", "add": "Add", "delete": "Delete"}.get(mode, "Unknown")
        
        # Get selected keypoint info
        side = self.active_side
        kp_info = ""
        if self.selected_keypoints[side] is not None and self.current_annotations[side]:
            keypoints = self.current_annotations[side].get('keypoints', [])
            idx = self.selected_keypoints[side]
            if idx < len(keypoints):
                kp = keypoints[idx]
                label = self.keypoint_names[idx % len(self.keypoint_names)]
                kp_info = f" | {label} ({kp[0]:.0f},{kp[1]:.0f})"
        
        # Get zoom level
        zoom = int(self.scale_factors[side] * 100) if self.scale_factors[side] > 0 else 100
        zoom_text = f" | Zoom: {zoom}%"
        
        # Get unsaved status
        unsaved_text = ""
        if self.unsaved_changes["left"] or self.unsaved_changes["right"]:
            unsaved_text = " | *Unsaved"
        
        return f"Mode: {mode_text}{kp_info}{zoom_text}{unsaved_text}"
    
    def update_status_hover(self, side, keypoint_idx):
        """Update status bar with hover keypoint info"""
        if not self.current_annotations[side]:
            return
        
        keypoints = self.current_annotations[side].get('keypoints', [])
        if keypoint_idx >= len(keypoints):
            return
        
        kp = keypoints[keypoint_idx]
        label = self.keypoint_names[keypoint_idx % len(self.keypoint_names)]
        if len(kp) >= 3:
            vis_text = {0: "Not Labeled", 1: "Occluded", 2: "Visible"}.get(int(kp[2]), "?")
            hover_text = f"Hover: {label} ({kp[0]:.1f}, {kp[1]:.1f}) v={kp[2]} ({vis_text})"
        else:
            hover_text = f"Hover: {label} ({kp[0]:.1f}, {kp[1]:.1f})"
        
        self.status_bar.config(text=hover_text)
    
    def toggle_skeleton(self):
        """Toggle skeleton visibility"""
        self.show_skeleton = not self.show_skeleton
        self.left_skeleton_var.set(self.show_skeleton)
        self.right_skeleton_var.set(self.show_skeleton)
        self.display_image("left", force=True)
        self.display_image("right", force=True)
        self.update_status(f"Skeleton: {'ON' if self.show_skeleton else 'OFF'}")
    
    def switch_active_side(self):
        """Switch active side"""
        self.active_side = "right" if self.active_side == "left" else "left"
        self.update_active_side_indication()
        self.update_status(f"Active side: {self.active_side.upper()}")
    
    def deselect_keypoint(self):
        """Deselect current keypoint"""
        side = self.active_side
        if self.selected_keypoints[side] is not None:
            self.selected_keypoints[side] = None
            self.display_image(side, force=True)
            self.update_status("Keypoint deselected")
    
    def update_status_display(self):
        """Update status bar display periodically"""
        self.status_bar.config(text=self.get_status_text())
        self.root.after(1000, self.update_status_display)
    
    def add_tooltips(self):
        """Add tooltips to buttons"""
        def create_tooltip(widget, text):
            def on_enter(event):
                tooltip = tk.Toplevel()
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
                label = tk.Label(tooltip, text=text, bg='#FFFFE0', fg='#000000',
                               font=('Segoe UI', 8), relief=tk.SOLID, borderwidth=1,
                               padx=4, pady=2)
                label.pack()
                widget.tooltip = tooltip
            
            def on_leave(event):
                if hasattr(widget, 'tooltip'):
                    widget.tooltip.destroy()
                    del widget.tooltip
            
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
        
        # Add tooltips to mode buttons
        if hasattr(self, 'move_button'):
            create_tooltip(self.move_button, "Move keypoints (M)")
        if hasattr(self, 'add_button'):
            create_tooltip(self.add_button, "Add keypoint (A)")
        if hasattr(self, 'delete_button'):
            create_tooltip(self.delete_button, "Delete keypoint (D)")
    
    def load_settings(self):
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'geometry' in settings:
                        self.root.geometry(settings['geometry'])
                    if 'last_folders' in settings:
                        self._last_folders = settings['last_folders']
            except Exception as e:
                print(f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'geometry': self.root.geometry(),
                'last_folders': {
                    'left': self.image_folders['left'],
                    'right': self.image_folders['right']
                }
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.save_settings()
        self.root.destroy()
    
    def export_statistics(self):
        """Export annotation statistics"""
        stats = {
            "left": self.calculate_statistics("left"),
            "right": self.calculate_statistics("right")
        }
        
        file_path = filedialog.asksaveasfilename(
            title="Export Statistics",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w') as f:
                json.dump(stats, f, indent=2)
            messagebox.showinfo("Success", "Statistics exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export statistics: {str(e)}")
    
    def calculate_statistics(self, side):
        """Calculate annotation statistics for a side"""
        if not self.annotations_data[side]:
            return {}
        
        total_images = len(self.image_lists[side])
        annotated_images = 0
        total_keypoints = 0
        keypoint_counts = {}
        visibility_counts = {0: 0, 1: 0, 2: 0}
        
        for ann in self.annotations_data[side].get('annotations', []):
            keypoints = ann.get('keypoints', [])
            if keypoints:
                annotated_images += 1
                total_keypoints += len(keypoints)
                for idx, kp in enumerate(keypoints):
                    if isinstance(kp, (list, tuple)) and len(kp) >= 2:
                        keypoint_counts[idx] = keypoint_counts.get(idx, 0) + 1
                        if len(kp) >= 3:
                            try:
                                vis = int(kp[2])
                                if vis in visibility_counts:
                                    visibility_counts[vis] = visibility_counts.get(vis, 0) + 1
                            except (ValueError, TypeError):
                                pass
        
        return {
            "total_images": total_images,
            "annotated_images": annotated_images,
            "total_keypoints": total_keypoints,
            "average_keypoints_per_image": total_keypoints / annotated_images if annotated_images > 0 else 0,
            "visibility_counts": visibility_counts,
            "completion_percentage": (annotated_images / total_images * 100) if total_images > 0 else 0
        }
    
    def sync_navigation_toggle(self):
        """Toggle navigation synchronization"""
        self.sync_navigation = not self.sync_navigation
        self.update_status(f"Sync navigation: {'ON' if self.sync_navigation else 'OFF'}")
    
    def match_by_filename_toggle(self):
        """Toggle filename matching"""
        self.match_by_filename = not self.match_by_filename
        if self.match_by_filename:
            self.sync_by_filename()
        self.update_status(f"Match by filename: {'ON' if self.match_by_filename else 'OFF'}")
    
    def sync_by_filename(self):
        """Sync both sides by matching filenames"""
        if not self.image_lists["left"] or not self.image_lists["right"]:
            return
        
        # Create filename maps
        left_map = {os.path.basename(f): i for i, f in enumerate(self.image_lists["left"])}
        right_map = {os.path.basename(f): i for i, f in enumerate(self.image_lists["right"])}
        
        # Find matching filenames
        common_names = set(left_map.keys()) & set(right_map.keys())
        
        if common_names:
            # Use first common filename to sync
            first_match = list(common_names)[0]
            self.current_image_indices["left"] = left_map[first_match]
            self.current_image_indices["right"] = right_map[first_match]
            self.load_current_image("left")
            self.load_current_image("right")
            self.update_status(f"Synced by filename: {first_match}")


def main():
    root = tk.Tk()
    app = DualKeypointLabeler(root)
    root.mainloop()


if __name__ == "__main__":
    main()

