import os
import json
import pygame
from tkinter import messagebox
from constants import TASK_FILE_PATH

def safe_play_audio(file_path, volume=100):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError("音频文件不存在")

        sound = pygame.mixer.Sound(file_path)
        duration = sound.get_length()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume / 100)
        pygame.mixer.music.play()

        return True, duration

    except Exception as e:
        messagebox.showerror("播放错误", f"播放音频失败: {str(e)}")
        return False, 0

def update_task_in_json(task_data):
    try:
        tasks = []
        if os.path.exists(TASK_FILE_PATH):
            with open(TASK_FILE_PATH, "r", encoding="utf-8") as f:
                try:
                    loaded_tasks = json.load(f)
                    tasks = loaded_tasks if isinstance(loaded_tasks, list) else []
                except json.JSONDecodeError:
                    pass
        
        # 移除 task_data 中的 "status" 字段
        if "status" in task_data:
            del task_data["status"]

        # 更新 tasks 列表
        updated = False
        for i, task in enumerate(tasks):
            if task["id"] == task_data["id"]:
                tasks[i] = task_data
                updated = True
                break
        if not updated:
            tasks.append(task_data)

        with open(TASK_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
        return True
    except (IOError, json.JSONDecodeError) as e:
        messagebox.showerror("保存错误", f"保存任务数据失败: {str(e)}")
        return False

def load_tasks():
    if not os.path.exists(TASK_FILE_PATH):
        return []
    
    try:
        with open(TASK_FILE_PATH, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            for task in tasks:
                if "status" in task:
                    del task["status"]
            return tasks
    except json.JSONDecodeError:
        return []
    except (IOError, json.JSONDecodeError) as e:
        messagebox.showerror("错误", f"加载任务失败: {str(e)}")
        return []

def save_all_tasks(tasks):
    try:
        tasks_without_status = []
        for task in tasks:
            task_copy = task.copy()
            if "status" in task_copy:
                del task_copy["status"]
            tasks_without_status.append(task_copy)
        with open(TASK_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(tasks_without_status, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        messagebox.showerror("保存错误", f"保存任务失败: {str(e)}")
        return False