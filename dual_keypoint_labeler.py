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
from PIL import Image, ImageTk, ImageFont
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
        self.keypoint_radius = 4  # Reduced from 8 for better visibility of points
        
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
        
        # Edit mode (drag/move/add/delete) - initialize early
        self.edit_mode = tk.StringVar(value="move")
        
        # Drag mode tracking
        self._drag_start_x = None
        self._drag_start_y = None
        
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
        
        # Load fonts from font folder
        self.font_path = Path(__file__).parent / "font"
        try:
            # Try to use NotoSansKR, fallback to system font if not available
            if (self.font_path / "NotoSansKR-Regular.ttf").exists():
                self.font_family = 'Noto Sans KR'
            else:
                self.font_family = 'Segoe UI'
        except:
            self.font_family = 'Segoe UI'
        
        # UI Setup
        self.setup_ui()
        
    def setup_ui(self):
        # Configure root window with professional styling - slate-50 background
        self.root.config(bg='#F8FAFC')  # slate-50
        
        # Configure modern ttk styles
        style = ttk.Style()
        # Use a more modern theme - 'vista' on Windows, 'aqua' on macOS, 'clam' as fallback
        try:
            if self.root.tk.call('tk', 'windowingsystem') == 'win32':
                style.theme_use('vista')
            else:
                style.theme_use('clam')
        except:
            style.theme_use('clam')
        
        # Modern scrollbar styling - thin and sleek
        style.configure('Modern.Vertical.TScrollbar',
                       background='#E5E7EB',
                       troughcolor='#F3F4F6',
                       borderwidth=0,
                       arrowcolor='#6B7280',
                       darkcolor='#E5E7EB',
                       lightcolor='#E5E7EB',
                       width=12,
                       gripcount=0)
        style.map('Modern.Vertical.TScrollbar',
                 background=[('active', '#D1D5DB'), ('pressed', '#9CA3AF')])
        
        style.configure('Modern.Horizontal.TScrollbar',
                       background='#E5E7EB',
                       troughcolor='#F3F4F6',
                       borderwidth=0,
                       arrowcolor='#6B7280',
                       darkcolor='#E5E7EB',
                       lightcolor='#E5E7EB',
                       width=12,
                       gripcount=0)
        style.map('Modern.Horizontal.TScrollbar',
                 background=[('active', '#D1D5DB'), ('pressed', '#9CA3AF')])
        
        # Modern frame styling
        style.configure('Modern.TFrame',
                       background='#FFFFFF',
                       borderwidth=0,
                       relief='flat')
        
        # Modern LabelFrame styling
        style.configure('Modern.TLabelframe',
                       background='#FFFFFF',
                       borderwidth=1,
                       relief='flat',
                       bordercolor='#E5E7EB')
        style.configure('Modern.TLabelframe.Label',
                       background='#FFFFFF',
                       foreground='#374151',
                       font=(self.font_family, 9, 'bold'))
        
        # Modern Scale (Slider) styling - sleek and modern
        style.configure('Modern.Horizontal.TScale',
                       background='#FFFFFF',
                       troughcolor='#E2E8F0',  # slate-200
                       borderwidth=0,
                       sliderthickness=16,
                       sliderrelief='flat',
                       sliderlength=16,
                       darkcolor='#2563EB',  # blue-600 for slider
                       lightcolor='#2563EB',
                       bordercolor='#E2E8F0')
        style.map('Modern.Horizontal.TScale',
                 background=[('active', '#2563EB')],  # blue-600 when active
                 troughcolor=[('active', '#E2E8F0')],
                 darkcolor=[('active', '#1D4ED8')],  # blue-700 when active
                 lightcolor=[('active', '#1D4ED8')])
        
        # TOP HEADER - white background with border-bottom, shadow-sm
        header_frame = tk.Frame(self.root, bg='#FFFFFF', height=56, relief=tk.FLAT, bd=0)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Bottom border for header (border-bottom)
        header_border = tk.Frame(header_frame, bg='#E2E8F0', height=1)  # slate-200
        header_border.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Header content container
        header_content = tk.Frame(header_frame, bg='#FFFFFF', height=56)
        header_content.pack(fill=tk.BOTH, expand=True, padx=24, pady=12)
        
        # Left side: App title + subtitle
        title_container = tk.Frame(header_content, bg='#FFFFFF')
        title_container.pack(side=tk.LEFT)
        
        title_label = tk.Label(title_container, text="Keypoint Annotation Tool", 
                              font=(self.font_family, 18, 'bold'), 
                              bg='#FFFFFF', fg='#1E293B', anchor='w')  # slate-800
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(title_container, text="Dual-View Editor", 
                                 font=(self.font_family, 11), 
                                 bg='#FFFFFF', fg='#64748B', anchor='w')  # slate-500
        subtitle_label.pack(side=tk.LEFT, padx=(12, 0))
        
        # Right side: Settings, Export, Save Both buttons
        header_btn_frame = tk.Frame(header_content, bg='#FFFFFF')
        header_btn_frame.pack(side=tk.RIGHT)
        
        # Header button style
        header_btn_style = {
            'font': (self.font_family, 10, 'normal'),
            'relief': tk.FLAT,
            'bd': 0,
            'padx': 16,
            'pady': 8,
            'cursor': 'hand2',
            'bg': '#FFFFFF',
            'fg': '#475569',  # slate-600
            'activebackground': '#F1F5F9',  # slate-100
            'activeforeground': '#1E293B',  # slate-800
            'highlightthickness': 0
        }
        
        settings_btn = tk.Button(header_btn_frame, text="Settings", 
                                command=self.edit_keypoint_names,
                                **header_btn_style)
        settings_btn.pack(side=tk.LEFT, padx=4)
        
        # Export button with dropdown menu
        export_menu_btn = tk.Menubutton(header_btn_frame, text="Export", 
                                        direction='below',
                                        **header_btn_style)
        export_menu_btn.pack(side=tk.LEFT, padx=4)
        
        export_dropdown = tk.Menu(export_menu_btn, tearoff=0, 
                                  font=(self.font_family, 9),
                                  bg='#FFFFFF', fg='#1E293B',
                                  activebackground='#F1F5F9', activeforeground='#1E293B',
                                  selectcolor='#E2E8F0')
        export_menu_btn.config(menu=export_dropdown)
        export_dropdown.add_command(label="Export Left to COCO...", command=lambda: self.export_to_coco("left"))
        export_dropdown.add_command(label="Export Right to COCO...", command=lambda: self.export_to_coco("right"))
        export_dropdown.add_separator()
        export_dropdown.add_command(label="Export Statistics...", command=self.export_statistics)
        
        # Save Both button - primary blue button
        save_both_btn = tk.Button(header_btn_frame, text="Save Both", 
                                 font=(self.font_family, 10, 'bold'),
                                 bg='#2563EB', fg='#FFFFFF',  # blue-600
                                 activebackground='#1D4ED8', activeforeground='#FFFFFF',  # blue-700
                                 relief=tk.FLAT, bd=0, padx=18, pady=8, cursor='hand2',
                                 command=self.save_both_sides,
                                 highlightthickness=0)
        save_both_btn.pack(side=tk.LEFT, padx=(12, 0))
        
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
        
        # MAIN CONTENT AREA - Sidebar + 50/50 split layout (flex-1)
        main_frame = tk.Frame(self.root, bg='#F8FAFC')  # slate-50
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # LEFT SIDEBAR - modern design with gradient background (320px width)
        left_panel = tk.Frame(main_frame, width=320, bg='#F1F5F9', relief=tk.FLAT, bd=0)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        # Sidebar scrollable area - using Canvas for proper scrolling
        sidebar_canvas = tk.Canvas(left_panel, bg='#F1F5F9', highlightthickness=0)
        sidebar_scrollbar = ttk.Scrollbar(left_panel, orient=tk.VERTICAL, command=sidebar_canvas.yview, style='Modern.Vertical.TScrollbar')
        sidebar_scroll = tk.Frame(sidebar_canvas, bg='#F1F5F9')
        
        # Configure scrolling
        sidebar_scroll.bind(
            "<Configure>",
            lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        )
        
        scroll_window = sidebar_canvas.create_window((0, 0), window=sidebar_scroll, anchor="nw")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        
        # Function to update canvas window width when canvas is resized
        def configure_scroll_region(event):
            canvas_width = event.width
            sidebar_canvas.itemconfig(scroll_window, width=canvas_width)
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        
        sidebar_canvas.bind('<Configure>', configure_scroll_region)
        
        # Pack canvas and scrollbar
        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Enable mousewheel scrolling on the sidebar
        def _on_mousewheel(event):
            sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to the canvas
        sidebar_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Also bind to the scrollable frame and its children for better UX
        def bind_to_children(parent):
            parent.bind("<MouseWheel>", _on_mousewheel)
            for child in parent.winfo_children():
                bind_to_children(child)
        
        bind_to_children(sidebar_scroll)
        
        # Sidebar sections - modern styling matching React design
        section_style = {
            'font': (self.font_family, 10, 'bold'),
            'bg': '#F8FAFC',  # slate-50
            'fg': '#475569',  # slate-600
            'anchor': 'w'
        }
        
        # Initialize active_side_var for internal use (not displayed in UI)
        self.active_side_var = tk.StringVar(value="left")
        self.format_mode_var = tk.StringVar(value="standard")
        self.visibility_var = tk.IntVar(value=2)
        self.skeleton_var = tk.BooleanVar(value=True)
        self.labels_var = tk.BooleanVar(value=True)
        self.radius_var = tk.IntVar(value=self.keypoint_radius)
        
        # Initialize skeleton variables for left and right sides (checkboxes removed but variables still used)
        self.left_skeleton_var = tk.BooleanVar(value=True)
        self.right_skeleton_var = tk.BooleanVar(value=True)
        
        # Navigation Section - 2-col grid for Prev/Next, 3-col for First/Last/Reset
        nav_section_label = tk.Label(sidebar_scroll, text="NAVIGATION", **section_style)
        nav_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        nav_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        nav_frame.pack(fill=tk.X, padx=16, pady=(0, 0))
        
        nav_inner = tk.Frame(nav_frame, bg='#FFFFFF')
        nav_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        # 2-column grid: Previous/Next (blue buttons)
        nav_row1 = tk.Frame(nav_inner, bg='#FFFFFF')
        nav_row1.pack(fill=tk.X, pady=(0, 8))
        
        # Navigation buttons - blue-600 for Prev/Next
        nav_btn_style = {
            'font': (self.font_family, 9, 'normal'),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 16,
            'pady': 10,
            'bd': 0,
            'bg': '#2563EB',  # blue-600
            'fg': '#FFFFFF',
            'activebackground': '#1D4ED8',  # blue-700 hover
            'activeforeground': '#FFFFFF',
            'highlightthickness': 0
        }
        
        prev_btn = tk.Button(nav_row1, text="Previous", 
                            command=self.previous_image, **nav_btn_style)
        prev_btn.grid(row=0, column=0, sticky='ew', padx=8, pady=0)
        
        next_btn = tk.Button(nav_row1, text="Next", 
                            command=self.next_image, **nav_btn_style)
        next_btn.grid(row=0, column=1, sticky='ew', padx=8, pady=0)
        
        nav_row1.columnconfigure(0, weight=1)
        nav_row1.columnconfigure(1, weight=1)
        
        # 3-column grid: First/Last (slate-700), Reset (amber-500)
        nav_row2 = tk.Frame(nav_inner, bg='#FFFFFF')
        nav_row2.pack(fill=tk.X, pady=(8, 0))
        
        first_btn = tk.Button(nav_row2, text="First", 
                             command=lambda: self.jump_to_image(0),
                             font=(self.font_family, 9, 'normal'),
                             relief=tk.FLAT, bd=0, cursor='hand2',
                             padx=12, pady=8,
                             bg='#334155', fg='#FFFFFF',  # slate-700
                             activebackground='#1E293B', activeforeground='#FFFFFF',
                             highlightthickness=0)
        first_btn.grid(row=0, column=0, sticky='ew', padx=8)
        
        last_btn = tk.Button(nav_row2, text="Last", 
                            command=lambda: self.jump_to_image(-1),
                            font=(self.font_family, 9, 'normal'),
                            relief=tk.FLAT, bd=0, cursor='hand2',
                            padx=12, pady=8,
                            bg='#334155', fg='#FFFFFF',  # slate-700
                            activebackground='#1E293B', activeforeground='#FFFFFF',
                            highlightthickness=0)
        last_btn.grid(row=0, column=1, sticky='ew', padx=8)
        
        reset_btn = tk.Button(nav_row2, text="Reset", 
                             command=self.reset_zoom,
                             font=(self.font_family, 9, 'normal'),
                             relief=tk.FLAT, bd=0, cursor='hand2',
                             padx=12, pady=8,
                             bg='#F59E0B', fg='#FFFFFF',  # amber-500
                             activebackground='#D97706', activeforeground='#FFFFFF',
                             highlightthickness=0)
        reset_btn.grid(row=0, column=2, sticky='ew', padx=8)
        
        nav_row2.columnconfigure(0, weight=1)
        nav_row2.columnconfigure(1, weight=1)
        nav_row2.columnconfigure(2, weight=1)
        
        # Initialize labels
        self.image_index_labels = {
            "left": tk.Label(nav_inner, text="", font=(self.font_family, 1), bg='#FFFFFF'),
            "right": tk.Label(nav_inner, text="", font=(self.font_family, 1), bg='#FFFFFF')
        }
        self.progress_labels = {
            "left": tk.Label(nav_inner, text="", font=(self.font_family, 1), bg='#FFFFFF'),
            "right": tk.Label(nav_inner, text="", font=(self.font_family, 1), bg='#FFFFFF')
        }
        
        # Border separator
        nav_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        nav_border.pack(fill=tk.X, side=tk.TOP)
        
        # Edit Mode Section - 4-column grid (drag, move, add, delete)
        mode_section_label = tk.Label(sidebar_scroll, text="EDIT MODE", **section_style)
        mode_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        mode_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        mode_frame.pack(fill=tk.X, padx=16, pady=(0, 0))
        
        mode_inner = tk.Frame(mode_frame, bg='#FFFFFF')
        mode_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        mode_grid = tk.Frame(mode_inner, bg='#FFFFFF')
        mode_grid.pack(fill=tk.X)
        
        mode_btn_style = {
            'font': (self.font_family, 10, 'normal'),
            'relief': tk.FLAT,
            'bd': 0,
            'padx': 8,
            'pady': 12,
            'cursor': 'hand2',
            'highlightthickness': 0
        }
        
        self.drag_button = tk.Button(mode_grid, text="Drag", 
                                     command=lambda: self.set_mode("drag"),
                                     bg='#F1F5F9', fg='#334155',  # slate-100, slate-700
                                     activebackground='#E2E8F0', activeforeground='#334155',
                                     **mode_btn_style)
        self.drag_button.grid(row=0, column=0, sticky='ew', padx=8)
        
        self.move_button = tk.Button(mode_grid, text="Move", 
                                     command=lambda: self.set_mode("move"),
                                     bg='#F1F5F9', fg='#334155',  # slate-100, slate-700
                                     activebackground='#E2E8F0', activeforeground='#334155',
                                     **mode_btn_style)
        self.move_button.grid(row=0, column=1, sticky='ew', padx=8)
        
        self.add_button = tk.Button(mode_grid, text="Add", 
                                    command=lambda: self.set_mode("add"),
                                    bg='#F1F5F9', fg='#334155',
                                    activebackground='#E2E8F0', activeforeground='#334155',
                                    **mode_btn_style)
        self.add_button.grid(row=0, column=2, sticky='ew', padx=8)
        
        self.delete_button = tk.Button(mode_grid, text="Delete", 
                                       command=lambda: self.set_mode("delete"),
                                       bg='#F1F5F9', fg='#334155',
                                       activebackground='#E2E8F0', activeforeground='#334155',
                                       **mode_btn_style)
        self.delete_button.grid(row=0, column=3, sticky='ew', padx=8)
        
        mode_grid.columnconfigure(0, weight=1)
        mode_grid.columnconfigure(1, weight=1)
        mode_grid.columnconfigure(2, weight=1)
        mode_grid.columnconfigure(3, weight=1)
        
        # Update button appearance and cursor
        self.update_mode_buttons()
        self.update_cursor_for_mode()
        
        # Border separator
        mode_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        mode_border.pack(fill=tk.X, side=tk.TOP)
        
        # Format Mode Section - toggle buttons
        format_section_label = tk.Label(sidebar_scroll, text="FORMAT MODE", **section_style)
        format_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        format_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        format_frame.pack(fill=tk.X, padx=16, pady=(0, 0))
        
        format_inner = tk.Frame(format_frame, bg='#FFFFFF')
        format_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        format_grid = tk.Frame(format_inner, bg='#FFFFFF')
        format_grid.pack(fill=tk.X)
        
        def create_format_toggle(text, value):
            def on_click():
                self.format_mode_var.set(value)
                self.on_format_mode_change()
                update_all_format_buttons()
            
            btn = tk.Button(format_grid, text=text,
                          font=(self.font_family, 9, 'normal'),
                          relief=tk.FLAT, bd=0, cursor='hand2',
                          padx=16, pady=10,
                          bg='#F1F5F9', fg='#334155',  # slate-100, slate-700
                          activebackground='#E2E8F0', activeforeground='#334155',
                          highlightthickness=0,
                          command=on_click)
            
            def update_format_btn():
                if self.format_mode_var.get() == value:
                    btn.config(bg='#2563EB', fg='#FFFFFF')  # blue-600 when active
                else:
                    btn.config(bg='#F1F5F9', fg='#334155')  # slate-100 when inactive
            
            btn.update_func = update_format_btn
            return btn
        
        def update_all_format_buttons():
            if hasattr(self, 'format_std_btn'):
                self.format_std_btn.update_func()
            if hasattr(self, 'format_coco_btn'):
                self.format_coco_btn.update_func()
        
        std_btn = create_format_toggle("Standard", "standard")
        std_btn.grid(row=0, column=0, sticky='ew', padx=4)
        self.format_std_btn = std_btn
        
        coco_btn = create_format_toggle("COCO", "coco")
        coco_btn.grid(row=0, column=1, sticky='ew', padx=4)
        self.format_coco_btn = coco_btn
        
        format_grid.columnconfigure(0, weight=1)
        format_grid.columnconfigure(1, weight=1)
        
        # Store update function
        self.update_format_buttons = update_all_format_buttons
        
        # Update initial state
        std_btn.update_func()
        
        # Border separator
        format_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        format_border.pack(fill=tk.X, side=tk.TOP)
        
        # Visibility controls (COCO mode) - full width buttons
        self.visibility_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        
        visibility_section_label = tk.Label(self.visibility_frame, text="VISIBILITY (COCO)", **section_style)
        visibility_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        vis_inner = tk.Frame(self.visibility_frame, bg='#FFFFFF')
        vis_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))
        
        # Visibility options - all use blue-600 when active
        vis_options = [
            ("Visible (v=2)", 2),
            ("Occluded (v=1)", 1),
            ("Not Labeled (v=0)", 0)
        ]
        
        def update_all_vis_buttons(*args):
            for btn in self.vis_buttons:
                btn.update_func()
        
        def create_vis_button(text, value):
            def on_click():
                self.visibility_var.set(value)
                update_all_vis_buttons()
            
            btn = tk.Button(vis_inner, text=text,
                          font=(self.font_family, 9, 'normal'),
                          relief=tk.FLAT, bd=0, cursor='hand2',
                          padx=16, pady=10, anchor='w',
                          bg='#F1F5F9', fg='#334155',  # slate-100, slate-700
                          activebackground='#E2E8F0', activeforeground='#334155',
                          highlightthickness=0,
                          command=on_click)
            
            def update_vis_btn():
                if self.visibility_var.get() == value:
                    btn.config(bg='#2563EB', fg='#FFFFFF')  # blue-600 when active
                else:
                    btn.config(bg='#F1F5F9', fg='#334155')  # slate-100 when inactive
            
            btn.update_func = update_vis_btn
            btn.pack(fill=tk.X, pady=8)
            return btn
        
        self.vis_buttons = []
        for text, value in vis_options:
            btn = create_vis_button(text, value)
            self.vis_buttons.append(btn)
        
        # Update initial state
        for btn in self.vis_buttons:
            btn.update_func()
        
        # Border separator
        vis_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        vis_border.pack(fill=tk.X, side=tk.TOP)
        
        # Actions Section
        actions_section_label = tk.Label(sidebar_scroll, text="ACTIONS", **section_style)
        actions_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        actions_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        actions_frame.pack(fill=tk.X, padx=16, pady=(0, 0))
        
        actions_inner = tk.Frame(actions_frame, bg='#FFFFFF')
        actions_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        # Undo/Redo in 2-column grid
        undo_redo_frame = tk.Frame(actions_inner, bg='#FFFFFF')
        undo_redo_frame.pack(fill=tk.X, pady=(0, 8))
        
        undo_redo_inner = tk.Frame(undo_redo_frame, bg='#FFFFFF')
        undo_redo_inner.pack(fill=tk.X)
        
        undo_btn_style = {
            'font': (self.font_family, 9, 'normal'),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 12,
            'pady': 8,
            'bd': 0,
            'bg': '#F1F5F9',  # slate-100
            'fg': '#334155',  # slate-700
            'activebackground': '#E2E8F0',  # slate-200 hover
            'activeforeground': '#1E293B',
            'highlightthickness': 0
        }
        
        undo_btn = tk.Button(undo_redo_inner, text="Undo", 
                            command=self.undo_action, **undo_btn_style)
        undo_btn.grid(row=0, column=0, sticky='ew', padx=8)
        
        redo_btn = tk.Button(undo_redo_inner, text="Redo", 
                            command=self.redo_action, **undo_btn_style)
        redo_btn.grid(row=0, column=1, sticky='ew', padx=8)
        
        undo_redo_inner.columnconfigure(0, weight=1)
        undo_redo_inner.columnconfigure(1, weight=1)
        
        # Action buttons with specific colors
        action_btn_style = {
            'font': (self.font_family, 9, 'normal'),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 16,
            'pady': 4,
            'bd': 0,
            'highlightthickness': 0
        }
        
        # Clear All: red-50 background with red-700 text and border
        clear_btn_style = action_btn_style.copy()
        clear_btn_style.update({
            'bg': '#FEF2F2',  # red-50
            'fg': '#B91C1C',  # red-700
            'activebackground': '#FEE2E2',
            'activeforeground': '#991B1B',
            'highlightthickness': 1,
            'highlightbackground': '#FECACA'  # border-red-200
        })
        clear_btn = tk.Button(actions_inner, text="Clear All Keypoints", 
                            command=self.clear_keypoints,
                            **clear_btn_style)
        clear_btn.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        # Copy buttons: slate-800 background
        copy_btn = tk.Button(actions_inner, text="Copy Previous (Ctrl+C)", 
                            command=self.copy_from_previous_frame,
                            bg='#1E293B', fg='#FFFFFF',
                            activebackground='#0F172A', activeforeground='#FFFFFF',
                            **action_btn_style)
        copy_btn.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        copy_both_btn = tk.Button(actions_inner, text="Copy Both (Ctrl+B)", 
                                 command=self.copy_from_previous_frame_both,
                                 bg='#1E293B', fg='#FFFFFF',
                                 activebackground='#0F172A', activeforeground='#FFFFFF',
                                 **action_btn_style)
        copy_both_btn.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        # Copy only keypoints or only visibility buttons
        copy_kp_btn = tk.Button(actions_inner, text="Copy Keypoints Only", 
                               command=self.copy_keypoints_only,
                               bg='#2563EB', fg='#FFFFFF',  # blue-600
                               activebackground='#1D4ED8', activeforeground='#FFFFFF',
                               **action_btn_style)
        copy_kp_btn.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        copy_vis_btn = tk.Button(actions_inner, text="Copy Visibility Only", 
                                command=self.copy_visibility_only,
                                bg='#059669', fg='#FFFFFF',  # emerald-600
                                activebackground='#047857', activeforeground='#FFFFFF',
                                **action_btn_style)
        copy_vis_btn.pack(fill=tk.X, pady=(0, 0), ipady=4)
        
        # Border separator
        actions_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        actions_border.pack(fill=tk.X, side=tk.TOP)
        
        # Visibility Guide Section
        self.visibility_guide_frame = tk.Frame(sidebar_scroll, bg='#F8FAFC', relief=tk.FLAT, bd=0)
        
        guide_section_label = tk.Label(self.visibility_guide_frame, text="VISIBILITY GUIDE", **section_style)
        guide_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        guide_inner = tk.Frame(self.visibility_guide_frame, bg='#F8FAFC')
        guide_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))
        
        # Three white cards with border
        guide_cards = [
            {
                'title': 'v=2 (Visible)',
                'content': 'Clear: 선명히 잘 보임\nBlurry: 안보이기만 하지 않으면 위치 추정 가능'
            },
            {
                'title': 'v=1 (Occluded)',
                'content': 'Severe Blur: 추측해야 할 정도로 안 보임'
            },
            {
                'title': 'v=0 (Not Labeled)',
                'content': 'Not visible or cannot be determined'
            }
        ]
        
        for card in guide_cards:
            card_frame = tk.Frame(guide_inner, bg='#FFFFFF', relief=tk.FLAT, bd=1,
                                 highlightthickness=1, highlightbackground='#E2E8F0')
            card_frame.pack(fill=tk.X, pady=(0, 12))
            
            card_content = tk.Frame(card_frame, bg='#FFFFFF')
            card_content.pack(fill=tk.X, padx=12, pady=12)
            
            title_label = tk.Label(card_content, text=card['title'],
                                  font=(self.font_family, 10, 'bold'),
                                  bg='#FFFFFF', fg='#1E293B', anchor='w')
            title_label.pack(fill=tk.X, pady=(0, 4))
            
            # Use Text widget for better text wrapping
            content_text = tk.Text(card_content,
                                  font=(self.font_family, 10),
                                  bg='#FFFFFF', fg='#475569',
                                  wrap=tk.WORD,
                                  relief=tk.FLAT,
                                  borderwidth=0,
                                  highlightthickness=0,
                                  padx=0, pady=0,
                                  height=4,
                                  width=32)
            content_text.insert('1.0', card['content'])
            content_text.config(state=tk.DISABLED)
            content_text.pack(fill=tk.BOTH, expand=True)
        
        # Border separator
        guide_border = tk.Frame(sidebar_scroll, bg='#E2E8F0', height=1)
        guide_border.pack(fill=tk.X, side=tk.TOP)
        
        # Visual Settings Section
        visual_section_label = tk.Label(sidebar_scroll, text="VISUAL SETTINGS", **section_style)
        visual_section_label.pack(fill=tk.X, padx=16, pady=(16, 0))
        
        visual_frame = tk.Frame(sidebar_scroll, bg='#FFFFFF', relief=tk.FLAT, bd=0)
        visual_frame.pack(fill=tk.X, padx=16, pady=(0, 0))
        
        visual_inner = tk.Frame(visual_frame, bg='#FFFFFF')
        visual_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        tk.Checkbutton(visual_inner, text="Show Skeleton", 
                      variable=self.skeleton_var,
                      command=self.toggle_skeleton,
                      font=(self.font_family, 9), bg='#FFFFFF', fg='#334155',
                      activebackground='#FFFFFF', activeforeground='#1E293B',
                      selectcolor='#FFFFFF',
                      padx=0, pady=0, anchor='w').pack(fill=tk.X, pady=(0, 12))
        
        tk.Checkbutton(visual_inner, text="Show Keypoint Labels", 
                      variable=self.labels_var,
                      command=self.toggle_labels,
                      font=(self.font_family, 9), bg='#FFFFFF', fg='#334155',
                      activebackground='#FFFFFF', activeforeground='#1E293B',
                      selectcolor='#FFFFFF',
                      padx=0, pady=0, anchor='w').pack(fill=tk.X, pady=(0, 12))
        
        # Keypoint Size slider
        radius_container = tk.Frame(visual_inner, bg='#FFFFFF')
        radius_container.pack(fill=tk.X)
        
        radius_header = tk.Frame(radius_container, bg='#FFFFFF')
        radius_header.pack(fill=tk.X, pady=(0, 8))
        
        radius_label = tk.Label(radius_header, text="Keypoint Size", 
                               font=(self.font_family, 9, 'normal'), bg='#FFFFFF', fg='#334155', anchor='w')
        radius_label.pack(side=tk.LEFT)
        
        self.radius_value_label = tk.Label(radius_header, text=str(self.keypoint_radius),
                                           font=(self.font_family, 9, 'bold'),
                                           bg='#EFF6FF', fg='#2563EB',
                                           padx=8, pady=2, relief=tk.FLAT)
        self.radius_value_label.pack(side=tk.RIGHT)
        
        radius_slider_frame = tk.Frame(radius_container, bg='#FFFFFF')
        radius_slider_frame.pack(fill=tk.X)
        
        radius_slider = ttk.Scale(radius_slider_frame, from_=2, to=10, 
                                 variable=self.radius_var, orient=tk.HORIZONTAL,
                                 command=self.on_radius_change,
                                 style='Modern.Horizontal.TScale',
                                 length=280)
        radius_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create paned window for 50/50 split display
        self.image_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.image_paned.pack(fill=tk.BOTH, expand=True)
        
        # LEFT PANEL - Blue gradient header, ACTIVE badge
        self.left_image_frame = tk.Frame(self.image_paned, bg='#F8FAFC')  # slate-50
        self.image_paned.add(self.left_image_frame, weight=1)
        
        # LEFT PANEL HEADER - gradient blue-50 to blue-100
        left_header = tk.Frame(self.left_image_frame, bg='#EFF6FF', height=100, relief=tk.FLAT, bd=0)  # blue-50
        left_header.pack(fill=tk.X)
        left_header.pack_propagate(False)
        
        left_header_content = tk.Frame(left_header, bg='#EFF6FF')
        left_header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # Title and subtitle
        left_title_frame = tk.Frame(left_header_content, bg='#EFF6FF')
        left_title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.left_section_label = tk.Label(left_title_frame, text="LEFT (FO)", 
                                           font=(self.font_family, 16, 'bold'), 
                                           bg='#EFF6FF', fg='#1E40AF', anchor='w')  # blue-800
        self.left_section_label.pack(side=tk.TOP, anchor='w')
        
        left_subtitle = tk.Label(left_title_frame, text="Front-Oblique View", 
                                font=(self.font_family, 11), 
                                bg='#EFF6FF', fg='#3B82F6', anchor='w')  # blue-500
        left_subtitle.pack(side=tk.TOP, anchor='w', pady=(4, 0))
        
        # Buttons frame
        left_btn_frame = tk.Frame(left_header_content, bg='#EFF6FF')
        left_btn_frame.pack(side=tk.RIGHT, padx=(0, 12))
        
        # Button style
        panel_btn_style = {
            'font': (self.font_family, 10, 'normal'),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 14,
            'pady': 8,
            'bd': 0,
            'bg': '#FFFFFF',
            'fg': '#475569',  # slate-600
            'activebackground': '#F1F5F9',  # slate-100
            'activeforeground': '#1E293B',  # slate-800
            'highlightthickness': 0
        }
        
        # Left buttons - horizontal layout, top-aligned
        # Select Folder button with label below
        left_folder_col = tk.Frame(left_btn_frame, bg='#EFF6FF')
        left_folder_col.pack(side=tk.LEFT, padx=(0, 8), anchor='n')
        
        left_img_btn = tk.Button(left_folder_col, text="Select Folder", 
                                command=lambda: self.select_image_folder("left"),
                                **panel_btn_style)
        left_img_btn.pack(side=tk.TOP)
        
        # Folder name label (small, below button)
        self.left_folder_label = tk.Label(left_folder_col, text="", 
                                         font=(self.font_family, 8),
                                         bg='#EFF6FF', fg='#64748B',  # slate-500
                                         anchor='w')
        self.left_folder_label.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
        
        # Import Annotations button with label below
        left_ann_col = tk.Frame(left_btn_frame, bg='#EFF6FF')
        left_ann_col.pack(side=tk.LEFT, padx=(0, 8), anchor='n')
        
        left_ann_btn = tk.Button(left_ann_col, text="Import Annotations", 
                                command=lambda: self.import_annotations("left"),
                                **panel_btn_style)
        left_ann_btn.pack(side=tk.TOP)
        
        # Annotation file name label (small, below button)
        self.left_annotation_label = tk.Label(left_ann_col, text="", 
                                             font=(self.font_family, 8),
                                             bg='#EFF6FF', fg='#64748B',  # slate-500
                                             anchor='w')
        self.left_annotation_label.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
        
        save_left_btn = tk.Button(left_btn_frame, text="Save Left", 
                                 command=lambda: self.save_annotations("left"),
                                 font=(self.font_family, 10, 'bold'),
                                 bg='#2563EB', fg='#FFFFFF',  # blue-600
                                 activebackground='#1D4ED8', activeforeground='#FFFFFF',
                                 relief=tk.FLAT, bd=0, padx=14, pady=8, cursor='hand2',
                                 highlightthickness=0)
        save_left_btn.pack(side=tk.LEFT, padx=(12, 0), anchor='n')
        
        # Initialize save indicators (hidden, for internal use)
        self.save_indicators = {
            "left": tk.Label(left_btn_frame, text="", font=(self.font_family, 1), 
                            bg='#EFF6FF', fg='#EFF6FF'),
            "right": None
        }
        
        # File path labels (hidden, for internal use - kept for compatibility)
        self.image_folder_labels = {
            "left": tk.Label(left_btn_frame, text="", 
                            font=(self.font_family, 1), bg='#EFF6FF', fg='#EFF6FF'),
            "right": tk.Label(left_btn_frame, text="", 
                             font=(self.font_family, 1), bg='#EFF6FF', fg='#EFF6FF')
        }
        self.annotation_labels = {
            "left": tk.Label(left_btn_frame, text="", 
                           font=(self.font_family, 1), bg='#EFF6FF', fg='#EFF6FF'),
            "right": tk.Label(left_btn_frame, text="", 
                            font=(self.font_family, 1), bg='#EFF6FF', fg='#EFF6FF')
        }
        
        # LEFT CANVAS AREA - slate-100 background, white canvas with border
        left_canvas_container = tk.Frame(self.left_image_frame, bg='#F1F5F9')  # slate-100
        left_canvas_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # Canvas wrapper with border
        left_canvas_wrapper = tk.Frame(left_canvas_container, bg='#CBD5E1', relief=tk.FLAT, bd=4)  # slate-300 border
        left_canvas_wrapper.pack(fill=tk.BOTH, expand=True)
        
        # Top-left overlay: "Left: 0/0" badge
        self.left_nav_label = tk.Label(left_canvas_wrapper, text="Left: 0/0", 
                                       font=(self.font_family, 10, 'bold'), 
                                       bg='#1E293B', fg='#FFFFFF',  # slate-800
                                       relief=tk.FLAT, padx=10, pady=6)
        self.left_nav_label.place(x=12, y=12)
        
        # File path labels (hidden, for internal use)
        self.left_folder_label_canvas = tk.Label(left_canvas_wrapper, text="", 
                                                 font=(self.font_family, 1), 
                                                 bg='#FFFFFF', fg='#FFFFFF')
        self.left_annotation_label_canvas = tk.Label(left_canvas_wrapper, text="", 
                                                     font=(self.font_family, 1), 
                                                     bg='#FFFFFF', fg='#FFFFFF')
        
        # Canvas frame with scrollbars
        left_canvas_frame = tk.Frame(left_canvas_wrapper, bg='#FFFFFF')
        left_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        left_v_scrollbar = ttk.Scrollbar(left_canvas_frame, orient=tk.VERTICAL, style='Modern.Vertical.TScrollbar')
        left_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        left_h_scrollbar = ttk.Scrollbar(left_canvas_frame, orient=tk.HORIZONTAL, style='Modern.Horizontal.TScrollbar')
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
        
        # Bottom-right controls: Grid toggle + Fullscreen button (floating)
        left_controls_overlay = tk.Frame(left_canvas_wrapper, bg='#FFFFFF')
        left_controls_overlay.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor='se')
        
        grid_toggle_btn = tk.Button(left_controls_overlay, text="Grid", 
                                    font=(self.font_family, 9),
                                    bg='#FFFFFF', fg='#475569',
                                    activebackground='#F1F5F9', activeforeground='#1E293B',
                                    relief=tk.FLAT, bd=0, padx=12, pady=8, cursor='hand2',
                                    command=self.toggle_grid,
                                    highlightthickness=0)
        grid_toggle_btn.pack(side=tk.LEFT)
        
        # Left keypoint list (below canvas) - shows keypoints with coordinates and visibility
        # Split into multiple columns to show all keypoints
        left_kp_list_frame = tk.LabelFrame(self.left_image_frame, text="Keypoints (Left)", 
                                           bg='#FFFFFF', fg='#374151',
                                           font=(self.font_family, 9, 'bold'),
                                           relief=tk.FLAT, bd=1, highlightbackground='#E5E7EB',
                                           padx=6, pady=6)
        left_kp_list_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Create frame for multiple columns
        left_kp_columns_frame = tk.Frame(left_kp_list_frame, bg='#FFFFFF')
        left_kp_columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create 4 columns for keypoints + 1 column for image list
        self.left_kp_listboxes = []
        for col in range(4):
            col_frame = tk.Frame(left_kp_columns_frame, bg='#FFFFFF')
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            
            listbox = tk.Listbox(col_frame, height=5, font=(self.font_family, 9), width=20,
                               bg='#FFFFFF', fg='#1F2937',
                               selectbackground='#2563EB', selectforeground='#FFFFFF',
                               relief=tk.FLAT, bd=1, highlightthickness=1,
                               highlightbackground='#E5E7EB', highlightcolor='#2563EB')
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.left_kp_listboxes.append(listbox)
        
        # Add image list column (5th column)
        image_list_frame = tk.Frame(left_kp_columns_frame, bg='#FFFFFF')
        image_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        
        image_list_label = tk.Label(image_list_frame, text="Image List:", 
                                   font=(self.font_family, 8, 'bold'),
                                   bg='#FFFFFF', fg='#374151', anchor='w')
        image_list_label.pack(side=tk.TOP, anchor='w', pady=(0, 2))
        
        self.left_image_listbox = tk.Listbox(image_list_frame, height=5, font=(self.font_family, 9), width=25,
                                            bg='#FFFFFF', fg='#1F2937',
                                            selectbackground='#2563EB', selectforeground='#FFFFFF',
                                            relief=tk.FLAT, bd=1, highlightthickness=1,
                                            highlightbackground='#E5E7EB', highlightcolor='#2563EB')
        self.left_image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add modern scrollbar for image list
        left_img_scrollbar = ttk.Scrollbar(image_list_frame, orient=tk.VERTICAL, 
                                          command=self.left_image_listbox.yview,
                                          style='Modern.Vertical.TScrollbar')
        left_img_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_image_listbox.config(yscrollcommand=left_img_scrollbar.set)
        
        # Bind double-click to jump to image
        self.left_image_listbox.bind('<Double-Button-1>', lambda e: self.on_image_list_select("left"))
        
        
        # RIGHT PANEL - Slate gradient header, INACTIVE badge
        self.right_image_frame = tk.Frame(self.image_paned, bg='#F8FAFC')  # slate-50
        self.image_paned.add(self.right_image_frame, weight=1)
        
        # RIGHT PANEL HEADER - gradient slate-50 to slate-100
        right_header = tk.Frame(self.right_image_frame, bg='#F1F5F9', height=100, relief=tk.FLAT, bd=0)  # slate-100
        right_header.pack(fill=tk.X)
        right_header.pack_propagate(False)
        
        right_header_content = tk.Frame(right_header, bg='#F1F5F9')
        right_header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # Title and subtitle
        right_title_frame = tk.Frame(right_header_content, bg='#F1F5F9')
        right_title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.right_section_label = tk.Label(right_title_frame, text="RIGHT (DL)", 
                                            font=(self.font_family, 16, 'bold'), 
                                            bg='#F1F5F9', fg='#334155', anchor='w')  # slate-700
        self.right_section_label.pack(side=tk.TOP, anchor='w')
        
        right_subtitle = tk.Label(right_title_frame, text="Direct-Lateral View", 
                                 font=(self.font_family, 11), 
                                 bg='#F1F5F9', fg='#64748B', anchor='w')  # slate-500
        right_subtitle.pack(side=tk.TOP, anchor='w', pady=(4, 0))
        
        # Buttons frame
        right_btn_frame = tk.Frame(right_header_content, bg='#F1F5F9')
        right_btn_frame.pack(side=tk.RIGHT, padx=(0, 12))
        
        # Right buttons - horizontal layout
        # Select Folder button with label below
        right_folder_col = tk.Frame(right_btn_frame, bg='#F1F5F9')
        right_folder_col.pack(side=tk.LEFT, padx=(0, 8), anchor='n')
        
        right_img_btn = tk.Button(right_folder_col, text="Select Folder", 
                                 command=lambda: self.select_image_folder("right"),
                                 **panel_btn_style)
        right_img_btn.pack(side=tk.TOP)
        
        # Folder name label (small, below button)
        self.right_folder_label = tk.Label(right_folder_col, text="", 
                                          font=(self.font_family, 8),
                                          bg='#F1F5F9', fg='#64748B',  # slate-500
                                          anchor='w')
        self.right_folder_label.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
        
        # Import Annotations button with label below
        right_ann_col = tk.Frame(right_btn_frame, bg='#F1F5F9')
        right_ann_col.pack(side=tk.LEFT, padx=(0, 8), anchor='n')
        
        right_ann_btn = tk.Button(right_ann_col, text="Import Annotations", 
                                 command=lambda: self.import_annotations("right"),
                                 **panel_btn_style)
        right_ann_btn.pack(side=tk.TOP)
        
        # Annotation file name label (small, below button)
        self.right_annotation_label = tk.Label(right_ann_col, text="", 
                                              font=(self.font_family, 8),
                                              bg='#F1F5F9', fg='#64748B',  # slate-500
                                              anchor='w')
        self.right_annotation_label.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
        
        save_right_btn = tk.Button(right_btn_frame, text="Save Right", 
                                  command=lambda: self.save_annotations("right"),
                                  font=(self.font_family, 10, 'bold'),
                                  bg='#475569', fg='#FFFFFF',  # slate-600
                                  activebackground='#334155', activeforeground='#FFFFFF',
                                  relief=tk.FLAT, bd=0, padx=14, pady=8, cursor='hand2',
                                  highlightthickness=0)
        save_right_btn.pack(side=tk.LEFT, anchor='n')
        
        # Initialize right save indicator (hidden)
        self.save_indicators["right"] = tk.Label(right_btn_frame, text="", font=(self.font_family, 1), 
                                                 bg='#F1F5F9', fg='#F1F5F9')
        
        # File path labels (hidden, for internal use)
        self.image_folder_labels["right"] = tk.Label(right_btn_frame, text="", 
                                                     font=(self.font_family, 1), bg='#F1F5F9', fg='#F1F5F9')
        self.annotation_labels["right"] = tk.Label(right_btn_frame, text="", 
                                                  font=(self.font_family, 1), bg='#F1F5F9', fg='#F1F5F9')
        
        # RIGHT CANVAS AREA - slate-100 background, white canvas with border
        right_canvas_container = tk.Frame(self.right_image_frame, bg='#F1F5F9')  # slate-100
        right_canvas_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # Canvas wrapper with border
        right_canvas_wrapper = tk.Frame(right_canvas_container, bg='#CBD5E1', relief=tk.FLAT, bd=4)  # slate-300 border
        right_canvas_wrapper.pack(fill=tk.BOTH, expand=True)
        
        # Top-left overlay: "Right: 0/0" badge
        self.right_nav_label = tk.Label(right_canvas_wrapper, text="Right: 0/0", 
                                       font=(self.font_family, 10, 'bold'), 
                                       bg='#1E293B', fg='#FFFFFF',  # slate-800
                                       relief=tk.FLAT, padx=10, pady=6)
        self.right_nav_label.place(x=12, y=12)
        
        # File path labels (hidden, for internal use)
        self.right_folder_label_canvas = tk.Label(right_canvas_wrapper, text="", 
                                                  font=(self.font_family, 1), 
                                                  bg='#FFFFFF', fg='#FFFFFF')
        self.right_annotation_label_canvas = tk.Label(right_canvas_wrapper, text="", 
                                                      font=(self.font_family, 1), 
                                                      bg='#FFFFFF', fg='#FFFFFF')
        
        # Canvas frame with scrollbars
        right_canvas_frame = tk.Frame(right_canvas_wrapper, bg='#FFFFFF')
        right_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        right_v_scrollbar = ttk.Scrollbar(right_canvas_frame, orient=tk.VERTICAL, style='Modern.Vertical.TScrollbar')
        right_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        right_h_scrollbar = ttk.Scrollbar(right_canvas_frame, orient=tk.HORIZONTAL, style='Modern.Horizontal.TScrollbar')
        right_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvases["right"] = tk.Canvas(right_canvas_frame,
                                          yscrollcommand=right_v_scrollbar.set,
                                          xscrollcommand=right_h_scrollbar.set,
                                          bg='gray90')
        self.canvases["right"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_v_scrollbar.config(command=self.canvases["right"].yview)
        right_h_scrollbar.config(command=self.canvases["right"].xview)
        
        # Bottom-right controls: Grid toggle + Fullscreen button (floating)
        right_controls_overlay = tk.Frame(right_canvas_wrapper, bg='#FFFFFF')
        right_controls_overlay.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor='se')
        
        grid_toggle_btn_right = tk.Button(right_controls_overlay, text="Grid", 
                                          font=(self.font_family, 9),
                                          bg='#FFFFFF', fg='#475569',
                                          activebackground='#F1F5F9', activeforeground='#1E293B',
                                          relief=tk.FLAT, bd=0, padx=12, pady=8, cursor='hand2',
                                          command=self.toggle_grid,
                                          highlightthickness=0)
        grid_toggle_btn_right.pack(side=tk.LEFT)
        
        # Right keypoint list (below canvas) - shows keypoints with coordinates and visibility
        # Split into multiple columns to show all keypoints
        right_kp_list_frame = tk.LabelFrame(self.right_image_frame, text="Keypoints (Right)", 
                                           bg='#FFFFFF', fg='#374151',
                                           font=(self.font_family, 9, 'bold'),
                                           relief=tk.FLAT, bd=1, highlightbackground='#E5E7EB',
                                           padx=6, pady=6)
        right_kp_list_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Create frame for multiple columns
        right_kp_columns_frame = tk.Frame(right_kp_list_frame, bg='#FFFFFF')
        right_kp_columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create 4 columns for keypoints + 1 column for image list
        self.right_kp_listboxes = []
        for col in range(4):
            col_frame = tk.Frame(right_kp_columns_frame, bg='#FFFFFF')
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            
            listbox = tk.Listbox(col_frame, height=5, font=(self.font_family, 9), width=20,
                               bg='#FFFFFF', fg='#1F2937',
                               selectbackground='#2563EB', selectforeground='#FFFFFF',
                               relief=tk.FLAT, bd=1, highlightthickness=1,
                               highlightbackground='#E5E7EB', highlightcolor='#2563EB')
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.right_kp_listboxes.append(listbox)
        
        # Add image list column (5th column)
        image_list_frame = tk.Frame(right_kp_columns_frame, bg='#FFFFFF')
        image_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        
        image_list_label = tk.Label(image_list_frame, text="Image List:", 
                                   font=(self.font_family, 8, 'bold'),
                                   bg='#FFFFFF', fg='#374151', anchor='w')
        image_list_label.pack(side=tk.TOP, anchor='w', pady=(0, 2))
        
        self.right_image_listbox = tk.Listbox(image_list_frame, height=5, font=(self.font_family, 9), width=25,
                                            bg='#FFFFFF', fg='#1F2937',
                                            selectbackground='#2563EB', selectforeground='#FFFFFF',
                                            relief=tk.FLAT, bd=1, highlightthickness=1,
                                            highlightbackground='#E5E7EB', highlightcolor='#2563EB')
        self.right_image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add modern scrollbar for image list
        right_img_scrollbar = ttk.Scrollbar(image_list_frame, orient=tk.VERTICAL, 
                                           command=self.right_image_listbox.yview,
                                           style='Modern.Vertical.TScrollbar')
        right_img_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_image_listbox.config(yscrollcommand=right_img_scrollbar.set)
        
        # Bind double-click to jump to image
        self.right_image_listbox.bind('<Double-Button-1>', lambda e: self.on_image_list_select("right"))
        
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
        
        # Update cursor now that canvases are initialized
        self.update_cursor_for_mode()
        
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
        self.root.bind("<Control-Shift-A>", lambda e: self.copy_keypoints_only())
        self.root.bind("<Control-Shift-a>", lambda e: self.copy_keypoints_only())
        self.root.bind("<Control-Shift-V>", lambda e: self.copy_visibility_only())
        self.root.bind("<Control-Shift-v>", lambda e: self.copy_visibility_only())
        
        # Additional keyboard shortcuts - Edit modes: q=Drag, w=Move, e=Add, r=Delete
        self.root.bind("<KeyPress-q>", lambda e: self.set_mode("drag"))
        self.root.bind("<KeyPress-Q>", lambda e: self.set_mode("drag"))
        self.root.bind("<KeyPress-w>", lambda e: self.set_mode("move"))
        self.root.bind("<KeyPress-W>", lambda e: self.set_mode("move"))
        self.root.bind("<KeyPress-e>", lambda e: self.set_mode("add"))
        self.root.bind("<KeyPress-E>", lambda e: self.set_mode("add"))
        self.root.bind("<KeyPress-r>", lambda e: self.set_mode("delete"))
        self.root.bind("<KeyPress-R>", lambda e: self.set_mode("delete"))
        self.root.bind("?", lambda e: self.show_shortcuts())
        self.root.bind("<Shift-?>", lambda e: self.show_shortcuts())
        self.root.bind("<space>", lambda e: self.toggle_skeleton())
        self.root.bind("<Tab>", lambda e: self.switch_active_side())
        self.root.bind("<Escape>", lambda e: self.deselect_keypoint())
        
        # BOTTOM STATUS BAR - slate-800 background, white text, ~40px height
        status_frame = tk.Frame(self.root, bg='#1E293B', height=40, relief=tk.FLAT, bd=0)  # slate-800
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        status_content = tk.Frame(status_frame, bg='#1E293B')
        status_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # Left: Mode and Zoom display
        left_status = tk.Frame(status_content, bg='#1E293B')
        left_status.pack(side=tk.LEFT)
        
        self.mode_label = tk.Label(left_status, text="Mode: Move", 
                                   font=(self.font_family, 9), bg='#1E293B', fg='#FFFFFF',
                                   relief=tk.FLAT, anchor='w', padx=0)
        self.mode_label.pack(side=tk.LEFT, padx=(0, 16))
        
        self.zoom_label = tk.Label(left_status, text="Zoom: 100%", 
                                   font=(self.font_family, 9), bg='#1E293B', fg='#FFFFFF',
                                   relief=tk.FLAT, anchor='w')
        self.zoom_label.pack(side=tk.LEFT)
        
        # Center: Zoom controls (ZoomOut, slider, ZoomIn)
        center_status = tk.Frame(status_content, bg='#1E293B')
        center_status.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=40)
        
        zoom_out_btn = tk.Button(center_status, text="−", 
                                 font=(self.font_family, 14, 'bold'),
                                 bg='#334155', fg='#FFFFFF',  # slate-700
                                 activebackground='#475569', activeforeground='#FFFFFF',
                                 relief=tk.FLAT, bd=0, padx=8, pady=2, cursor='hand2',
                                 command=lambda: self.adjust_zoom(-10),
                                 highlightthickness=0)
        zoom_out_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Zoom slider
        self.zoom_var = tk.IntVar(value=100)
        zoom_slider = ttk.Scale(center_status, from_=25, to=200, 
                               variable=self.zoom_var, orient=tk.HORIZONTAL,
                               command=self.on_zoom_change,
                               style='Modern.Horizontal.TScale',
                               length=200)
        zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        
        zoom_in_btn = tk.Button(center_status, text="+", 
                                font=(self.font_family, 14, 'bold'),
                                bg='#334155', fg='#FFFFFF',  # slate-700
                                activebackground='#475569', activeforeground='#FFFFFF',
                                relief=tk.FLAT, bd=0, padx=8, pady=2, cursor='hand2',
                                command=lambda: self.adjust_zoom(10),
                                highlightthickness=0)
        zoom_in_btn.pack(side=tk.LEFT, padx=(8, 0))
        
        # Right: Keyboard shortcut hint
        right_status = tk.Frame(status_content, bg='#1E293B')
        right_status.pack(side=tk.RIGHT)
        
        shortcut_label = tk.Label(right_status, text="Press ? for shortcuts", 
                                  font=(self.font_family, 9), bg='#1E293B', fg='#94A3B8',  # slate-400
                                  relief=tk.FLAT, anchor='e')
        shortcut_label.pack(side=tk.RIGHT)
        
        # Keep coord labels for internal use (hidden)
        self.coord_labels = {
            "left": tk.Label(status_content, text="", 
                           font=(self.font_family, 1), bg='#1E293B', fg='#1E293B'),
            "right": tk.Label(status_content, text="", 
                            font=(self.font_family, 1), bg='#1E293B', fg='#1E293B')
        }
        
        # Status bar for messages (hidden, used internally)
        self.status_bar = tk.Label(status_content, text="", 
                                   font=(self.font_family, 1), bg='#1E293B', fg='#1E293B')
        
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
        """Handle active side change"""
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
            # Extract folder name (last part of path)
            folder_name = os.path.basename(os.path.normpath(folder))
            # Update the visible label with folder name
            if side == "left" and hasattr(self, 'left_folder_label'):
                self.left_folder_label.config(text=folder_name)
            elif side == "right" and hasattr(self, 'right_folder_label'):
                self.right_folder_label.config(text=folder_name)
            # Also update hidden labels for compatibility
            display_path = folder if len(folder) <= 50 else "..." + folder[-47:]
            self.image_folder_labels[side].config(text=f"Folder: {display_path}")
            # Also update canvas label
            if side == "left" and hasattr(self, 'left_folder_label_canvas'):
                self.left_folder_label_canvas.config(text=f"Folder: {display_path}")
            elif side == "right" and hasattr(self, 'right_folder_label_canvas'):
                self.right_folder_label_canvas.config(text=f"Folder: {display_path}")
            # Reset to first image when folder changes
            self.current_image_indices[side] = 0
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
        self.update_image_listbox(side)
        
        # Always load the current image (at current index) when image list is loaded/refreshed
        # This ensures the image updates immediately when folder changes
        if self.image_lists[side]:
            # Make sure index is valid
            if self.current_image_indices[side] >= len(self.image_lists[side]):
                self.current_image_indices[side] = 0
            # Load the image at the current index
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
                # Extract file name (last part of path)
                file_name = os.path.basename(file)
                # Update the visible label with file name
                if side == "left" and hasattr(self, 'left_annotation_label'):
                    self.left_annotation_label.config(text=file_name)
                elif side == "right" and hasattr(self, 'right_annotation_label'):
                    self.right_annotation_label.config(text=file_name)
                # Also update hidden labels for compatibility
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
    
    def find_matching_annotation(self, side, image_rel_path, image_path, image_folder=None):
        """Find matching annotation by checking the 'image' field in JSON annotations"""
        if not self.annotations_data[side]:
            return None
        
        # Normalize both paths
        normalized_rel_path = self.normalize_path(image_rel_path) if image_rel_path else None
        normalized_image_path = self.normalize_path(image_path) if image_path else None
        
        # Use image_path (from image_lists) which contains folder structure, 
        # fallback to image_rel_path if image_path is not available
        path_to_match = normalized_image_path if normalized_image_path else normalized_rel_path
        if not path_to_match:
            return None
        
        filename = os.path.basename(path_to_match)
        
        # Extract folder name from image_folder to help with matching
        folder_name = None
        if image_folder:
            # Get the last folder name (e.g., "DL_001" from "C:/path/DL/DL_001")
            folder_name = os.path.basename(os.path.normpath(image_folder))
            folder_name = self.normalize_path(folder_name)
        
        # Helper function to extract folder from annotation image path
        def get_annotation_folder(ann):
            """Extract folder name from annotation's image path"""
            ann_image = ann.get('image', '')
            if not ann_image:
                return None
            normalized_ann_image = self.normalize_path(ann_image)
            ann_parts = normalized_ann_image.split('/')
            if len(ann_parts) > 1:
                return ann_parts[-2]  # Return folder name (e.g., "DL_001")
            return None
        
        # Helper function to check if annotation matches folder
        def folder_matches(ann, required_folder):
            """Check if annotation's folder matches the required folder_name"""
            if not required_folder:
                return True  # No folder specified, accept any
            ann_folder = get_annotation_folder(ann)
            return ann_folder == required_folder
        
        # Strategy 1: Exact match with normalized paths (but verify folder if available)
        if normalized_rel_path and normalized_rel_path in self.annotation_dicts[side]:
            ann = self.annotation_dicts[side][normalized_rel_path]
            if folder_matches(ann, folder_name):
                return ann
        
        if normalized_image_path and normalized_image_path in self.annotation_dicts[side]:
            ann = self.annotation_dicts[side][normalized_image_path]
            if folder_matches(ann, folder_name):
                return ann
        
        # Strategy 2: Check all annotations for path matches
        # This handles cases where JSON has "DL/DL_001/frame_000000.jpg" 
        # but path_to_match is "DL_001/frame_000000.jpg" or "DL/DL_001/frame_000000.jpg"
        best_match = None
        best_match_score = 0
        
        for ann_path, ann in self.annotation_dicts[side].items():
            # CRITICAL: Filter by folder FIRST before doing any path matching
            # This ensures we only consider annotations from the correct folder
            if not folder_matches(ann, folder_name):
                continue
            
            ann_image = ann.get('image', '')
            if not ann_image:
                continue
            
            normalized_ann_image = self.normalize_path(ann_image)
            ann_parts = normalized_ann_image.split('/')
            
            # Check if annotation path ends with the path we're matching
            # This handles: "DL/DL_001/frame_000000.jpg" matches "DL_001/frame_000000.jpg"
            if normalized_ann_image.endswith(path_to_match):
                # Verify it's a proper path match by checking path segments
                match_parts = path_to_match.split('/')
                
                # Match if the last N parts of ann_image exactly match path_to_match
                if len(ann_parts) >= len(match_parts):
                    if ann_parts[-len(match_parts):] == match_parts:
                        # Score by how many path segments match (prefer longer matches)
                        score = len(match_parts)
                        if best_match is None or score > best_match_score:
                            best_match = ann
                            best_match_score = score
            
            # Also check if path_to_match ends with parts of ann_image
            # This handles: "DL/DL_001/frame_000000.jpg" matching "DL_001/frame_000000.jpg"
            elif path_to_match.endswith(normalized_ann_image):
                match_parts = path_to_match.split('/')
                
                if len(match_parts) >= len(ann_parts):
                    if match_parts[-len(ann_parts):] == ann_parts:
                        score = len(ann_parts)
                        if best_match is None or score > best_match_score:
                            best_match = ann
                            best_match_score = score
        
        if best_match:
            return best_match
        
        # Strategy 3: Match by filename with STRICT folder verification
        # This is the fallback when path matching doesn't work
        # CRITICAL: Only match if folder_name is available and matches exactly
        if folder_name:
            # Search all annotations for matching filename AND folder
            for ann_path, ann in self.annotation_dicts[side].items():
                # CRITICAL: Filter by folder FIRST
                if not folder_matches(ann, folder_name):
                    continue
                
                ann_image = ann.get('image', '')
                if not ann_image:
                    continue
                
                normalized_ann_image = self.normalize_path(ann_image)
                ann_parts = normalized_ann_image.split('/')
                
                # Check if filename matches
                if len(ann_parts) > 0 and ann_parts[-1] == filename:
                    return ann
        
        # Fallback: if no folder_name available, try filename match (less reliable)
        # But this should rarely happen if folder selection is working correctly
        if filename in self.annotation_dicts[side] and not folder_name:
            return self.annotation_dicts[side][filename]
        
        return None
    
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
                # Try to find matching annotation using improved matching logic
                # Pass the image folder to help with matching
                matched_annotation = self.find_matching_annotation(side, image_rel_path, image_path, self.image_folders[side])
                
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
            
            # Reset zoom state when loading new image
            # This ensures scale factors are recalculated correctly
            self.zoom_modes[side] = False
            self.selected_keypoints[side] = None
            self.undo_stacks[side].clear()
            self.redo_stacks[side].clear()
            
            # Clear image cache to force recalculation
            self._image_cache[side] = None
            
            self.display_image(side)
            self.update_keypoint_list(side)
            self.update_image_index_label(side)
            self.update_progress(side)
            self.update_image_listbox(side)  # Update image listbox to highlight current image
            
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
        
        # Check for invalid image dimensions to prevent division by zero
        if img_width <= 0 or img_height <= 0:
            self.update_status(f"Invalid image dimensions: {img_width}x{img_height}")
            return
        
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
            # Ensure we don't divide by zero
            if img_width > 0 and img_height > 0:
                scale_w = (min_canvas_width - 40) / img_width
                scale_h = (min_canvas_height - 40) / img_height
                calculated_scale = min(scale_w, scale_h, 1.0)
            else:
                calculated_scale = 1.0
            
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
        
        # Draw grid overlay if enabled
        if hasattr(self, 'show_grid') and self.show_grid:
            self.draw_grid(side)
        
        self.draw_keypoints(side)
    
    def draw_grid(self, side):
        """Draw grid overlay on canvas - aligned to image coordinates for symmetry"""
        canvas = self.canvases[side]
        if not self.current_images[side]:
            return
        
        img_width, img_height = self.current_images[side].size
        scale_factor = self.scale_factors[side]
        
        # Grid spacing in image coordinates (50 pixels)
        grid_spacing_image = 50
        
        # Calculate display dimensions
        display_width = int(img_width * scale_factor)
        display_height = int(img_height * scale_factor)
        
        # Draw vertical lines - based on image coordinates, then scaled
        # Start from 0 and draw lines at multiples of grid_spacing_image
        x_image = 0
        while x_image <= img_width:
            x_display = x_image * scale_factor
            canvas.create_line(x_display, 0, x_display, display_height, 
                             fill='#CBD5E1', width=1, 
                             tags='grid', stipple='gray25')
            x_image += grid_spacing_image
        
        # Draw horizontal lines - based on image coordinates, then scaled
        # Start from 0 and draw lines at multiples of grid_spacing_image
        y_image = 0
        while y_image <= img_height:
            y_display = y_image * scale_factor
            canvas.create_line(0, y_display, display_width, y_display, 
                             fill='#CBD5E1', width=1, 
                             tags='grid', stipple='gray25')
            y_image += grid_spacing_image
    
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
                
                # Validate and clamp coordinates to image bounds
                if self.current_images[side]:
                    x = max(0, min(x, self.current_images[side].width))
                    y = max(0, min(y, self.current_images[side].height))
                else:
                    if x < 0 or y < 0:
                        continue
                
                # Convert image coordinates to display coordinates
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
            
            # Scale keypoint radius with zoom for better visibility
            # Base radius scales with zoom, but with reasonable min/max limits
            base_radius = self.keypoint_radius
            radius = max(2, min(12, base_radius * scale_factor))  # Reduced limits for smaller dots
            
            # Highlight selected keypoint
            if is_selected:
                outline_color = '#FFFF00'  # Yellow highlight
                outline_width = max(1, int(2 * scale_factor))  # Reduced for smaller dots
                highlight_radius = radius + max(1, int(2 * scale_factor))  # Reduced highlight size
                # Draw larger outer circle for selected
                canvas.create_oval(
                    display_x - highlight_radius, display_y - highlight_radius,
                    display_x + highlight_radius, display_y + highlight_radius,
                    outline='#FFFF00', width=outline_width, tags=f"keypoint_{idx}_highlight"
                )
            
            # Scale outline width with zoom (reduced for smaller dots)
            scaled_outline_width = max(1, int(outline_width * scale_factor * 0.7))  # 30% thinner outline
            canvas.create_oval(
                display_x - radius, display_y - radius,
                display_x + radius, display_y + radius,
                fill=fill_color, outline=outline_color, width=scaled_outline_width,
                tags=f"keypoint_{idx}"
            )
            
            if self.show_keypoint_labels:
                label = self.keypoint_names[idx % len(self.keypoint_names)]
                # Label offset scales with radius to maintain proper spacing
                label_offset = radius + max(8, int(10 * scale_factor))
                # Scale font size with zoom for better readability (but with limits)
                font_size = max(8, min(14, int(8 * scale_factor)))
                canvas.create_text(
                    display_x, display_y - label_offset,
                    text=label, fill=color, font=('Arial', font_size, 'bold'),
                    tags=f"keypoint_{idx}"
                )
    
    def on_canvas_click(self, event, side):
        """Handle canvas click - both sides work simultaneously"""
        # Set active side for navigation/undo purposes, but allow operations on both sides
        if side != self.active_side:
            self.set_active_side(side)
        
        self.canvases[side].focus_set()
        
        mode = self.edit_mode.get()
        
        # Handle drag mode (panning) - doesn't require annotations
        if mode == "drag":
            # Start panning by marking the current position
            self.canvases[side].scan_mark(event.x, event.y)
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            return
        
        if not self.current_annotations[side]:
            return
        
        if self.scale_factors[side] <= 0:
            return
        
        # Initialize drag tracking
        self._was_dragging = False
        
        canvas_x = self.canvases[side].canvasx(event.x)
        canvas_y = self.canvases[side].canvasy(event.y)
        
        # Convert canvas coordinates to image coordinates
        if self.scale_factors[side] > 0:
            img_x = canvas_x / self.scale_factors[side]
            img_y = canvas_y / self.scale_factors[side]
        else:
            return
        
        # Validate coordinates are within image bounds
        if self.current_images[side]:
            img_x = max(0, min(img_x, self.current_images[side].width))
            img_y = max(0, min(img_y, self.current_images[side].height))
        
        if mode == "move":
            nearest_idx = self.find_nearest_keypoint(side, img_x, img_y)
            # Always update selection, even if None (to deselect)
            old_selection = self.selected_keypoints[side]
            self.selected_keypoints[side] = nearest_idx
            # Update display immediately to show selection change
            if nearest_idx != old_selection:
                self.display_image(side)
                self.update_keypoint_list(side)
        
        elif mode == "add":
            self.save_state(side)
            if 'keypoints' not in self.current_annotations[side]:
                self.current_annotations[side]['keypoints'] = []
            
            # Store coordinates with precision (round to 1 decimal place for consistency)
            img_x = round(img_x, 1)
            img_y = round(img_y, 1)
            
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
        mode = self.edit_mode.get()
        
        # Handle drag mode (panning)
        if mode == "drag":
            # Pan the canvas by dragging
            self.canvases[side].scan_dragto(event.x, event.y, gain=1)
            return
        
        if self.selected_keypoints[side] is not None and mode == "move":
            self._was_dragging = True  # Mark that we're dragging
            if self.scale_factors[side] <= 0:
                return
            
            if not hasattr(self, '_drag_state_saved'):
                self.save_state(side)
                self._drag_state_saved = True
            
            canvas_x = self.canvases[side].canvasx(event.x)
            canvas_y = self.canvases[side].canvasy(event.y)
            
            # Convert canvas coordinates to image coordinates
            if self.scale_factors[side] > 0:
                img_x = canvas_x / self.scale_factors[side]
                img_y = canvas_y / self.scale_factors[side]
            else:
                return
            
            # Validate coordinates are within image bounds
            if self.current_images[side]:
                img_x = max(0, min(img_x, self.current_images[side].width))
                img_y = max(0, min(img_y, self.current_images[side].height))
            
            # Round coordinates for consistency
            img_x = round(img_x, 1)
            img_y = round(img_y, 1)
            
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
        mode = self.edit_mode.get()
        
        # Clear drag tracking for drag mode
        if mode == "drag":
            self._drag_start_x = None
            self._drag_start_y = None
            return
        
        if hasattr(self, '_drag_state_saved'):
            delattr(self, '_drag_state_saved')
        # Don't deselect on release - keep selection for editing
        # Only clear _was_dragging flag if it exists
        if hasattr(self, '_was_dragging'):
            delattr(self, '_was_dragging')
    
    def on_canvas_right_click(self, event, side):
        """Handle right-click - show context menu"""
        if self.scale_factors[side] <= 0:
            return
        
        canvas_x = self.canvases[side].canvasx(event.x)
        canvas_y = self.canvases[side].canvasy(event.y)
        
        # Convert canvas coordinates to image coordinates
        if self.scale_factors[side] > 0:
            img_x = canvas_x / self.scale_factors[side]
            img_y = canvas_y / self.scale_factors[side]
        else:
            return
        
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
    
    def toggle_grid(self):
        """Toggle grid overlay on both canvases"""
        if not hasattr(self, 'show_grid'):
            self.show_grid = False
        self.show_grid = not self.show_grid
        # Redraw both canvases to show/hide grid
        for side in ["left", "right"]:
            if self.current_images[side]:
                self.display_image(side, force=True)
    
    def adjust_zoom(self, delta):
        """Adjust zoom by delta percentage"""
        current_zoom = self.zoom_var.get()
        new_zoom = max(25, min(200, current_zoom + delta))
        self.zoom_var.set(new_zoom)
        self.on_zoom_change(new_zoom)
    
    def on_zoom_change(self, value):
        """Handle zoom slider change"""
        try:
            zoom_percent = int(float(value))
            self.zoom_label.config(text=f"Zoom: {zoom_percent}%")
            # Apply zoom to active side canvas
            side = self.active_side
            if self.current_images[side]:
                # Convert percentage to scale factor
                # Base scale is 1.0, so zoom_percent/100 gives the multiplier
                zoom_factor = zoom_percent / 100.0
                
                # Get base scale (fit-to-window scale)
                if self.base_scale_factors[side] > 0:
                    # Apply zoom multiplier to base scale
                    self.scale_factors[side] = self.base_scale_factors[side] * zoom_factor
                    self.zoom_modes[side] = (zoom_percent != 100)
                    self.display_image(side, force=True)
        except Exception as e:
            pass
    
    def reset_zoom(self):
        """Reset zoom to fit-to-window for active side"""
        side = self.active_side
        if not self.current_images[side]:
            return
        
        # Reset to base scale factor
        self.scale_factors[side] = self.base_scale_factors[side]
        self.zoom_modes[side] = False
        self.display_image(side, force=True)
    
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
        """Update image index label - labels are hidden in navigation, only shown on canvas"""
        if self.image_lists[side]:
            # Update navigation label on canvas
            if side == "left":
                canvas_text = f"Left: {self.current_image_indices[side] + 1}/{len(self.image_lists[side])}"
                self.left_nav_label.config(text=canvas_text)
            else:
                canvas_text = f"Right: {self.current_image_indices[side] + 1}/{len(self.image_lists[side])}"
                self.right_nav_label.config(text=canvas_text)
        else:
            # No images loaded
            if side == "left":
                self.left_nav_label.config(text="Left: 0/0")
            else:
                self.right_nav_label.config(text="Right: 0/0")
    
    def update_image_listbox(self, side):
        """Update the image listbox with current image list"""
        if side == "left":
            if not hasattr(self, 'left_image_listbox'):
                return
            listbox = self.left_image_listbox
        else:
            if not hasattr(self, 'right_image_listbox'):
                return
            listbox = self.right_image_listbox
        
        # Clear existing items
        listbox.delete(0, tk.END)
        
        # Add images to listbox
        if self.image_lists[side]:
            for idx, image_path in enumerate(self.image_lists[side]):
                # Show just the filename or relative path (truncate if too long)
                display_name = os.path.basename(image_path)
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                listbox.insert(tk.END, f"{idx+1:4d}. {display_name}")
            
            # Highlight current image
            if 0 <= self.current_image_indices[side] < len(self.image_lists[side]):
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(self.current_image_indices[side])
                listbox.see(self.current_image_indices[side])
    
    def on_image_list_select(self, side):
        """Handle image selection from image listbox"""
        if side == "left":
            if not hasattr(self, 'left_image_listbox'):
                return
            listbox = self.left_image_listbox
        else:
            if not hasattr(self, 'right_image_listbox'):
                return
            listbox = self.right_image_listbox
        
        selection = listbox.curselection()
        if selection and self.image_lists[side]:
            selected_idx = selection[0]
            if 0 <= selected_idx < len(self.image_lists[side]):
                self.current_image_indices[side] = selected_idx
                self.load_current_image(side)
                self.update_status(f"Jumped to image {selected_idx + 1}/{len(self.image_lists[side])} ({side})")
    
    def update_progress(self, side):
        """Update progress for a side"""
        if not self.image_lists[side]:
            self.progress_labels[side].config(text=f"Progress: 0/0 (0%)")
            return
        
        # Progress is no longer shown in navigation section
        # This function is kept for compatibility but doesn't update navigation labels
        pass
    
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
        # Update cursor for drag mode
        self.update_cursor_for_mode()
    
    def update_mode_buttons(self):
        """Update mode button appearance - slate-800 when active (matching React design)"""
        mode = self.edit_mode.get()
        
        # Reset all buttons to default state (slate-100)
        self.drag_button.config(bg='#F1F5F9', fg='#334155', relief=tk.FLAT)
        self.move_button.config(bg='#F1F5F9', fg='#334155', relief=tk.FLAT)
        self.add_button.config(bg='#F1F5F9', fg='#334155', relief=tk.FLAT)
        self.delete_button.config(bg='#F1F5F9', fg='#334155', relief=tk.FLAT)
        
        # Highlight active button with slate-800 background (matching React design)
        if mode == "drag":
            self.drag_button.config(bg='#1E293B', fg='#FFFFFF', relief=tk.FLAT)  # slate-800
        elif mode == "move":
            self.move_button.config(bg='#1E293B', fg='#FFFFFF', relief=tk.FLAT)  # slate-800
        elif mode == "add":
            self.add_button.config(bg='#1E293B', fg='#FFFFFF', relief=tk.FLAT)
        elif mode == "delete":
            self.delete_button.config(bg='#1E293B', fg='#FFFFFF', relief=tk.FLAT)
    
    def update_cursor_for_mode(self):
        """Update cursor based on current edit mode"""
        # Check if canvases are initialized
        if not hasattr(self, 'canvases') or not self.canvases:
            return
        
        mode = self.edit_mode.get()
        cursor = 'hand2'  # default
        
        if mode == "drag":
            cursor = 'fleur'  # pan/grabbing hand cursor
        elif mode == "move":
            cursor = 'hand2'
        elif mode == "add":
            cursor = 'crosshair'  # crosshair for adding points
        elif mode == "delete":
            cursor = 'X_cursor'  # X cursor for deletion
        
        # Update cursor for both canvases
        for side in ["left", "right"]:
            if side in self.canvases:
                self.canvases[side].config(cursor=cursor)
    
    def on_format_mode_change(self):
        """Handle format mode change"""
        old_mode = self.format_mode
        self.format_mode = self.format_mode_var.get()
        
        # Update format button states
        if hasattr(self, 'update_format_buttons'):
            self.update_format_buttons()
        
        if self.format_mode == "coco":
            self.visibility_frame.pack(fill=tk.X, padx=16, pady=(0, 0), before=None)
            self.visibility_guide_frame.pack(fill=tk.X, padx=16, pady=(0, 0), before=None)
            
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
        
        prev_annotation = self.find_matching_annotation(side, prev_rel_path, prev_image_path, self.image_folders[side])
        
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
    
    def copy_keypoints_only(self):
        """Copy only keypoint coordinates from previous frame, keeping current visibility"""
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
        
        prev_annotation = self.find_matching_annotation(side, prev_rel_path, prev_image_path, self.image_folders[side])
        
        if not prev_annotation:
            messagebox.showwarning("Warning", "No annotation found for previous image")
            return
        
        prev_keypoints = prev_annotation.get('keypoints', [])
        if not prev_keypoints:
            messagebox.showinfo("Info", "Previous image has no keypoints to copy")
            return
        
        current_keypoints = self.current_annotations[side].get('keypoints', [])
        
        # Copy only coordinates, preserve current visibility
        updated_count = 0
        for idx, prev_kp in enumerate(prev_keypoints):
            if prev_kp is None or not isinstance(prev_kp, (list, tuple)) or len(prev_kp) < 2:
                continue
            
            try:
                x, y = float(prev_kp[0]), float(prev_kp[1])
                if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    continue
                
                # Ensure current keypoints list is long enough
                while len(current_keypoints) <= idx:
                    current_keypoints.append(None)
                
                # Preserve existing visibility or use default
                if current_keypoints[idx] and isinstance(current_keypoints[idx], (list, tuple)) and len(current_keypoints[idx]) >= 3:
                    # Keep existing visibility
                    visibility = int(current_keypoints[idx][2])
                elif self.format_mode == "coco":
                    # Use default visibility for COCO mode
                    visibility = self.default_visibility
                else:
                    # Standard mode, no visibility
                    current_keypoints[idx] = [x, y]
                    updated_count += 1
                    continue
                
                current_keypoints[idx] = [x, y, visibility]
                updated_count += 1
            except (ValueError, TypeError):
                continue
        
        self.current_annotations[side]['keypoints'] = current_keypoints
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_progress(side)
        self.update_status(f"Copied keypoint coordinates from previous frame ({updated_count} updated)")
    
    def copy_visibility_only(self):
        """Copy only visibility values from previous frame, keeping current coordinates"""
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
        
        if self.format_mode != "coco":
            messagebox.showinfo("Info", "Visibility copying is only available in COCO mode")
            return
        
        self.save_state(side)
        
        prev_image_path = self.image_lists[side][self.current_image_indices[side] - 1]
        prev_full_path = os.path.join(self.image_folders[side], prev_image_path)
        prev_rel_path = self.get_relative_path(prev_full_path, self.image_folders[side])
        
        prev_annotation = self.find_matching_annotation(side, prev_rel_path, prev_image_path, self.image_folders[side])
        
        if not prev_annotation:
            messagebox.showwarning("Warning", "No annotation found for previous image")
            return
        
        prev_keypoints = prev_annotation.get('keypoints', [])
        if not prev_keypoints:
            messagebox.showinfo("Info", "Previous image has no keypoints to copy")
            return
        
        current_keypoints = self.current_annotations[side].get('keypoints', [])
        
        # Copy only visibility, preserve current coordinates
        updated_count = 0
        for idx, prev_kp in enumerate(prev_keypoints):
            if prev_kp is None or not isinstance(prev_kp, (list, tuple)) or len(prev_kp) < 3:
                continue
            
            try:
                visibility = int(prev_kp[2])
                if visibility not in [0, 1, 2]:
                    continue
                
                # Ensure current keypoints list is long enough
                while len(current_keypoints) <= idx:
                    current_keypoints.append(None)
                
                # Preserve existing coordinates
                if current_keypoints[idx] and isinstance(current_keypoints[idx], (list, tuple)) and len(current_keypoints[idx]) >= 2:
                    x, y = float(current_keypoints[idx][0]), float(current_keypoints[idx][1])
                    current_keypoints[idx] = [x, y, visibility]
                    updated_count += 1
                elif prev_kp and isinstance(prev_kp, (list, tuple)) and len(prev_kp) >= 2:
                    # If current doesn't exist but previous does, copy both coordinates and visibility
                    x, y = float(prev_kp[0]), float(prev_kp[1])
                    current_keypoints[idx] = [x, y, visibility]
                    updated_count += 1
            except (ValueError, TypeError):
                continue
        
        self.current_annotations[side]['keypoints'] = current_keypoints
        self.unsaved_changes[side] = True
        self.display_image(side)
        self.update_keypoint_list(side)
        self.update_progress(side)
        self.update_status(f"Copied visibility values from previous frame ({updated_count} updated)")
    
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
                
                prev_annotation = self.find_matching_annotation("left", prev_rel_path, prev_image_path, self.image_folders["left"])
                
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
                
                prev_annotation = self.find_matching_annotation("right", prev_rel_path, prev_image_path, self.image_folders["right"])
                
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
    
    def on_radius_change(self, value=None):
        """Handle keypoint radius slider change"""
        new_radius = int(self.radius_var.get())
        self.keypoint_radius = new_radius
        self.radius_value_label.config(text=str(new_radius))
        # Update display for both sides
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
    
    def save_to_coco_file(self, side, file_path):
        """Save annotations to COCO format file (helper function)"""
        if not self.annotations_data[side]:
            return False, f"No annotations to save for {side} side"
        
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
                visible_count = 0
                for kp in keypoints:
                    if len(kp) >= 2:
                        x, y = float(kp[0]), float(kp[1])
                        v = int(kp[2]) if len(kp) >= 3 else 2
                        coco_keypoints.extend([x, y, v])
                        # Count only visible keypoints (v > 0)
                        if v > 0:
                            visible_count += 1
                
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
                            "num_keypoints": visible_count,
                            "bbox": [x_min, y_min, bbox_width, bbox_height],
                            "area": bbox_width * bbox_height,
                            "iscrowd": 0
                        })
                        annotation_id += 1
            
            with open(file_path, 'w') as f:
                json.dump(coco_data, f, indent=2)
            
            return True, f"Saved {len(coco_data['annotations'])} annotations"
        except Exception as e:
            return False, f"Failed to save COCO format: {str(e)}"
    
    def save_both_sides(self):
        """Save both left and right sides in original and COCO formats (4 files total)"""
        results = []
        
        # Save Left side
        left_original_saved = False
        left_coco_saved = False
        
        if self.annotations_data["left"]:
            # Save left original format
            if self.annotation_files["left"]:
                try:
                    if 'info' in self.annotations_data["left"]:
                        self.annotations_data["left"]["info"]["num_images"] = len(self.annotations_data["left"]["annotations"])
                        if self.annotations_data["left"]["annotations"]:
                            max_kp = max(len(ann.get('keypoints', [])) for ann in self.annotations_data["left"]["annotations"])
                            self.annotations_data["left"]["info"]["num_keypoints"] = max_kp
                    
                    with open(self.annotation_files["left"], 'w') as f:
                        json.dump(self.annotations_data["left"], f, indent=2)
                    
                    self.unsaved_changes["left"] = False
                    import time
                    self.last_save_times["left"] = time.time()
                    left_original_saved = True
                    results.append(f"Left original: {os.path.basename(self.annotation_files['left'])}")
                except Exception as e:
                    results.append(f"Left original: ERROR - {str(e)}")
            else:
                results.append("Left original: No file path set")
            
            # Save left COCO format
            if self.annotation_files["left"]:
                coco_path = os.path.splitext(self.annotation_files["left"])[0] + "_coco.json"
            else:
                # Try to determine from annotation data
                if self.annotations_data["left"].get('annotations'):
                    # Use a default path
                    coco_path = "left_annotations_coco.json"
                else:
                    coco_path = None
            
            if coco_path:
                success, message = self.save_to_coco_file("left", coco_path)
                if success:
                    self.coco_annotation_files["left"] = coco_path
                    left_coco_saved = True
                    results.append(f"Left COCO: {os.path.basename(coco_path)}")
                else:
                    results.append(f"Left COCO: ERROR - {message}")
            else:
                results.append("Left COCO: No file path available")
        else:
            results.append("Left: No annotations to save")
        
        # Save Right side
        right_original_saved = False
        right_coco_saved = False
        
        if self.annotations_data["right"]:
            # Save right original format
            if self.annotation_files["right"]:
                try:
                    if 'info' in self.annotations_data["right"]:
                        self.annotations_data["right"]["info"]["num_images"] = len(self.annotations_data["right"]["annotations"])
                        if self.annotations_data["right"]["annotations"]:
                            max_kp = max(len(ann.get('keypoints', [])) for ann in self.annotations_data["right"]["annotations"])
                            self.annotations_data["right"]["info"]["num_keypoints"] = max_kp
                    
                    with open(self.annotation_files["right"], 'w') as f:
                        json.dump(self.annotations_data["right"], f, indent=2)
                    
                    self.unsaved_changes["right"] = False
                    import time
                    self.last_save_times["right"] = time.time()
                    right_original_saved = True
                    results.append(f"Right original: {os.path.basename(self.annotation_files['right'])}")
                except Exception as e:
                    results.append(f"Right original: ERROR - {str(e)}")
            else:
                results.append("Right original: No file path set")
            
            # Save right COCO format
            if self.annotation_files["right"]:
                coco_path = os.path.splitext(self.annotation_files["right"])[0] + "_coco.json"
            else:
                # Try to determine from annotation data
                if self.annotations_data["right"].get('annotations'):
                    # Use a default path
                    coco_path = "right_annotations_coco.json"
                else:
                    coco_path = None
            
            if coco_path:
                success, message = self.save_to_coco_file("right", coco_path)
                if success:
                    self.coco_annotation_files["right"] = coco_path
                    right_coco_saved = True
                    results.append(f"Right COCO: {os.path.basename(coco_path)}")
                else:
                    results.append(f"Right COCO: ERROR - {message}")
            else:
                results.append("Right COCO: No file path available")
        else:
            results.append("Right: No annotations to save")
        
        # Update save indicators and labels
        if left_original_saved:
            self.save_indicators["left"].config(text="✓ Saved", foreground="green")
            self.root.after(2000, lambda: self.save_indicators["left"].config(text=""))
            
            # Update left annotation label to show both files
            if self.annotation_files["left"] and self.coco_annotation_files["left"]:
                std_path = self.annotation_files["left"]
                coco_path = self.coco_annotation_files["left"]
                std_display = std_path if len(std_path) <= 40 else "..." + std_path[-37:]
                coco_display = coco_path if len(coco_path) <= 40 else "..." + coco_path[-37:]
                self.annotation_labels["left"].config(text=f"Standard: {std_display} | COCO: {coco_display}")
                if hasattr(self, 'left_annotation_label_canvas'):
                    self.left_annotation_label_canvas.config(text=f"Standard: {std_display} | COCO: {coco_display}")
        
        if right_original_saved and self.save_indicators["right"]:
            self.save_indicators["right"].config(text="✓ Saved", foreground="green")
            self.root.after(2000, lambda: self.save_indicators["right"].config(text=""))
            
            # Update right annotation label to show both files
            if self.annotation_files["right"] and self.coco_annotation_files["right"]:
                std_path = self.annotation_files["right"]
                coco_path = self.coco_annotation_files["right"]
                std_display = std_path if len(std_path) <= 40 else "..." + std_path[-37:]
                coco_display = coco_path if len(coco_path) <= 40 else "..." + coco_path[-37:]
                self.annotation_labels["right"].config(text=f"Standard: {std_display} | COCO: {coco_display}")
                if hasattr(self, 'right_annotation_label_canvas'):
                    self.right_annotation_label_canvas.config(text=f"Standard: {std_display} | COCO: {coco_display}")
        
        # Update status and show message
        result_text = "\n".join(results)
        saved_count = sum([left_original_saved, left_coco_saved, right_original_saved, right_coco_saved])
        
        self.update_status(f"Saved {saved_count} files: {result_text}")
        
        if saved_count > 0:
            messagebox.showinfo("Save Both Complete", 
                              f"Saved {saved_count} file(s):\n\n{result_text}")
        else:
            messagebox.showwarning("Warning", 
                                 f"Could not save files:\n\n{result_text}")
    
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
                visible_count = 0
                for kp in keypoints:
                    if len(kp) >= 2:
                        x, y = float(kp[0]), float(kp[1])
                        v = int(kp[2]) if len(kp) >= 3 else 2
                        coco_keypoints.extend([x, y, v])
                        # Count only visible keypoints (v > 0)
                        if v > 0:
                            visible_count += 1
                
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
                            "num_keypoints": visible_count,
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
        """Open dialog to edit keypoint names - Modern UI"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Keypoint Names")
        dialog.geometry("700x750")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.config(bg='#F8FAFC')  # slate-50 background
        
        # Header
        header_frame = tk.Frame(dialog, bg='#FFFFFF', height=60, relief=tk.FLAT, bd=0)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg='#FFFFFF')
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)
        
        title_label = tk.Label(header_content, text="Edit Keypoint Names", 
                               font=(self.font_family, 18, 'bold'),
                               bg='#FFFFFF', fg='#1E293B', anchor='w')
        title_label.pack(side=tk.LEFT)
        
        # Main content area
        main_frame = tk.Frame(dialog, bg='#F8FAFC')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure modern notebook tab styling
        style = ttk.Style()
        style.configure('Modern.TNotebook', 
                       background='#F8FAFC',
                       borderwidth=0)
        style.configure('Modern.TNotebook.Tab',
                       background='#F1F5F9',  # slate-100
                       foreground='#475569',  # slate-600
                       padding=[20, 12],
                       borderwidth=0,
                       font=(self.font_family, 10))
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', '#FFFFFF'),  # white when selected
                           ('active', '#E2E8F0')],  # slate-200 on hover
                 foreground=[('selected', '#1E293B'),  # slate-800 when selected
                           ('active', '#334155')])  # slate-700 on hover
        
        # Create notebook for tabs with modern styling
        notebook = ttk.Notebook(main_frame, style='Modern.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Dictionary format input
        dict_frame = tk.Frame(notebook, bg='#FFFFFF')
        notebook.add(dict_frame, text="Dictionary Format")
        
        dict_inner = tk.Frame(dict_frame, bg='#FFFFFF')
        dict_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        dict_label = tk.Label(dict_inner, text="Paste or edit dictionary format:", 
                             font=(self.font_family, 11, 'bold'),
                             bg='#FFFFFF', fg='#1E293B', anchor='w')
        dict_label.pack(anchor=tk.W, pady=(0, 12))
        
        # Text area for dictionary input with modern styling
        text_container = tk.Frame(dict_inner, bg='#F1F5F9', relief=tk.FLAT, bd=1)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        text_frame = tk.Frame(text_container, bg='#FFFFFF')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        dict_text = tk.Text(text_frame, wrap=tk.WORD, 
                           font=(self.font_family, 10), 
                           bg='#FFFFFF', fg='#1E293B',
                           relief=tk.FLAT, bd=0,
                           insertbackground='#2563EB',
                           selectbackground='#DBEAFE',
                           selectforeground='#1E293B',
                           height=20)
        dict_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                      command=dict_text.yview,
                                      style='Modern.Vertical.TScrollbar')
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
        fields_frame = tk.Frame(notebook, bg='#FFFFFF')
        notebook.add(fields_frame, text="Individual Fields")
        
        fields_inner = tk.Frame(fields_frame, bg='#FFFFFF')
        fields_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        fields_label = tk.Label(fields_inner, text="Edit individual keypoint names:", 
                               font=(self.font_family, 11, 'bold'),
                               bg='#FFFFFF', fg='#1E293B', anchor='w')
        fields_label.pack(anchor=tk.W, pady=(0, 12))
        
        # Scrollable frame for individual fields
        scroll_container = tk.Frame(fields_inner, bg='#F1F5F9', relief=tk.FLAT, bd=1)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(scroll_container, bg='#FFFFFF', highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", 
                                 command=canvas.yview,
                                 style='Modern.Vertical.TScrollbar')
        scrollable_frame = tk.Frame(canvas, bg='#FFFFFF')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Entry fields for each keypoint with modern styling
        entry_vars = []
        for i in range(len(self.keypoint_names)):
            row_frame = tk.Frame(scrollable_frame, bg='#FFFFFF')
            row_frame.pack(fill=tk.X, pady=4, padx=8)
            
            kp_label = tk.Label(row_frame, text=f"KP{i}:", 
                               font=(self.font_family, 10),
                               bg='#FFFFFF', fg='#475569', width=8, anchor='w')
            kp_label.pack(side=tk.LEFT, padx=(0, 12))
            
            var = tk.StringVar(value=self.keypoint_names[i])
            entry = tk.Entry(row_frame, textvariable=var, 
                            font=(self.font_family, 10),
                            bg='#FFFFFF', fg='#1E293B',
                            relief=tk.FLAT, bd=1,
                            highlightthickness=1,
                            highlightcolor='#2563EB',
                            highlightbackground='#CBD5E1',
                            insertbackground='#2563EB',
                            selectbackground='#DBEAFE',
                            selectforeground='#1E293B')
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True, ipady=6)
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
        
        
        # Bottom button frame - all buttons in one row
        bottom_frame = tk.Frame(dialog, bg='#F8FAFC')
        bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side buttons
        left_buttons = tk.Frame(bottom_frame, bg='#F8FAFC')
        left_buttons.pack(side=tk.LEFT)
        
        load_btn = tk.Button(left_buttons, text="Load from Dictionary", 
                           command=load_from_dict,
                           font=(self.font_family, 10),
                           bg='#F1F5F9', fg='#475569',
                           activebackground='#E2E8F0', activeforeground='#1E293B',
                           relief=tk.FLAT, bd=0, padx=16, pady=10,
                           cursor='hand2', highlightthickness=0)
        load_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        save_dict_btn = tk.Button(left_buttons, text="Save from Dictionary", 
                                 command=save_from_dict,
                                 font=(self.font_family, 10, 'bold'),
                                 bg='#2563EB', fg='#FFFFFF',
                                 activebackground='#1D4ED8', activeforeground='#FFFFFF',
                                 relief=tk.FLAT, bd=0, padx=16, pady=10,
                                 cursor='hand2', highlightthickness=0)
        save_dict_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        save_fields_btn = tk.Button(left_buttons, text="Save", 
                                   command=save_from_fields,
                                   font=(self.font_family, 10, 'bold'),
                                   bg='#2563EB', fg='#FFFFFF',
                                   activebackground='#1D4ED8', activeforeground='#FFFFFF',
                                   relief=tk.FLAT, bd=0, padx=16, pady=10,
                                   cursor='hand2', highlightthickness=0)
        save_fields_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        reset_btn = tk.Button(left_buttons, text="Reset to Default", 
                             command=lambda: self.reset_keypoint_names(entry_vars, dict_text),
                             font=(self.font_family, 10),
                             bg='#F1F5F9', fg='#475569',
                             activebackground='#E2E8F0', activeforeground='#1E293B',
                             relief=tk.FLAT, bd=0, padx=16, pady=10,
                             cursor='hand2', highlightthickness=0)
        reset_btn.pack(side=tk.LEFT)
        
        # Right side button
        cancel_btn = tk.Button(bottom_frame, text="Cancel", 
                              command=dialog.destroy,
                              font=(self.font_family, 10),
                              bg='#F1F5F9', fg='#475569',
                              activebackground='#E2E8F0', activeforeground='#1E293B',
                              relief=tk.FLAT, bd=0, padx=16, pady=10,
                              cursor='hand2', highlightthickness=0)
        cancel_btn.pack(side=tk.RIGHT)
    
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
    
    def show_shortcuts(self):
        """Show keyboard shortcuts help dialog"""
        shortcuts_text = """Keyboard Shortcuts:

