import tkinter as tk
from tkinter import messagebox, Spinbox, filedialog
import threading
import time
import datetime
import platform
import subprocess
import os
import uuid

# --- ライブラリのインポートチェック (変更なし) ---
try:
    from playsound import playsound
except ImportError:
    messagebox.showerror("ライブラリ不足", "playsoundライブラリが必要です。\n'pip install playsound==1.2.2' を実行してください。")
    exit()
if platform.system() == "Windows":
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except ImportError:
        messagebox.showerror("ライブラリ不足", "pycawライブラリが必要です。\n'pip install pycaw' を実行してください。")
        exit()

class FinalAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高機能アラーム")
        self.root.geometry("400x200")

        self.alarms = {}
        self.sound_stop_event = threading.Event()
        self.snooze_minutes = 5
        self.alarm_list_window = None

        # --- メイン画面のUI (変更なし) ---
        self.clock_label = tk.Label(root, text="", font=("Helvetica", 48, "bold"))
        self.clock_label.pack(pady=20)
        self.update_clock()

        self.show_alarms_button = tk.Button(root, text="アラーム一覧・設定", font=("", 14), command=self.open_alarm_list_window)
        self.show_alarms_button.pack(pady=10)

        threading.Thread(target=self.alarm_monitor_thread, daemon=True).start()

    def update_clock(self):
        now = time.strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def alarm_monitor_thread(self):
        """全てのアラームをバックグラウンドで監視し続ける"""
        last_triggered_minute = ""
        while True:
            now = datetime.datetime.now()
            current_minute = now.strftime("%H:%M")
            today_weekday = now.weekday()  # 月曜=0, 日曜=6

            if current_minute != last_triggered_minute:
                for alarm_id, alarm in list(self.alarms.items()):
                    # アラームが有効で、時刻が一致するかチェック
                    if alarm['enabled'] and alarm['time'] == current_minute:
                        # <<< 変更点: 曜日指定のロジック ---
                        is_one_time = not any(alarm['repeat_days'])
                        is_repeat_today = alarm['repeat_days'][today_weekday]

                        if is_repeat_today or is_one_time:
                            print(f"時間です！ ({alarm['time']})")
                            self.trigger_alarm_action(alarm_id, alarm)
                            last_triggered_minute = current_minute
                            
                            # 一回だけのアラームなら鳴らした後に無効化
                            if is_one_time:
                                self.alarms[alarm_id]['enabled'] = False
                                self.root.after(0, self.refresh_alarm_list) # UIを更新
                        # --- 変更点ここまで ---
            time.sleep(1)

    def open_alarm_list_window(self):
        """アラーム一覧画面を開く"""
        if self.alarm_list_window and self.alarm_list_window.winfo_exists():
            self.alarm_list_window.lift()
            return

        self.alarm_list_window = tk.Toplevel(self.root)
        self.alarm_list_window.title("アラーム一覧")
        self.alarm_list_window.geometry("500x450")

        add_button = tk.Button(self.alarm_list_window, text="＋ 新規アラームを追加", command=lambda: self.open_alarm_details_window(None))
        add_button.pack(pady=10)

        self.alarm_list_frame = tk.Frame(self.alarm_list_window)
        self.alarm_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_alarm_list()

    def refresh_alarm_list(self):
        """アラーム一覧画面の表示を更新する"""
        if not self.alarm_list_window or not self.alarm_list_window.winfo_exists():
            return
        for widget in self.alarm_list_frame.winfo_children():
            widget.destroy()
        if not self.alarms:
            tk.Label(self.alarm_list_frame, text="アラームは設定されていません").pack(pady=20)
            return

        sorted_alarms = sorted(self.alarms.items(), key=lambda item: item[1]['time'])
        for alarm_id, alarm in sorted_alarms:
            frame = tk.Frame(self.alarm_list_frame, relief="groove", borderwidth=2)
            frame.pack(fill="x", pady=5, padx=5)

            left_frame = tk.Frame(frame)
            left_frame.pack(side="left", padx=10, pady=5)
            
            tk.Label(left_frame, text=alarm['time'], font=("Helvetica", 24)).pack(anchor="w")
            
            # <<< 変更点: 繰り返し曜日の表示 ---
            days = ["月", "火", "水", "木", "金", "土", "日"]
            repeat_str = " ".join([days[i] for i, repeat in enumerate(alarm['repeat_days']) if repeat])
            if not repeat_str:
                repeat_str = "一回のみ"
            tk.Label(left_frame, text=repeat_str, fg="gray").pack(anchor="w")
            # --- 変更点ここまで ---

            right_frame = tk.Frame(frame)
            right_frame.pack(side="right", padx=10)

            tk.Button(right_frame, text="削除", command=lambda i=alarm_id: self.delete_alarm(i)).pack(fill="x")
            tk.Button(right_frame, text="編集", command=lambda i=alarm_id: self.open_alarm_details_window(i)).pack(fill="x") # <<< 変更点: 編集ボタン

            is_enabled_var = tk.BooleanVar(value=alarm['enabled'])
            tk.Checkbutton(right_frame, text="有効", variable=is_enabled_var,
                           command=lambda i=alarm_id, v=is_enabled_var: self.toggle_alarm(i, v)).pack(fill="x")

    def open_alarm_details_window(self, alarm_id):
        """新規追加または編集のためのウィンドウを開く"""
        details_window = tk.Toplevel(self.alarm_list_window)
        is_new = alarm_id is None
        details_window.title("新規アラーム" if is_new else "アラームの編集")
        
        alarm = self.alarms.get(alarm_id, {}) # 既存アラームか空の辞書を取得

        # 時刻設定
        time_frame = tk.Frame(details_window); time_frame.pack(pady=10)
        hour_var = tk.StringVar(value=alarm.get('time', '07:00').split(':')[0])
        minute_var = tk.StringVar(value=alarm.get('time', '07:00').split(':')[1])
        Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f", textvariable=hour_var).pack(side="left")
        tk.Label(time_frame, text=":").pack(side="left")
        Spinbox(time_frame, from_=0, to=59, width=5, format="%02.0f", textvariable=minute_var).pack(side="left")

        # <<< 変更点: 曜日指定UI ---
        repeat_frame = tk.Frame(details_window); repeat_frame.pack(pady=10)
        days = ["月", "火", "水", "木", "金", "土", "日"]
        repeat_days_vars = [tk.BooleanVar(value=v) for v in alarm.get('repeat_days', [False]*7)]
        for i, day in enumerate(days):
            tk.Checkbutton(repeat_frame, text=day, variable=repeat_days_vars[i]).pack(side="left")
        # --- 変更点ここまで ---

        # サウンド設定
        sound_file = {'path': alarm.get('sound', 'alarm.mp3')}
        sound_label = tk.Label(details_window, text=f"音源: {os.path.basename(sound_file['path'])}")
        def select_sound():
            path = filedialog.askopenfilename(filetypes=[("MP3ファイル", "*.mp3")])
            if path:
                sound_file['path'] = path
                sound_label.config(text=f"音源: {os.path.basename(path)}")
        tk.Button(details_window, text="音源を選択", command=select_sound).pack(pady=5)
        sound_label.pack()

        def on_save():
            self.save_alarm(
                alarm_id=alarm_id,
                time_str=f"{hour_var.get()}:{minute_var.get()}",
                sound_path=sound_file['path'],
                repeat_days=[v.get() for v in repeat_days_vars]
            )
            details_window.destroy()

        tk.Button(details_window, text="保存", command=on_save).pack(pady=10)

    def save_alarm(self, alarm_id, time_str, sound_path, repeat_days):
        """アラームを新規保存または更新する"""
        if alarm_id is None:
            alarm_id = str(uuid.uuid4()) # 新規の場合はIDを生成
        
        self.alarms[alarm_id] = {
            'time': time_str,
            'sound': sound_path,
            'enabled': True,
            'repeat_days': repeat_days
        }
        print(f"アラーム保存: ID={alarm_id}")
        self.refresh_alarm_list()

    def delete_alarm(self, alarm_id):
        if alarm_id in self.alarms:
            del self.alarms[alarm_id]
            self.refresh_alarm_list()

    def toggle_alarm(self, alarm_id, var):
        if alarm_id in self.alarms:
            self.alarms[alarm_id]['enabled'] = var.get()

    def trigger_alarm_action(self, alarm_id, alarm):
        self.sound_stop_event.clear()
        self.set_max_volume()
        threading.Thread(target=self.play_alarm_sound, args=(alarm['sound'],), daemon=True).start()
        self.show_snooze_popup(alarm_id, alarm)

    def show_snooze_popup(self, alarm_id, alarm):
        popup = tk.Toplevel(self.root)
        popup.title("アラーム")
        
        def on_snooze():
            self.sound_stop_event.set()
            popup.destroy()
            snooze_time = (datetime.datetime.now() + datetime.timedelta(minutes=self.snooze_minutes)).strftime("%H:%M")
            self.save_alarm(None, snooze_time, alarm['sound'], [False]*7) # スヌーズは一回のみ

        def on_stop():
            self.sound_stop_event.set()
            popup.destroy()

        tk.Label(popup, text=f"{alarm['time']}です！", font=("", 14)).pack(pady=10)
        tk.Button(popup, text=f"スヌーズ ({self.snooze_minutes}分)", command=on_snooze).pack(side="left", padx=10, pady=10)
        tk.Button(popup, text="停止", command=on_stop).pack(side="left", padx=10, pady=10)

    def play_alarm_sound(self, sound_path):
        try:
            while not self.sound_stop_event.is_set():
                playsound(sound_path)
        except Exception as e:
            self.root.after(0, messagebox.showerror, "再生エラー", f"アラーム音の再生に失敗しました。\n{e}")

    def set_max_volume(self):
        system = platform.system()
        try:
            if system == "Windows":
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevel(0.0, None)
                volume.SetMute(0, None)
            elif system == "Darwin":
                subprocess.run(['osascript', '-e', 'set volume output volume 100'], check=True)
            elif system == "Linux":
                subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', '100%'], check=True)
        except Exception as e:
            messagebox.showerror("音量設定エラー", f"音量の設定中にエラーが発生しました。\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FinalAlarmApp(root)
    root.mainloop()