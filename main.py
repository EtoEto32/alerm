import tkinter as tk
from tkinter import messagebox, Spinbox, filedialog
import threading
import time
import datetime
import platform
import subprocess
import os
import uuid # <<< 変更点: アラームにユニークなIDを付けるためにインポート

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

class MultiAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多機能アラーム")
        self.root.geometry("400x200")

        self.alarms = {}  # <<< 変更点: アラームをIDで管理する辞書に変更
        self.sound_stop_event = threading.Event()
        self.snooze_minutes = 5
        self.alarm_list_window = None # アラーム一覧画面の参照を保持

        # --- メイン画面のUI ---
        self.clock_label = tk.Label(root, text="", font=("Helvetica", 48, "bold"))
        self.clock_label.pack(pady=20)
        self.update_clock()

        self.show_alarms_button = tk.Button(root, text="アラーム一覧", font=("", 14), command=self.open_alarm_list_window)
        self.show_alarms_button.pack(pady=10)

        # --- バックグラウンドでアラームを監視するスレッドを開始 ---
        threading.Thread(target=self.alarm_monitor_thread, daemon=True).start()

    def update_clock(self):
        """メイン画面の時計を更新"""
        now = time.strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def alarm_monitor_thread(self):
        """全てのアラームをバックグラウンドで監視し続ける"""
        last_triggered_minute = ""
        while True:
            now = datetime.datetime.now()
            current_minute = now.strftime("%H:%M")

            # 同じ分に何度も鳴らないように、分が変わったときだけチェック
            if current_minute != last_triggered_minute:
                for alarm_id, alarm in list(self.alarms.items()):
                    if alarm['enabled'] and alarm['time'] == current_minute:
                        print(f"時間です！ ({alarm['time']})")
                        self.trigger_alarm_action(alarm)
                        last_triggered_minute = current_minute
            
            time.sleep(1)

    # <<< 変更点: アラーム一覧画面の作成と管理 ---
    def open_alarm_list_window(self):
        """アラーム一覧画面を開く"""
        if self.alarm_list_window and self.alarm_list_window.winfo_exists():
            self.alarm_list_window.lift()
            return

        self.alarm_list_window = tk.Toplevel(self.root)
        self.alarm_list_window.title("アラーム一覧")
        self.alarm_list_window.geometry("450x400")

        add_button = tk.Button(self.alarm_list_window, text="＋ 新規アラームを追加", command=self.open_add_alarm_window)
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
            no_alarm_label = tk.Label(self.alarm_list_frame, text="アラームは設定されていません")
            no_alarm_label.pack(pady=20)
            return

        # 時刻順にソートして表示
        sorted_alarms = sorted(self.alarms.items(), key=lambda item: item[1]['time'])

        for alarm_id, alarm in sorted_alarms:
            frame = tk.Frame(self.alarm_list_frame, relief="groove", borderwidth=2)
            frame.pack(fill="x", pady=5, padx=5)

            time_label = tk.Label(frame, text=alarm['time'], font=("Helvetica", 24))
            time_label.pack(side="left", padx=10)

            sound_label = tk.Label(frame, text=os.path.basename(alarm['sound']), fg="gray")
            sound_label.pack(side="left", padx=10)

            delete_button = tk.Button(frame, text="削除", command=lambda i=alarm_id: self.delete_alarm(i))
            delete_button.pack(side="right", padx=10)

            is_enabled_var = tk.BooleanVar(value=alarm['enabled'])
            toggle_button = tk.Checkbutton(frame, text="有効", variable=is_enabled_var, 
                                           command=lambda i=alarm_id, v=is_enabled_var: self.toggle_alarm(i, v))
            toggle_button.pack(side="right")

    def open_add_alarm_window(self):
        """新規アラームを追加するためのウィンドウを開く"""
        add_window = tk.Toplevel(self.alarm_list_window)
        add_window.title("新規アラーム")
        add_window.geometry("300x200")

        time_frame = tk.Frame(add_window)
        time_frame.pack(pady=10)
        hour_spinbox = Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f")
        hour_spinbox.pack(side=tk.LEFT)
        tk.Label(time_frame, text=":").pack(side=tk.LEFT)
        minute_spinbox = Spinbox(time_frame, from_=0, to=59, width=5, format="%02.0f")
        minute_spinbox.pack(side=tk.LEFT)

        sound_file = {'path': 'alarm.mp3'} # デフォルト音源
        sound_label = tk.Label(add_window, text=f"音源: {os.path.basename(sound_file['path'])}")
        
        def select_sound():
            path = filedialog.askopenfilename(filetypes=[("MP3ファイル", "*.mp3")])
            if path:
                sound_file['path'] = path
                sound_label.config(text=f"音源: {os.path.basename(path)}")
        
        sound_button = tk.Button(add_window, text="音源を選択", command=select_sound)
        sound_button.pack(pady=5)
        sound_label.pack()

        def save_new_alarm():
            alarm_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}"
            self.add_alarm(alarm_time, sound_file['path'])
            add_window.destroy()

        save_button = tk.Button(add_window, text="保存", command=save_new_alarm)
        save_button.pack(pady=10)

    # <<< 変更点: アラームデータの操作メソッド ---
    def add_alarm(self, time_str, sound_path):
        alarm_id = str(uuid.uuid4()) # ユニークなIDを生成
        self.alarms[alarm_id] = {
            'time': time_str,
            'sound': sound_path,
            'enabled': True
        }
        print(f"アラーム追加: ID={alarm_id}, 時刻={time_str}")
        self.refresh_alarm_list()

    def delete_alarm(self, alarm_id):
        if alarm_id in self.alarms:
            del self.alarms[alarm_id]
            print(f"アラーム削除: ID={alarm_id}")
            self.refresh_alarm_list()

    def toggle_alarm(self, alarm_id, var):
        if alarm_id in self.alarms:
            self.alarms[alarm_id]['enabled'] = var.get()
            status = "有効化" if var.get() else "無効化"
            print(f"アラーム{status}: ID={alarm_id}")

    # --- アラーム発動時の処理 (ほぼ変更なし) ---
    def trigger_alarm_action(self, alarm):
        self.sound_stop_event.clear()
        self.set_max_volume()
        threading.Thread(target=self.play_alarm_sound, args=(alarm['sound'],), daemon=True).start()
        self.show_snooze_popup(alarm)

    def show_snooze_popup(self, alarm):
        popup = tk.Toplevel(self.root)
        popup.title("アラーム")
        
        def on_snooze():
            self.sound_stop_event.set()
            popup.destroy()
            snooze_time = (datetime.datetime.now() + datetime.timedelta(minutes=self.snooze_minutes)).strftime("%H:%M")
            # スヌーズ用の一時的なアラームを追加
            self.add_alarm(snooze_time, alarm['sound'])
            print(f"スヌーズ設定: {snooze_time}")

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
        # (この関数の内容は変更なし)
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiAlarmApp(root)
    root.mainloop()