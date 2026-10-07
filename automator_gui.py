import os
import json
import time
import shutil
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pynput
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE_DIR = 'projects'
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Test Case Recorder")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        self.root.iconbitmap(icon_path)
        self.center_window(self.root, 650, 450)

        # State Recorder
        self.current_project = None
        self.recording_events = []
        self.is_recording = False
        self.is_paused = False
        self.start_time = 0
        self.pause_offset = 0
        self.pause_start_time = 0
        self.recorder_window = None
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # State Playback
        self.playback_window = None
        self.stop_playback_flag = False

        self.show_project_dashboard()

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f"{width}x{height}+{x}+{y}")

    #UI: PROJECT DASHBOARD
    def show_project_dashboard(self):
        self.clear_window()
        self.current_project = None
        
        ctk.CTkLabel(self.root, text="Project Dashboard", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="Create Project", command=self.create_project, width=150).pack(side=tk.LEFT, padx=10)

        self.project_listbox = tk.Listbox(self.root, width=70, height=12, bg="#2b2b2b", fg="white", 
                                          selectbackground="#1f538d", borderwidth=0, highlightthickness=1, highlightbackground="#565b5e")
        self.project_listbox.pack(pady=15)
        self.refresh_project_list()
        
        action_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        action_frame.pack(pady=5)
        
        ctk.CTkButton(action_frame, text="Open Project", command=self.open_project, width=150).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(action_frame, text="Delete Project", command=self.delete_project, width=150, fg_color="#dc3545", hover_color="#c82333").pack(side=tk.LEFT, padx=10)

    def refresh_project_list(self):
        self.project_listbox.delete(0, tk.END)
        for proj in os.listdir(BASE_DIR):
            if os.path.isdir(os.path.join(BASE_DIR, proj)):
                self.project_listbox.insert(tk.END, proj)

    def create_project(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create Project")
        self.center_window(dialog, 350, 250)
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Project Name:").pack(pady=(15, 2))
        entry_name = ctk.CTkEntry(dialog, width=280)
        entry_name.pack(pady=5)
        entry_name.focus_set() 

        ctk.CTkLabel(dialog, text="Project Description:").pack(pady=(10, 2))
        entry_desc = ctk.CTkEntry(dialog, width=280)
        entry_desc.pack(pady=5)

        def on_submit():
            name = entry_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Project name is required!", parent=dialog)
                return
            desc = entry_desc.get().strip()
            
            proj_path = os.path.join(BASE_DIR, name)
            if os.path.exists(proj_path):
                messagebox.showerror("Error", "Project already exists!", parent=dialog)
                return
                
            os.makedirs(proj_path)
            os.makedirs(os.path.join(proj_path, 'test_cases'))
            
            meta = {"name": name, "description": desc}
            with open(os.path.join(proj_path, 'project_metadata.json'), 'w') as f:
                json.dump(meta, f)
                
            dialog.destroy()
            self.refresh_project_list()

        ctk.CTkButton(dialog, text="Save Project", command=on_submit).pack(pady=20)
        self.root.wait_window(dialog)

    def delete_project(self):
        sel = self.project_listbox.curselection()
        if not sel: return
        proj_name = self.project_listbox.get(sel[0])
        
        if messagebox.askyesno("Confirm", f"Delete project '{proj_name}' and all its test cases?"):
            shutil.rmtree(os.path.join(BASE_DIR, proj_name))
            self.refresh_project_list()

    def open_project(self):
        sel = self.project_listbox.curselection()
        if not sel: return
        self.current_project = self.project_listbox.get(sel[0])
        self.show_test_case_menu()

    #UI: TEST CASE MENU
    def show_test_case_menu(self):
        self.clear_window()
        
        ctk.CTkLabel(self.root, text=f"Project: {self.current_project}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="Back to Projects", command=self.show_project_dashboard, fg_color="#6c757d", hover_color="#5a6268").pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Record New Test Case", command=self.start_recorder_ui, fg_color="#17a2b8", hover_color="#138496").pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Run All Test Cases", command=self.run_all_test_cases, fg_color="#28a745", hover_color="#218838").pack(side=tk.LEFT, padx=5)

        self.tc_listbox = tk.Listbox(self.root, width=70, height=10, bg="#2b2b2b", fg="white", 
                                     selectbackground="#1f538d", borderwidth=0, highlightthickness=1, highlightbackground="#565b5e")
        self.tc_listbox.pack(pady=15)
        self.refresh_tc_list()

        action_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        action_frame.pack(pady=5)

        ctk.CTkButton(action_frame, text="Run Selected", command=self.run_selected_tc, width=150).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(action_frame, text="Delete Selected", command=self.delete_tc, width=150, fg_color="#dc3545", hover_color="#c82333").pack(side=tk.LEFT, padx=10)

    def refresh_tc_list(self):
        self.tc_listbox.delete(0, tk.END)
        tc_dir = os.path.join(BASE_DIR, self.current_project, 'test_cases')
        
        files = [f for f in os.listdir(tc_dir) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getctime(os.path.join(tc_dir, x)))
        
        for tc in files:
            self.tc_listbox.insert(tk.END, tc.replace('.json', ''))

    def delete_tc(self):
        sel = self.tc_listbox.curselection()
        if not sel: return
        tc_name = self.tc_listbox.get(sel[0])
        
        if messagebox.askyesno("Confirm", f"Delete Test Case '{tc_name}'?"):
            tc_path = os.path.join(BASE_DIR, self.current_project, 'test_cases', f"{tc_name}.json")
            os.remove(tc_path)
            self.refresh_tc_list()

    #RECORDER LOGIC & UI
    def start_recorder_ui(self):
        self.root.withdraw() 
        
        self.recorder_window = ctk.CTkToplevel(self.root)
        self.recorder_window.title("Recorder")
        
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - 290 
        self.recorder_window.geometry(f"270x70+{x_pos}+20")
        self.recorder_window.attributes('-topmost', True) 
        self.recorder_window.protocol("WM_DELETE_WINDOW", self.stop_recording)
        
        self.btn_rec = ctk.CTkButton(self.recorder_window, text="Start", command=self.toggle_record, width=70, fg_color="#28a745", hover_color="#218838")
        self.btn_rec.pack(side=tk.LEFT, padx=5, pady=10)
        
        self.btn_pause = ctk.CTkButton(self.recorder_window, text="Pause", command=self.toggle_pause, width=70, state="disabled")
        self.btn_pause.pack(side=tk.LEFT, padx=5, pady=10)
        
        ctk.CTkButton(self.recorder_window, text="Stop & Save", command=self.stop_recording, width=90, fg_color="#dc3545", hover_color="#c82333").pack(side=tk.LEFT, padx=5, pady=10)

    def toggle_record(self):
        if not self.is_recording:
            self.is_recording = True
            self.is_paused = False
            self.recording_events = []
            self.start_time = time.time()
            self.pause_offset = 0
            
            self.btn_rec.configure(state="disabled")
            self.btn_pause.configure(state="normal")
            
            self.mouse_listener = pynput.mouse.Listener(on_click=self.on_click)
            self.keyboard_listener = pynput.keyboard.Listener(on_press=self.on_press)
            self.mouse_listener.start()
            self.keyboard_listener.start()

    def toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.configure(text="Pause", fg_color="#1f538d")
            self.pause_offset += (time.time() - self.pause_start_time)
        else:
            self.is_paused = True
            self.btn_pause.configure(text="Resume", fg_color="#fd7e14", hover_color="#e8590c")
            self.pause_start_time = time.time()

    def is_click_on_recorder_ui(self, x, y):
        if not self.recorder_window: return False
        try:
            rx = self.recorder_window.winfo_rootx()
            ry = self.recorder_window.winfo_rooty()
            rw = self.recorder_window.winfo_width()
            rh = self.recorder_window.winfo_height()
            return rx <= x <= rx + rw and ry <= y <= ry + rh
        except:
            return False

    def on_click(self, x, y, button, pressed):
        if self.is_paused or not self.is_recording: return
        if self.is_click_on_recorder_ui(x, y): return 
        
        if pressed:
            actual_time = time.time() - self.start_time - self.pause_offset
            self.recording_events.append({'type': 'click', 'x': x, 'y': y, 'button': str(button), 'time': actual_time})

    def on_press(self, key):
        if self.is_paused or not self.is_recording: return
        
        actual_time = time.time() - self.start_time - self.pause_offset
        self.recording_events.append({'type': 'press', 'key': str(key), 'time': actual_time})

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.mouse_listener: self.mouse_listener.stop()
            if self.keyboard_listener: self.keyboard_listener.stop()
            
        if self.recorder_window:
            self.recorder_window.destroy()
        
        if self.recording_events:
            self.save_test_case_dialog()
        else:
            self.root.deiconify()

    def save_test_case_dialog(self):
        save_window = ctk.CTkToplevel(self.root)
        save_window.title("Save Test Case")
        self.center_window(save_window, 400, 500)
        save_window.grab_set()
        
        ctk.CTkLabel(save_window, text="Test Case Name:").pack(pady=(15, 2))
        entry_name = ctk.CTkEntry(save_window, width=320)
        entry_name.pack(pady=2)
        entry_name.focus_set()
        
        ctk.CTkLabel(save_window, text="Description:").pack(pady=(10, 2))
        entry_desc = ctk.CTkEntry(save_window, width=320)
        entry_desc.pack(pady=2)
        
        ctk.CTkLabel(save_window, text="Expected Result:").pack(pady=(10, 2))
        entry_exp = ctk.CTkEntry(save_window, width=320)
        entry_exp.pack(pady=2)
        
        ctk.CTkLabel(save_window, text="Draft Steps:").pack(pady=(10, 2))
        txt_steps = ctk.CTkTextbox(save_window, width=320, height=150)
        txt_steps.pack(pady=2)
        
        draft_text = ""
        step_num = 1
        buffer_text = ""
        last_time = 0

        def flush_buffer():
            nonlocal draft_text, step_num, buffer_text
            if buffer_text:
                draft_text += f"{step_num}. Type '{buffer_text}'\n"
                step_num += 1
                buffer_text = ""

        for ev in self.recording_events:
            if ev['type'] == 'click':
                flush_buffer()
                btn_name = ev['button'].split('.')[-1]
                draft_text += f"{step_num}. Click {btn_name} at ({ev['x']}, {ev['y']})\n"
                step_num += 1
                last_time = ev['time']
                
            elif ev['type'] == 'press':
                key_val = ev['key']
                current_time = ev['time']
                
                if key_val.startswith("'") and key_val.endswith("'") and len(key_val) == 3:
                    char = key_val.strip("'")
                    if buffer_text and (current_time - last_time > 0.5):
                        flush_buffer()
                    buffer_text += char
                    last_time = current_time
                else:
                    flush_buffer()
                    key_name = key_val.replace("Key.", "")
                    draft_text += f"{step_num}. Press '{key_name}'\n"
                    step_num += 1
                    last_time = current_time

        flush_buffer()
                
        txt_steps.insert("1.0", draft_text)
        
        def do_save():
            tc_name = entry_name.get().strip()
            if not tc_name:
                messagebox.showerror("Error", "Name is required", parent=save_window)
                return
                
            data = {
                "metadata": {
                    "name": tc_name,
                    "description": entry_desc.get(),
                    "expected_result": entry_exp.get(),
                    "steps": txt_steps.get("1.0", "end-1c").strip()
                },
                "events": self.recording_events
            }
            
            tc_path = os.path.join(BASE_DIR, self.current_project, 'test_cases', f"{tc_name}.json")
            with open(tc_path, 'w') as f:
                json.dump(data, f)
                
            save_window.destroy()
            self.root.deiconify()
            self.refresh_tc_list()
            
        ctk.CTkButton(save_window, text="Save Test Case", command=do_save, fg_color="#28a745", hover_color="#218838").pack(pady=20)

    #PLAYBACK LOGIC & UI
    def run_selected_tc(self):
        sel = self.tc_listbox.curselection()
        if not sel: return
        tc_name = self.tc_listbox.get(sel[0])
        self.start_playback_ui([f"{tc_name}.json"])

    def run_all_test_cases(self):
        tc_dir = os.path.join(BASE_DIR, self.current_project, 'test_cases')
        files = [f for f in os.listdir(tc_dir) if f.endswith('.json')]
        if not files: return
        files.sort(key=lambda x: os.path.getctime(os.path.join(tc_dir, x)))
        self.start_playback_ui(files)

    def start_playback_ui(self, file_list):
        self.root.withdraw()
        self.stop_playback_flag = False
        
        self.playback_window = ctk.CTkToplevel(self.root)
        self.playback_window.title("Playback")
        
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - 140 
        self.playback_window.geometry(f"120x60+{x_pos}+20")
        self.playback_window.attributes('-topmost', True) 
        self.playback_window.protocol("WM_DELETE_WINDOW", self.force_stop_playback)
        
        ctk.CTkButton(self.playback_window, text="Stop & Back", command=self.force_stop_playback, fg_color="#dc3545", hover_color="#c82333").pack(padx=10, pady=15)

        threading.Thread(target=self._playback_worker, args=(file_list,), daemon=True).start()

    def force_stop_playback(self):
        self.stop_playback_flag = True
        if self.playback_window:
            self.playback_window.destroy()
        self.root.deiconify()

    def stoppable_sleep(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self.stop_playback_flag: return False
            time.sleep(0.01)
        return True

    def _playback_worker(self, file_list):
        mouse = MouseController()
        keyboard = KeyboardController()
        tc_dir = os.path.join(BASE_DIR, self.current_project, 'test_cases')
        
        for file in file_list:
            if self.stop_playback_flag: break
            
            file_path = os.path.join(tc_dir, file)
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            events = data.get('events', [])
            if not events: continue
            
            if not self.stoppable_sleep(2): break 
            
            start_time = time.time()
            for event in events:
                if self.stop_playback_flag: break
                
                current_time = time.time() - start_time
                sleep_duration = event['time'] - current_time

                if sleep_duration > 0:
                    if not self.stoppable_sleep(sleep_duration): break

                if self.stop_playback_flag: break

                if event['type'] == 'click':
                    mouse.position = (event['x'], event['y'])
                    button_str = event['button']
                    btn = Button.left
                    if 'right' in button_str: btn = Button.right
                    elif 'middle' in button_str: btn = Button.middle
                    mouse.click(btn)
                elif event['type'] == 'press':
                    key_str = event['key']
                    if key_str.startswith('Key.'):
                        key_name = key_str.split('.')[1]
                        try:
                            key_obj = getattr(Key, key_name)
                            keyboard.press(key_obj)
                            keyboard.release(key_obj)
                        except AttributeError: pass
                    else:
                        char = key_str.strip("'")
                        keyboard.press(char)
                        keyboard.release(char)
                        
        if not self.stop_playback_flag:
            messagebox.showinfo("Playback", "Playback Completed!")
            self.root.after(0, self.force_stop_playback)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == '__main__':
    root = ctk.CTk()
    app = AutomationApp(root)
    root.mainloop()