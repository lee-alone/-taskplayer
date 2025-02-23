import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import json
import os
from tkinter.font import Font
import pandas as pd  # 用于Excel导出
import threading
import time

# 检查必要依赖
try:
    import pygame
    from tkcalendar import Calendar
except ImportError as e:
    print(f"缺少必要的依赖库: {str(e)}")
    print("请运行以下命令安装依赖:")
    print("pip install pygame tkcalendar")
    sys.exit(1)

class AudioPlayer:
    def __init__(self):
        # 初始化音频系统
        pygame.init()
        pygame.mixer.init()
        
        # 初始化播放控制变量
        self.current_playing_sound = None
        self.paused = False
        self.current_playing_duration = 0
        self.current_playing_position = 0
        self.playing_thread = None
        self.stop_thread = False
        self.current_playing_item = None
        
        # 初始化主窗口
        self.root = tk.Tk()
        self.root.title("任务播放器")
        self.root.geometry("1200x800")  # 增加默认窗口大小
        
        # 设置图标
        self._set_icon()
        
        # 设置样式和UI组件
        self.setup_styles()
        
        # 创建主布局框架
        self.create_main_layout()
        
        # 设置组件
        self.setup_search_bar()
        self.setup_tree()
        self.setup_playback_controls()
        self.setup_status_bar()
        
        # 加载任务并启动检查
        self.load_tasks()
        self.update_time()
        self.check_tasks()
        
        # 配置窗口布局
        self.root.grid_rowconfigure(1, weight=1)  # 任务列表区域可扩展
        self.root.grid_columnconfigure(0, weight=1)

    def create_main_layout(self):
        """创建主要布局框架"""
        # 顶部搜索栏框架
        self.search_frame = ttk.Frame(self.root, padding="10")
        self.search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # 中间任务列表框架
        self.task_frame = ttk.Frame(self.root, padding="10")
        self.task_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        
        # 底部播放控制框架
        self.control_frame = ttk.Frame(self.root, padding="10")
        self.control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # 状态栏框架
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

    def setup_search_bar(self):
        """设置搜索栏"""
        # 搜索输入框
        search_container = ttk.Frame(self.search_frame)
        search_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        search_icon = ttk.Label(search_container, text="🔍")
        search_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_tasks)
        search_entry = ttk.Entry(search_container, textvariable=self.search_var,
                               font=self.normal_font, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 搜索类型选择
        self.search_type = tk.StringVar(value="name")
        for text, value in [("按名称", "name"), ("按时间", "time"), ("按日期", "date")]:
            ttk.Radiobutton(search_container, text=text, variable=self.search_type,
                           value=value, command=self.filter_tasks).pack(side=tk.LEFT, padx=5)
        
        # 主题选择
        theme_frame = ttk.Frame(self.search_frame)
        theme_frame.pack(side=tk.RIGHT)
        
        ttk.Label(theme_frame, text="主题:", font=self.normal_font).pack(side=tk.LEFT, padx=5)
        themes = ["默认", "暗色", "浅色"]
        self.theme_var = tk.StringVar(value="默认")
        theme_combo = ttk.Combobox(theme_frame, values=themes,
                                 textvariable=self.theme_var, width=8,
                                 state="readonly")
        theme_combo.pack(side=tk.LEFT)
        theme_combo.bind('<<ComboboxSelected>>', self.change_theme)

    def setup_playback_controls(self):
        """设置播放控制区域"""
        # 播放进度条框架
        progress_frame = ttk.LabelFrame(self.control_frame, text="播放进度", padding="5")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.play_progress_var = tk.DoubleVar()
        self.play_progress = ttk.Progressbar(progress_frame,
                                           variable=self.play_progress_var,
                                           maximum=100)
        self.play_progress.pack(fill=tk.X, padx=5, pady=5)
        
        # 时间显示
        time_frame = ttk.Frame(progress_frame)
        time_frame.pack(fill=tk.X, padx=5)
        
        self.current_time = ttk.Label(time_frame, text="00:00")
        self.current_time.pack(side=tk.LEFT)
        
        self.total_time = ttk.Label(time_frame, text="/ 00:00")
        self.total_time.pack(side=tk.RIGHT)
        
        # 控制按钮
        control_buttons_frame = ttk.Frame(self.control_frame)
        control_buttons_frame.pack(fill=tk.X, pady=5)
        
        buttons = [
            ("新增任务", "🆕", self.add_task),
            ("删除任务", "❌", self.delete_task),
            ("复制任务", "📋", self.copy_task),
            ("导入任务", "📥", self.import_tasks),
            ("导出任务", "📤", self.export_tasks),
            ("导出Excel", "📊", self.export_to_excel),
            ("排序任务", "🔄", self.sort_tasks),
            ("播放任务", "▶", self.play_task),
            ("暂停任务", "⏸", self.pause_task),
            ("停止任务", "⏹", self.stop_task),
            ("同步时间", "🕒", self.sync_time),
            ("上移任务", "⬆", self.move_task_up),
            ("下移任务", "⬇", self.move_task_down)
        ]
        
        for text, icon, command in buttons:
            btn = ttk.Button(control_buttons_frame, 
                           text=f"{icon} {text}", 
                           command=command, 
                           style="Custom.TButton")
            btn.pack(side=tk.LEFT, padx=2)

    def setup_status_bar(self):
        """设置状态栏"""
        separator = ttk.Separator(self.status_frame, orient="horizontal")
        separator.pack(fill=tk.X)
        
        status_container = ttk.Frame(self.status_frame, padding="5")
        status_container.pack(fill=tk.X)
        
        # 时间显示
        self.time_label = ttk.Label(status_container, 
                                  font=self.normal_font,
                                  anchor="e")
        self.time_label.pack(side=tk.RIGHT)
        
        # 状态信息
        self.status_label = ttk.Label(status_container,
                                    text="就绪",
                                    font=self.normal_font)
        self.status_label.pack(side=tk.LEFT)

    def _set_icon(self):
        """设置应用程序图标"""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError as e:
                print(f"Warning: Could not load icon: {e}")
                
    def _safe_play_audio(self, file_path, volume=100):
        """安全的音频播放"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError("音频文件不存在")
                
            sound = pygame.mixer.Sound(file_path)
            self.current_playing_duration = sound.get_length()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(volume / 100)
            pygame.mixer.music.play()
            
            # 更新初始时间显示
            total_str = time.strftime('%M:%S', time.gmtime(self.current_playing_duration))
            self.current_time.config(text="00:00")
            self.total_time.config(text=f"/ {total_str}")
            
            return True
            
        except Exception as e:
            messagebox.showerror("播放错误", f"播放音频失败: {str(e)}")
            return False
            
    def _update_task_in_json(self, task_data):
        """安全地更新任务数据到JSON文件"""
        task_file = os.path.join(os.path.dirname(__file__), "task.json")
        try:
            tasks = []
            if os.path.exists(task_file):
                with open(task_file, "r", encoding="utf-8") as f:
                    try:
                        tasks = json.load(f)
                    except json.JSONDecodeError:
                        pass
                        
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)
                
            return True
        except Exception as e:
            messagebox.showerror("保存错误", f"保存任务数据失败: {str(e)}")
            return False

    def setup_styles(self):
        """设置界面样式"""
        # 设置字体
        self.title_font = Font(family="Microsoft YaHei", size=12, weight="bold")
        self.normal_font = Font(family="Microsoft YaHei", size=10)
        
        # 设置主题样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置Treeview样式
        style.configure("Treeview",
                    background="#ffffff",
                    fieldbackground="#ffffff",
                    foreground="black",
                    font=self.normal_font,
                    rowheight=25)
        
        style.configure("Treeview.Heading",
                    background="#4a90e2",
                    foreground="white",
                    font=self.title_font,
                    relief="flat")
        
        style.map("Treeview.Heading",
                background=[('active', '#2c5282')])
        
        # 配置Button样式
        style.configure("Custom.TButton",
                    font=self.normal_font,
                    padding=5)
        
        style.map("Custom.TButton",
                background=[('active', '#4a90e2'), ('pressed', '#2c5282')],
                foreground=[('active', 'white'), ('pressed', 'white')])

        # 配置进度条样式
        style.configure("Horizontal.TProgressbar",
                    background="#4a90e2",
                    troughcolor="#f0f0f0",
                    bordercolor="#e0e0e0",
                    lightcolor="#6ab7ff",
                    darkcolor="#1976d2")

        # 配置其他控件样式
        style.configure("Custom.TLabel",
                    font=self.normal_font)
        
        style.configure("Title.TLabel",
                    font=self.title_font)
        
    def setup_tree(self):
        """设置任务列表"""
        # 创建一个框架来容纳树形视图和滚动条
        tree_frame = ttk.Frame(self.task_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 定义列
        self.columns = ("序号", "任务名称", "开始时间", "结束时间", "音量", "播放日期/星期", "文件路径", "状态")
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings", 
                                selectmode="browse", style="Treeview")
        
        # 设置列标题和列宽
        column_widths = {
            "序号": 60,
            "任务名称": 200,
            "开始时间": 100,
            "结束时间": 100,
            "音量": 80,
            "播放日期/星期": 150,
            "文件路径": 300,
            "状态": 100
        }
        
        # 配置列
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=column_widths[col], 
                           anchor="center" if col not in ["文件路径", "任务名称"] else "w")
        
        # 配置标签样式
        self.tree.tag_configure('playing', foreground='#4CAF50', background='#E8F5E9')
        self.tree.tag_configure('paused', foreground='#FFA000', background='#FFF3E0')
        self.tree.tag_configure('waiting', foreground='#757575')
        self.tree.tag_configure('error', foreground='#F44336', background='#FFEBEE')
        self.tree.tag_configure('selected', background='#E3F2FD')
        
        # 添加滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 使用网格布局管理器布置组件
        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        # 配置网格权重
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定事件
        self.tree.bind("<Double-1>", self.edit_task)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.delete_task())
        self.tree.bind("<Control-c>", lambda e: self.copy_task())
        self.tree.bind("<Control-v>", lambda e: self.paste_task())
        self.tree.bind("<space>", lambda e: self.toggle_playback())
        
    def sort_by_column(self, column):
        """按列排序"""
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children('')]
        
        # 确定排序方式
        if hasattr(self, '_sort_column') and self._sort_column == column:
            items.sort(reverse=not self._sort_reverse)
            self._sort_reverse = not self._sort_reverse
        else:
            items.sort()
            self._sort_reverse = False
        
        self._sort_column = column
        
        # 重新排序项目
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)
            # 更新序号
            if column != "序号":
                self.tree.set(item, "序号", str(index + 1))
        
        # 更新标题指示器
        for col in self.columns:
            if col == column:
                self.tree.heading(col, text=f"{col} {'↓' if self._sort_reverse else '↑'}")
            else:
                self.tree.heading(col, text=col)

    def on_select(self, event):
        """处理选择事件"""
        selected = self.tree.selection()
        if selected:
            # 移除之前的选择样式
            for item in self.tree.get_children():
                tags = list(self.tree.item(item)["tags"])
                if "selected" in tags:
                    tags.remove("selected")
                self.tree.item(item, tags=tags)
            
            # 添加新的选择样式
            for item in selected:
                tags = list(self.tree.item(item)["tags"])
                if "selected" not in tags:
                    tags.append("selected")
                self.tree.item(item, tags=tags)
                
            # 更新状态栏信息
            item = selected[0]
            values = self.tree.item(item)["values"]
            self.status_label.config(text=f"已选择任务：{values[1]}")

    def toggle_playback(self):
        """切换播放状态"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
        if item == self.current_playing_item:
            if self.paused:
                self.play_task(item)
            else:
                self.pause_task()
        else:
            self.play_task(item)

    def update_task_status(self, item, status_text, status_tag):
        """更新任务状态"""
        if item:
            values = list(self.tree.item(item)["values"])
            tags = list(self.tree.item(item)["tags"])
            
            # 更新状态文本
            if len(values) < len(self.columns):
                values.append("")
            values[-1] = status_text
            
            # 更新状态标签
            tags = [tag for tag in tags if tag not in ['playing', 'paused', 'waiting', 'error']]
            tags.append(status_tag)
            
            self.tree.item(item, values=values, tags=tags)
            
            # 更新状态栏
            self.status_label.config(text=f"当前任务：{values[1]} - {status_text}")

    def edit_task(self, event):
        try:
            selected_item = self.tree.selection()[0]
            task_data = self.tree.item(selected_item)['values']
            if not hasattr(self, 'add_task_window') or self.add_task_window is None:
                self.add_task_window = AddTaskWindow(self, task_data=task_data, selected_item=selected_item)
            else:
                self.add_task_window.window.focus()
        except IndexError:
            messagebox.showinfo("提示", "请先选择要编辑的任务")

    def filter_tasks(self, *args):
        search_text = self.search_var.get().lower()
        search_type = self.search_type.get()
        
        # 显示所有项目
        for item in self.tree.get_children():
            self.tree.item(item, tags=self.tree.item(item)["tags"])  # 保持原有标签
            
        if not search_text:
            return
            
        # 隐藏不匹配的项目
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            match = False
            
            if search_type == "name":
                match = search_text in str(values[1]).lower()  # 任务名称
            elif search_type == "time":
                match = search_text in str(values[2]).lower()  # 开始时间
            elif search_type == "date":
                match = search_text in str(values[5]).lower()  # 播放日期/星期
                
            if not match:
                self.tree.item(item, tags=("hidden",))

    def change_theme(self, event=None):
        theme = self.theme_var.get()
        style = ttk.Style()
        
        if theme == "暗色":
            style.configure(".", 
                          background="#2d2d2d",
                          foreground="white",
                          fieldbackground="#3d3d3d")
            style.configure("Treeview",
                          background="#2d2d2d",
                          foreground="white",
                          fieldbackground="#3d3d3d")
            style.configure("Treeview.Heading",
                          background="#4a4a4a",
                          foreground="white")
            self.root.configure(bg="#2d2d2d")
            
        elif theme == "浅色":
            style.configure(".",
                          background="#ffffff",
                          foreground="black",
                          fieldbackground="#f0f0f0")
            style.configure("Treeview",
                          background="#ffffff",
                          foreground="black",
                          fieldbackground="#f0f0f0")
            style.configure("Treeview.Heading",
                          background="#e1e1e1",
                          foreground="black")
            self.root.configure(bg="#ffffff")
            
        else:  # 默认主题
            style.configure(".",
                          background="#f5f6f7",
                          foreground="black",
                          fieldbackground="#ffffff")
            style.configure("Treeview",
                          background="#f0f0f0",
                          foreground="black",
                          fieldbackground="#f0f0f0")
            style.configure("Treeview.Heading",
                          background="#4a90e2",
                          foreground="white")
            self.root.configure(bg="#f5f6f7")
            
        # 重新应用交替行颜色
        for i, item in enumerate(self.tree.get_children()):
            if "hidden" not in self.tree.item(item)["tags"]:
                self.tree.item(item, tags=('oddrow' if i % 2 else 'evenrow',))
        
    def load_tasks(self):
        """加载任务数据"""
        task_file = os.path.join(os.path.dirname(__file__), "task.json")
        try:
            if not os.path.exists(task_file):
                self._create_empty_task_file(task_file)
                self.status_label.config(text="已创建新的任务文件")
                return
                
            with open(task_file, "r", encoding="utf-8") as f:
                try:
                    tasks = json.load(f)
                except json.JSONDecodeError:
                    self._create_empty_task_file(task_file)
                    self.status_label.config(text="任务文件已重置")
                    return
                    
                for task in tasks:
                    self._add_task_to_tree(task)
                    
            total_tasks = len(self.tree.get_children())
            self.status_label.config(text=f"已加载 {total_tasks} 个任务")
                    
        except Exception as e:
            messagebox.showerror("错误", f"加载任务失败: {str(e)}")
            self.status_label.config(text="加载任务失败")

    def _add_task_to_tree(self, task):
        """将任务添加到树形视图"""
        try:
            # 处理新旧格式的任务数据
            if isinstance(task, dict):
                values = [
                    task.get('id', ''),
                    task.get('name', ''),
                    task.get('startTime', ''),
                    task.get('endTime', ''),
                    task.get('volume', ''),
                    task.get('schedule', ''),
                    task.get('audioPath', ''),
                    task.get('status', '等待播放')
                ]
            else:
                values = list(task)
                if len(values) < 8:
                    values.append('等待播放')
                    
            # 验证文件路径
            if not os.path.exists(values[6]):
                values[-1] = "文件丢失"
                self.tree.insert("", "end", values=values, tags=('error',))
            else:
                self.tree.insert("", "end", values=values, tags=('waiting',))
                
        except Exception as e:
            print(f"Warning: Failed to add task: {e}")

    def add_task(self):
         if not hasattr(self, 'add_task_window') or self.add_task_window is None:
            self.add_task_window = AddTaskWindow(self)
         else:
            self.add_task_window.window.focus()

    def delete_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的任务")
            return
            
        if len(selected) > 1:
            confirm = messagebox.askyesno("确认", 
                f"确定要删除选中的 {len(selected)} 个任务吗？")
        else:
            confirm = messagebox.askyesno("确认", "确定要删除选中的任务吗？")
            
        if confirm:
            for item in selected:
                self.tree.delete(item)
            self.save_all_tasks()
            messagebox.showinfo("成功", f"已删除 {len(selected)} 个任务")

    def play_task(self, item=None, file_path=None, volume=None):
        """增强的任务播放功能"""
        try:
            # 获取播放信息
            if not item and not file_path:
                selected = self.tree.selection()
                if not selected:
                    messagebox.showinfo("提示", "请先选择要播放的任务")
                    return
                item = selected[0]
                
            if item:
                values = self.tree.item(item)['values']
                file_path = values[6]
                volume = int(values[4])
                
            # 停止当前播放
            if self.current_playing_sound:
                self.stop_task()
                
            # 播放新任务
            if self._safe_play_audio(file_path, volume):
                self.current_playing_sound = file_path
                self.current_playing_item = item
                self.paused = False
                
                # 更新状态
                self.update_task_status(item, "正在播放", 'playing')
                
                # 重置并显示进度条
                self.play_progress_var.set(0)
                
                # 启动进度更新线程
                self.stop_thread = False
                self.playing_thread = threading.Thread(target=self.update_play_progress)
                self.playing_thread.daemon = True
                self.playing_thread.start()
                
        except Exception as e:
            messagebox.showerror("错误", f"播放失败: {str(e)}")
            if item:
                self.update_task_status(item, "播放失败", 'error')

    def pause_task(self):
        if self.current_playing_sound:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                self.update_task_status(self.current_playing_item, "正在播放", 'playing')
            else:
                pygame.mixer.music.pause()
                self.paused = True
                self.update_task_status(self.current_playing_item, "已暂停", 'paused')

    def stop_task(self):
        if self.current_playing_sound:
            self.stop_thread = True
            if self.playing_thread:
                self.playing_thread.join()
            pygame.mixer.music.stop()
            self.update_task_status(self.current_playing_item, "等待播放", 'waiting')
            self.current_playing_sound = None
            self.current_playing_item = None
            self.paused = False
            self.play_progress_frame.grid_remove()

    def sync_time(self):
        try:
            result = os.system("w32tm /resync")
            if result == 0:
                messagebox.showinfo("提示", "时间同步成功")
            elif result == 1114:
                messagebox.showerror("错误", "时间同步失败：没有管理员权限")
            else:
                messagebox.showerror("错误", f"时间同步失败，错误代码：{result}")
        except Exception as e:
            messagebox.showerror("错误", f"时间同步失败: {str(e)}")

    def move_task_up(self):
        self._move_task(-1)

    def move_task_down(self):
        self._move_task(1)

    def _move_task(self, direction):
        try:
            selected = self.tree.selection()[0]
            idx = self.tree.index(selected)
            if 0 <= idx + direction < len(self.tree.get_children()):
                self.tree.move(selected, "", idx + direction)
                self.update_task_order()
        except IndexError:
            messagebox.showinfo("提示", "请选择要移动的任务")

    def update_task_order(self):
        with open("audio_player/task.json", "r+", encoding="utf-8") as f:
            data = []
            for idx, item in enumerate(self.tree.get_children(), 1):
                values = self.tree.item(item)['values']
                task = list(values)
                task[0] = idx
                data.append(task)
                self.tree.set(item, 0, idx)
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=4)

    def sort_tasks(self):
        tasks = [(self.tree.set(item, "开始时间"), 
                 self.tree.set(item, "播放日期"), 
                 item) for item in self.tree.get_children()]
        tasks.sort(key=lambda x: (x[1] if x[1] else "9999-99-99", x[0]))
        
        for index, (_, _, item) in enumerate(tasks):
            self.tree.move(item, '', index)
        
        self.update_task_order()

    def import_tasks(self):
        """导入任务"""
        file_path = filedialog.askopenfilename(
            title="导入任务",
            filetypes=[("JSON文件", "*.json"), ("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            self.status_label.config(text="正在导入...")
            
            if (file_path.lower().endswith('.xlsx')):
                # 从Excel导入
                df = pd.read_excel(file_path)
                tasks = df.to_dict('records')
            else:
                # 从JSON导入
                with open(file_path, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
            
            # 清空现有任务
            if messagebox.askyesno("确认", "是否清空现有任务？"):
                for item in self.tree.get_children():
                    self.tree.delete(item)
            
            # 添加新任务
            total_tasks = len(tasks)
            for i, task in enumerate(tasks, 1):
                self._add_task_to_tree(task)
                # 更新进度
                self.play_progress_var.set(i / total_tasks * 100)
                self.root.update()
            
            # 保存更改
            self.save_all_tasks()
            
            self.play_progress_var.set(0)
            self.status_label.config(text=f"已导入 {total_tasks} 个任务")
            messagebox.showinfo("成功", f"成功导入 {total_tasks} 个任务")
            
        except Exception as e:
            self.play_progress_var.set(0)
            self.status_label.config(text="导入失败")
            messagebox.showerror("错误", f"导入失败: {str(e)}")
            
    def export_tasks(self):
        file_path = filedialog.asksaveasfilename(
            title="导出任务",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            tasks = []
            total_items = len(self.tree.get_children())
            
            for i, item in enumerate(self.tree.get_children()):
                
                values = self.tree.item(item)["values"]
                tasks.append(values[:7])  # 不包含状态列
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("成功", f"成功导出 {len(tasks)} 个任务")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            
    def save_all_tasks(self):
        """保存所有任务"""
        task_file = os.path.join(os.path.dirname(__file__), "task.json")
        try:
            tasks = []
            for item in self.tree.get_children():
                values = list(self.tree.item(item)["values"])
                task_data = {
                    "id": values[0],
                    "name": values[1],
                    "startTime": values[2],
                    "endTime": values[3],
                    "volume": values[4],
                    "schedule": values[5],
                    "audioPath": values[6],
                    "status": values[7] if len(values) > 7 else "waiting"
                }
                tasks.append(task_data)
                
            # 创建备份
            if os.path.exists(task_file):
                backup_file = f"{task_file}.bak"
                try:
                    import shutil
                    shutil.copy2(task_file, backup_file)
                except Exception as e:
                    print(f"Warning: Failed to create backup: {e}")
                
            # 保存新数据
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)
                
            self.status_label.config(text="任务已保存")
            return True
            
        except Exception as e:
            messagebox.showerror("保存错误", f"保存任务失败: {str(e)}")
            self.status_label.config(text="保存任务失败")
            return False

    def check_tasks(self):
        """改进的任务自动检查机制"""
        try:
            current_time = datetime.datetime.now()
            current_weekday = ["一", "二", "三", "四", "五", "六", "日"][current_time.weekday()]
            current_date = current_time.strftime("%Y-%m-%d")
            
            # 更新时间显示
            time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=time_str)
            
            # 检查所有任务
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if len(values) < 8 or values[-1] == "正在播放":
                    continue
                    
                # 检查播放条件
                if self._should_play_task(values, current_time, current_weekday, current_date):
                    # 如果有任务正在播放，先停止
                    if self.current_playing_sound:
                        self.stop_task()
                    self.play_task(item)
                    break  # 只播放一个任务
                    
        except Exception as e:
            print(f"Warning: Task check error: {e}")
        finally:
            # 继续检查
            self.root.after(1000, self.check_tasks)
            
    def _should_play_task(self, values, current_time, current_weekday, current_date):
        """检查任务是否应该播放"""
        try:
            task_time = values[2]  # 开始时间
            task_date = values[5]  # 播放日期/星期
            
            # 解析任务时间
            task_time_obj = datetime.datetime.strptime(task_time, "%H:%M:%S").time()
            current_time_obj = current_time.time()
            
            # 检查时间匹配
            time_match = (
                task_time_obj.hour == current_time_obj.hour and
                task_time_obj.minute == current_time_obj.minute and
                abs(task_time_obj.second - current_time_obj.second) <= 1
            )
            
            if not time_match:
                return False
                
            # 检查日期或星期匹配
            if "," in task_date:  # 星期模式
                weekdays = [day.strip() for day in task_date.split(",")]
                return current_weekday in weekdays
            else:  # 日期模式
                return task_date == current_date
                
        except Exception as e:
            print(f"Warning: Task validation error: {e}")
            return False

    def run(self):
        self.root.mainloop()

    def update_play_progress(self):
        """更新播放进度"""
        try:
            start_time = time.time()
            while not self.stop_thread and pygame.mixer.music.get_busy():
                if not self.paused:
                    elapsed = time.time() - start_time
                    progress = min((elapsed / self.current_playing_duration) * 100, 100)
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_progress_ui, elapsed, progress)
                    
                time.sleep(0.1)
                
            if not self.stop_thread:  # 正常播放结束
                self.root.after(0, self._on_playback_complete)
                
        except Exception as e:
            print(f"Warning: Progress update error: {e}")
            self.root.after(0, self.stop_task)
            
    def _update_progress_ui(self, elapsed, progress):
        """更新进度条UI"""
        try:
            self.play_progress_var.set(progress)
            
            # 更新时间显示
            elapsed_str = time.strftime('%M:%S', time.gmtime(elapsed))
            total_str = time.strftime('%M:%S', time.gmtime(self.current_playing_duration))
            self.current_time.config(text=elapsed_str)
            self.total_time.config(text=f"/ {total_str}")
            
            # 更新任务状态
            if self.current_playing_item:
                values = self.tree.item(self.current_playing_item)["values"]
                self.status_label.config(text=f"正在播放：{values[1]} ({elapsed_str}/{total_str})")
                
        except Exception as e:
            print(f"Warning: UI update error: {e}")
            
    def _on_playback_complete(self):
        """播放完成处理"""
        if self.current_playing_item:
            self.update_task_status(self.current_playing_item, "等待播放", 'waiting')
        self.stop_task()
        self.status_label.config(text="就绪")

    def export_to_excel(self):
        """导出到Excel"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="导出到Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
                
            # 准备数据
            data = []
            columns = list(self.columns)  # 使用已定义的列名
            
            self.status_label.config(text="正在导出数据...")
            total_items = len(self.tree.get_children())
            
            for i, item in enumerate(self.tree.get_children()):
                # 更新进度
                progress = (i + 1) / total_items * 100
                self.play_progress_var.set(progress)
                self.root.update()
                
                values = list(self.tree.item(item)["values"])
                # 确保所有行都有相同的列数
                while len(values) < len(columns):
                    values.append("")
                data.append(values)
            
            df = pd.DataFrame(data, columns=columns)
            
            # 使用 ExcelWriter 添加格式
            writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name="任务列表")
            
            # 获取workbook和worksheet对象
            workbook = writer.book
            worksheet = writer.sheets['任务列表']
            
            # 定义格式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4a90e2',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            content_format = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            # 应用格式
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                # 设置列格式
                if value in ["文件路径", "任务名称"]:
                    worksheet.set_column(col_num, col_num, 30, content_format)
                else:
                    worksheet.set_column(col_num, col_num, 15, content_format)
            
            # 冻结首行
            worksheet.freeze_panes(1, 0)
            
            # 添加自动筛选
            worksheet.autofilter(0, 0, len(data), len(columns)-1)
            
            writer.close()
            
            self.play_progress_var.set(0)
            self.status_label.config(text=f"已成功导出 {len(data)} 个任务到 Excel")
            messagebox.showinfo("成功", "成功导出到Excel文件")
            
        except Exception as e:
            self.play_progress_var.set(0)
            self.status_label.config(text="导出失败")
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def copy_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要复制的任务")
            return
            
        for item in selected:
            values = list(self.tree.item(item)["values"])
            # 修改任务名称，添加"副本"标记
            values[1] = f"{values[1]} - 副本"
            # 重置状态
            if len(values) > 7:
                values = values[:7]
            self.save_task_data(values[1:])  # 不包含序号

    def update_time(self):
        """更新状态栏时间显示"""
        current_time = datetime.datetime.now()
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=time_str)
        self.root.after(1000, self.update_time)  # 每秒更新一次


class AddTaskWindow:
    def __init__(self, player, task_data=None, selected_item=None):
        self.player = player
        self.selected_item = selected_item
        self.window = tk.Toplevel(player.root)
        self.window.title("修改任务" if task_data else "新增任务")
        self.window.geometry("500x600")
        self.window.configure(bg="#f5f6f7")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 使窗口模态
        self.window.transient(player.root)
        self.window.grab_set()
        
        # 设置窗口在父窗口中居中
        self.center_window()
        
        self.setup_ui(task_data)

    def center_window(self):
        parent = self.window.master
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def on_closing(self):
        if self.preview_playing:
            pygame.mixer.music.stop()
        self.player.add_task_window = None
        self.window.destroy()

    def setup_ui(self, task_data):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        # Task name
        self.setup_task_name(main_frame, task_data)
        
        # Date/Weekday selection
        self.setup_date_selection(main_frame, task_data)
        
        # Time setting
        self.setup_time_setting(main_frame, task_data)
        
        # File path
        self.setup_file_path(main_frame, task_data)
        
        # Volume
        self.setup_volume(main_frame, task_data)
        
        # Buttons
        self.setup_buttons(main_frame)

    def setup_task_name(self, parent, task_data):
        frame = ttk.LabelFrame(parent, text="任务名称", padding="5")
        frame.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        self.task_name_entry = ttk.Entry(frame, font=self.player.normal_font)
        self.task_name_entry.pack(fill=tk.X, padx=5, pady=5)
        if task_data:
            self.task_name_entry.insert(0, task_data[1])

    def setup_date_selection(self, parent, task_data=None):
        date_frame = ttk.LabelFrame(parent, text="日期设置", padding="5")
        date_frame.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))

        # Radio buttons for date/weekday selection
        radio_frame = ttk.Frame(date_frame)
        radio_frame.pack(fill=tk.X, padx=5, pady=5)

        self.date_weekday_var = tk.IntVar()
        ttk.Radiobutton(radio_frame, text="单次日期", variable=self.date_weekday_var,
                       value=0, command=self.show_date).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(radio_frame, text="每周重复", variable=self.date_weekday_var,
                       value=1, command=self.show_weekday).pack(side=tk.LEFT, padx=10)

        # Calendar with custom style
        self.cal = Calendar(date_frame, selectmode="day", date_pattern="yyyy-mm-dd",
                          background="#4a90e2", foreground="white",
                          headersbackground="#2c5282", headersforeground="white",
                          selectbackground="#2c5282", selectforeground="white",
                          normalbackground="#ffffff", normalforeground="black",
                          weekendbackground="#f0f0f0", weekendforeground="black")
        self.cal.pack(padx=5, pady=5)

        # Weekday selection
        self.setup_weekday_selection(date_frame, task_data)

        # Initialize based on task_data
        if task_data:
            date_str = task_data[5]
            if "," in date_str:
                self.date_weekday_var.set(1)
                weekdays = [day.strip() for day in date_str.split(",")]
                for i, day in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
                    self.weekday_vars[i].set(day in weekdays)
                self.show_weekday()
            else:
                self.date_weekday_var.set(0)
                try:
                    self.cal.selection_set(date_str)
                except:
                    pass
                self.show_date()
        else:
            self.show_date()

    def setup_weekday_selection(self, parent, task_data):
        self.weekdays_frame = ttk.Frame(parent)
        self.weekdays_frame.pack(fill=tk.X, padx=5, pady=5)

        weekday_label = ttk.Label(self.weekdays_frame, text="选择重复的星期:",
                                 font=self.player.normal_font)
        weekday_label.pack(pady=5)

        checkbutton_frame = ttk.Frame(self.weekdays_frame)
        checkbutton_frame.pack(fill=tk.X, padx=5)

        self.weekday_vars = []
        for day in ["一", "二", "三", "四", "五", "六", "日"]:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(checkbutton_frame, text=day, variable=var)
            cb.pack(side=tk.LEFT, padx=5)
            self.weekday_vars.append(var)

        quick_select_frame = ttk.Frame(self.weekdays_frame)
        quick_select_frame.pack(fill=tk.X, pady=5)

        ttk.Button(quick_select_frame, text="工作日", style="Custom.TButton",
                  command=self.select_workdays).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_select_frame, text="全选", style="Custom.TButton",
                  command=lambda: [var.set(True) for var in self.weekday_vars]).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_select_frame, text="清除", style="Custom.TButton",
                  command=lambda: [var.set(False) for var in self.weekday_vars]).pack(side=tk.LEFT, padx=5)

        self.weekdays_frame.pack_forget()

    def setup_time_setting(self, parent, task_data=None):
        time_frame = ttk.LabelFrame(parent, text="时间设置", padding="5")
        time_frame.grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))

        spinner_frame = ttk.Frame(time_frame)
        spinner_frame.pack(fill=tk.X, padx=5, pady=5)

        # 时间调节框架
        time_controls = []
        for unit, max_val in [("时", 23), ("分", 59), ("秒", 59)]:
            control_frame = ttk.Frame(spinner_frame)
            control_frame.pack(side=tk.LEFT, padx=5)
            
            # 上调按钮
            up_btn = ttk.Button(control_frame, text="▲", width=3,
                              style="Toolbutton")
            up_btn.pack(pady=(0, 2))
            
            # 时间输入框
            var = tk.StringVar(value="00")
            entry = ttk.Entry(control_frame, textvariable=var, width=3,
                            justify="center", font=self.player.normal_font)
            entry.pack()
            
            # 下调按钮
            down_btn = ttk.Button(control_frame, text="▼", width=3,
                                style="Toolbutton")
            down_btn.pack(pady=(2, 0))
            
            # 时间单位标签
            ttk.Label(control_frame, text=unit,
                     font=self.player.normal_font).pack(pady=2)
            
            time_controls.append((var, up_btn, down_btn, max_val))
            
            # 添加分隔符，但不在最后一个单位后添加
            if unit != "秒":
                ttk.Label(spinner_frame, text=":",
                         font=self.player.normal_font).pack(side=tk.LEFT)

        # 存储变量引用
        self.hour_var, self.minute_var, self.second_var = [x[0] for x in time_controls]

        # 绑定事件
        for var, up_btn, down_btn, max_val in time_controls:
            self.bind_time_controls(var, up_btn, down_btn, max_val)

        if task_data:
            start_time = task_data[2]
            try:
                times = start_time.split(":")
                self.hour_var.set(times[0].zfill(2))
                self.minute_var.set(times[1].zfill(2))
                self.second_var.set(times[2].zfill(2))
            except:
                pass

    def bind_time_controls(self, var, up_btn, down_btn, max_val):
        def validate_time(value):
            try:
                if value == "": return True
                val = int(value)
                return 0 <= val <= max_val
            except ValueError:
                return False

        def increment(event=None):
            try:
                val = int(var.get())
                val = (val + 1) % (max_val + 1)
                var.set(f"{val:02d}")
            except ValueError:
                var.set("00")

        def decrement(event=None):
            try:
                val = int(var.get())
                val = (val - 1) % (max_val + 1)
                var.set(f"{val:02d}")
            except ValueError:
                var.set("00")

        def on_key(event):
            if event.keysym == "Up":
                increment()
                return "break"
            elif event.keysym == "Down":
                decrement()
                return "break"

        def on_scroll(event):
            if event.delta > 0:
                increment()
            else:
                decrement()
            return "break"

        def on_focus_out(event):
            try:
                val = int(var.get())
                var.set(f"{val:02d}")
            except ValueError:
                var.set("00")

        # 绑定按钮事件
        up_btn.configure(command=increment)
        down_btn.configure(command=decrement)

        # 获取Entry小部件
        entry = up_btn.master.children[list(up_btn.master.children.keys())[1]]
        
        # 绑定Entry事件
        entry.bind("<Up>", on_key)
        entry.bind("<Down>", on_key)
        entry.bind("<MouseWheel>", on_scroll)
        entry.bind("<FocusOut>", on_focus_out)

        # 验证函数
        vcmd = (entry.register(validate_time), '%P')
        entry.configure(validate="key", validatecommand=vcmd)

    def setup_file_path(self, parent, task_data=None):
        file_frame = ttk.LabelFrame(parent, text="音频文件", padding="5")
        file_frame.grid(row=3, column=0, pady=5, sticky=(tk.W, tk.E))

        file_entry_frame = ttk.Frame(file_frame)
        file_entry_frame.pack(fill=tk.X, padx=5, pady=5)

        self.file_path_entry = ttk.Entry(file_entry_frame, font=self.player.normal_font)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(file_entry_frame, text="浏览", style="Custom.TButton",
                              command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT)

        if task_data:
            self.file_path_entry.insert(0, task_data[6])

    def setup_volume(self, parent, task_data=None):
        volume_frame = ttk.LabelFrame(parent, text="音量控制", padding="5")
        volume_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

        volume_control_frame = ttk.Frame(volume_frame)
        volume_control_frame.pack(fill=tk.X, padx=5, pady=5)

        # 音量滑块
        self.volume_scale = ttk.Scale(volume_control_frame, from_=0, to=100, orient="horizontal")
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 音量数值显示
        self.volume_label = ttk.Label(volume_control_frame, text="0%", width=5)
        self.volume_label.pack(side=tk.LEFT)

        # 预览控制按钮
        preview_frame = ttk.Frame(volume_frame)
        preview_frame.pack(fill=tk.X, padx=5, pady=5)

        self.preview_button = ttk.Button(preview_frame, 
                                       text="▶ 预览", 
                                       style="Custom.TButton",
                                       command=self.toggle_preview)
        self.preview_button.pack(side=tk.LEFT, padx=5)

        self.preview_playing = False
        self.preview_sound = None

        def update_volume(event=None):
            volume = int(self.volume_scale.get())
            self.volume_label.config(text=f"{volume}%")
            if self.preview_playing and self.preview_sound:
                pygame.mixer.music.set_volume(volume / 100)

        self.volume_scale.bind("<Motion>", update_volume)
        self.volume_scale.bind("<ButtonRelease-1>", update_volume)

        if task_data:
            self.volume_scale.set(task_data[4])
            update_volume()
        else:
            self.volume_scale.set(50)
            update_volume()

    def toggle_preview(self):
        if not self.preview_playing:
            file_path = self.file_path_entry.get()
            if not file_path or not os.path.exists(file_path):
                messagebox.showerror("错误", "请先选择有效的音频文件")
                return

            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.set_volume(int(self.volume_scale.get()) / 100)
                pygame.mixer.music.play()
                self.preview_playing = True
                self.preview_button.configure(text="⏹ 停止")
            except Exception as e:
                messagebox.showerror("错误", f"预览失败: {str(e)}")
        else:
            pygame.mixer.music.stop()
            self.preview_playing = False
            self.preview_button.configure(text="▶ 预览")

    def setup_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=5, column=0, pady=15, sticky=(tk.W, tk.E))

        save_btn = ttk.Button(button_frame, text="✔ 保存", style="Custom.TButton",
                            command=self.save_task)
        save_btn.pack(side=tk.RIGHT, padx=5)

        cancel_btn = ttk.Button(button_frame, text="✖ 取消", style="Custom.TButton",
                             command=self.on_closing)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

    def show_date(self):
        self.cal.pack()
        self.weekdays_frame.pack_forget()

    def show_weekday(self):
        self.cal.pack_forget()
        self.weekdays_frame.pack()

    def select_workdays(self):
        for i, var in enumerate(self.weekday_vars):
            var.set(i < 5)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)

    def validate_inputs(self):
        errors = []
        
        # 验证任务名称
        if not self.task_name_entry.get().strip():
            errors.append("任务名称不能为空")

        # 验证文件路径
        file_path = self.file_path_entry.get()
        if not file_path:
            errors.append("请选择音频文件")
        elif not os.path.exists(file_path):
            errors.append("选择的音频文件不存在")
        elif not file_path.lower().endswith(('.mp3', '.wav', '.ogg')):
            errors.append("请选择有效的音频文件(mp3/wav/ogg)")

        # 验证时间
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            second = int(self.second_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                raise ValueError
        except ValueError:
            errors.append("请输入有效的时间")

        # 验证日期/星期选择
        if self.date_weekday_var.get() == 1:  # 星期模式
            if not any(var.get() for var in self.weekday_vars):
                errors.append("请至少选择一个星期")

        if errors:
            raise ValueError("\n".join(errors))

    def save_task(self):
        try:
            self.validate_inputs()
            task_data = self.prepare_task_data()
            self.save_task_data(task_data, self.selected_item)
            messagebox.showinfo("成功", "任务保存成功！")
            self.on_closing()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
        except Exception as e:
            messagebox.showerror("保存失败", f"保存任务时发生错误：\n{str(e)}")

    def save_task_data(self, task_data, selected_item=None):
        task_file = os.path.join(os.path.dirname(__file__), "task.json")
        
        try:
            with open(task_file, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []

                if selected_item:  # 更新现有任务
                    index = self.player.tree.index(selected_item)
                    current_values = list(self.player.tree.item(selected_item)['values'])
                    
                    # 保持原有序号
                    updated_task = [
                        current_values[0],  # 序号
                        task_data[0],      # 任务名称
                        task_data[1],      # 开始时间
                        task_data[2],      # 结束时间
                        task_data[3],      # 音量
                        task_data[4],      # 播放日期/星期
                        task_data[5]       # 文件路径
                    ]
                    
                    # 更新显示
                    self.player.tree.item(selected_item, values=updated_task + ["等待播放"])
                    
                    # 更新数据
                    data[index] = updated_task
                else:  # 添加新任务
                    new_id = len(data) + 1
                    new_task = [
                        new_id,        # 序号
                        task_data[0],  # 任务名称
                        task_data[1],  # 开始时间
                        task_data[2],  # 结束时间
                        task_data[3],  # 音量
                        task_data[4],  # 播放日期/星期
                        task_data[5]   # 文件路径
                    ]
                    
                    # 更新显示
                    self.player.tree.insert("", "end", values=new_task + ["等待播放"])
                    
                    # 更新数据
                    data.append(new_task)
                
                # 保存到文件
                f.seek(0)
                f.truncate()
                json.dump(data, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            raise Exception(f"保存任务数据失败: {str(e)}")

    def prepare_task_data(self):
        # 获取并验证音频文件时长
        file_path = self.file_path_entry.get()
        try:
            sound = pygame.mixer.Sound(file_path)
            duration = sound.get_length()
            start_time = f"{int(self.hour_var.get()):02d}:{int(self.minute_var.get()):02d}:{int(self.second_var.get()):02d}"
            end_time = (datetime.datetime.strptime(start_time, "%H:%M:%S") +
                       datetime.timedelta(seconds=duration)).strftime("%H:%M:%S")
        except:
            # 如果无法获取音频时长，使用默认结束时间（开始时间加5分钟）
            start_time = f"{int(self.hour_var.get()):02d}:{int(self.minute_var.get()):02d}:{int(self.second_var.get()):02d}"
            end_time = (datetime.datetime.strptime(start_time, "%H:%M:%S") +
                       datetime.timedelta(minutes=5)).strftime("%H:%M:%S")

        # 确定播放日期或星期
        if self.date_weekday_var.get() == 0:  # 日期模式
            play_date = self.cal.get_date()
            date_str = play_date
        else:  # 星期模式
            weekdays = []
            for i, var in enumerate(self.weekday_vars):
                if var.get():
                    weekdays.append(["一", "二", "三", "四", "五", "六", "日"][i])
            date_str = ", ".join(weekdays)

        return [
            self.task_name_entry.get().strip(),  # 任务名称
            start_time,                          # 开始时间
            end_time,                            # 结束时间
            int(self.volume_scale.get()),        # 音量
            date_str,                            # 播放日期/星期
            file_path                            # 文件路径
        ]

if __name__ == "__main__":
    player = AudioPlayer()
    player.run()
