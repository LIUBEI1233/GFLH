import sys
import os
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from gflzirc import GFLProxy, set_windows_proxy, STATIC_KEY


TARGET_BUILDINGS = {
    "86402": "670115",
    "86399": "670116"
}

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class NightmareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GFLH - 偷看涅托底裤")
        self.root.geometry("680x600")
        icon_path = get_resource_path("mk/icon.ico")
        if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                except Exception as e:
                    print(f"Set icon failed: {e}")
                else:
                    print(f"Icon not found: {icon_path}")

        self.proxy_instance = None
        self.active_proxy = False
        self.monitor_thread = None
        self.stop_monitor_flag = False

    
        self.var_port = tk.IntVar(value=8080)
        self.var_auto_stop = tk.BooleanVar(value=True)   
        self.var_debug = tk.BooleanVar(value=False)       
        self.setup_ui()

   
    def setup_ui(self):
        frame_ctrl = ttk.LabelFrame(self.root, text="1. 偷看状态", padding=10)
        frame_ctrl.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_ctrl, text="偷看端口:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_ctrl, textvariable=self.var_port, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)

        self.btn_start = ttk.Button(frame_ctrl, text="开始偷看", command=self.start_monitor)
        self.btn_start.grid(row=0, column=2, padx=10)

        self.btn_stop = ttk.Button(frame_ctrl, text="停止偷看", command=self.stop_monitor, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=3, padx=5)

        self.lbl_status = ttk.Label(frame_ctrl, text="● 准备偷看", foreground="gray")
        self.lbl_status.grid(row=0, column=4, padx=15)

        
        frame_opts = ttk.LabelFrame(self.root, text="2. 偷看选项", padding=10)
        frame_opts.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(frame_opts, text="偷看到了自动停止偷看", variable=self.var_auto_stop).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(frame_opts, text="偷看所有的底裤！", variable=self.var_debug).pack(anchor=tk.W, pady=2)

        target_text = ", ".join([f"{k},{v}" for k, v in TARGET_BUILDINGS.items()])
        ttk.Label(frame_opts, text=f"期望: {target_text}").pack(anchor=tk.W, pady=5)

        
        frame_log = ttk.LabelFrame(self.root, text="3. 今日底裤颜色", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(
            frame_log, height=15, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        
        self.txt_log.tag_config("found" )
        self.txt_log.tag_config("info")
        self.txt_log.tag_config("warn")

    def log(self, msg, tag=None):
        try:
            if self.root.winfo_exists():
                self.root.after(0, self._append_log, msg, tag)
        except tk.TclError:
            pass

    def _append_log(self, msg, tag=None):
        self.txt_log.config(state=tk.NORMAL)
        if tag:
            self.txt_log.insert(tk.END, msg + "\n", tag)
        else:
            self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

   
    def _traffic_callback(self, event_type, url, data):
        if event_type.upper() != "S2C":
            return

        if self.var_debug.get():
            self.log(f"探测到信号: {url}", "info")

        if "Mission_startMission" not in url and "startMission" not in url:
            return

        if not isinstance(data, dict):
            self.log("信号干扰，看不清...", "warn")
            return

        building_info = data.get("building_info")
        
        if self.var_debug.get():
            if building_info:
                self.log(f"发现底裤: {json.dumps(building_info, ensure_ascii=False)}", "info")
            else:
                self.log("啥也没有...", "info")

        if not isinstance(building_info, dict):
            self.log("今天的底裤没穿？没有 building_info", "warn")
            return  

        all_found = True
        found_details = {}

        for spot_id, expected_bid in TARGET_BUILDINGS.items():
            spot_info = building_info.get(spot_id)
            if spot_info and spot_info.get("building_id") == expected_bid:
                found_details[spot_id] = expected_bid
            else:
                all_found = False

        if all_found and len(found_details) == len(TARGET_BUILDINGS):
            msg = f"白色！ " + ", ".join([f"{k}/{v}" for k, v in found_details.items()])
            self.log(msg, "found")
            messagebox.showinfo("偷看到了！", f"涅托小姐今天的颜色！\n{msg}")

            if self.var_auto_stop.get():
                self.log("看够了，收工！自动停止偷看...", "info")
                self.root.after(0, self.stop_monitor)
        else:
      
            spot_status = []
            for spot_id, expected_bid in TARGET_BUILDINGS.items():
                spot_info = building_info.get(spot_id)
                if spot_info:
                    actual_bid = spot_info.get("building_id", "无id")
                    if actual_bid == expected_bid:
                        spot_status.append(f"{spot_id}->{actual_bid} ✓")
                    else:
                        spot_status.append(f"{spot_id}->{actual_bid} ✗ (期望{expected_bid})")
                else:
                    spot_status.append(f"{spot_id}->不存在 ✗")
            
           
            if self.var_debug.get():
                self.log(f"今天穿的不是同一条... {', '.join(spot_status)}", "info")
            else:
                self.log(f"捕获到 startMission，色号不匹配: {', '.join(spot_status)}", "info")


    def monitor_worker(self):
        port = self.var_port.get()
        try:
            self.proxy_instance = GFLProxy(port, STATIC_KEY, self._traffic_callback)
            self.proxy_instance.start()
            set_windows_proxy(True, f"127.0.0.1:{port}")
            self.active_proxy = True
            self.log(f"[*] 无人机就绪，端口 {port}，Windows 摄像头已准备", "info")
            self.log(f"[*] 目标色号: {TARGET_BUILDINGS}", "info")
            self.log("[*] 请进入游戏，等待涅托小姐出现...", "info")

            while not self.stop_monitor_flag:
                time.sleep(0.5)

        except Exception as e:
            self.log(f"[Man!] 无人机坠毁了！: {e}", "warn")
        finally:
            if self.proxy_instance:
                try:
                    self.proxy_instance.stop()
                except:
                    pass
                self.proxy_instance = None
            if self.active_proxy:
                set_windows_proxy(False)
                self.active_proxy = False
            self.log("[*] 跑路，下次再看 ", "info")
            self.root.after(0, self._reset_ui)

    def start_monitor(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.log("已经在偷看力！...", "warn")
            return

        try:
            port = self.var_port.get()
            if not (1024 <= port <= 65535):
                raise ValueError("端口范围 1024-65535")
        except Exception as e:
            messagebox.showerror("错误", f"端口无效: {e}")
            return

        self.stop_monitor_flag = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text="● 偷看中", foreground="green")

        self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True)
        self.monitor_thread.start()

    def stop_monitor(self):
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.log("都没开始偷看呢...", "warn")
            self._reset_ui()
            return
        self.stop_monitor_flag = True
        self.log("[*] 等等，再让我看一眼... 该跑路了！", "info")

    def _reset_ui(self):
        try:
            if self.root.winfo_exists():
                self.btn_start.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                self.lbl_status.config(text="● 偷看结束", foreground="gray")
                self.monitor_thread = None
        except tk.TclError:
            pass

    def on_close(self):
        self.stop_monitor_flag = True
        if self.proxy_instance:
            try:
                self.proxy_instance.stop()
            except:
                pass
        if self.active_proxy:
            set_windows_proxy(False)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NightmareApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()