Edit Modes:
  Q - Drag (pan zoomed image)
  W - Move keypoints
  E - Add keypoint
  R - Delete keypoint

Navigation:
  ↑ / ↓ - Previous/Next image (active side)
  ← / → - Previous/Next image (both sides)
  Tab - Switch active side

Actions:
  Ctrl+C - Copy from previous frame
  Ctrl+B - Copy from previous frame (both sides)
  Ctrl+Z - Undo
  Ctrl+Y - Redo
  Ctrl+Shift+A - Copy keypoints only
  Ctrl+Shift+V - Copy visibility only

Other:
  Space - Toggle skeleton
  Escape - Deselect keypoint
  ? - Show this help"""
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)
    
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
                               font=(self.font_family, 8), relief=tk.SOLID, borderwidth=1,
                               padx=4, pady=2)
                label.pack()
                widget.tooltip = tooltip
            
            def on_leave(event):
                if hasattr(widget, 'tooltip'):
                    widget.tooltip.destroy()
                    del widget.tooltip
            
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
        
        # Add tooltips to mode buttons (if they exist)
        if hasattr(self, 'move_button') and self.move_button is not None:
            create_tooltip(self.move_button, "Move keypoints (M)")
        if hasattr(self, 'add_button') and self.add_button is not None:
            create_tooltip(self.add_button, "Add keypoint (A)")
        if hasattr(self, 'delete_button') and self.delete_button is not None:
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
