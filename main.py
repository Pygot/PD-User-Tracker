"""
╔════════════════════════════════════════════════════════════╗
║  Author  : pygot                                           ║
║  GitHub  : https://github.com/pygot                        ║
╚════════════════════════════════════════════════════════════╝
"""

from tkinter import ttk, messagebox

import threading, json, os, time, urllib.request, re, socket, queue, random
import tkinter as tk
import pytchat

CONFIG = "config.json"
DEFAULT = {
    "platform": "YouTube",
    "target_id": "dQw4w9WgXcQ",
    "cmd_prefix": "",
    "limit": 2,
    "auto_copy": False,
    "auto_restart": True,
    "mode_roulette": False,
    "roulette_duration": 30,
    "mode_latest": False,
    "history": {},
    "blacklist": ["roblox", "builderman", "robux"],
    "blacklist_authors": [],
}

BG = "#121212"
FG = "#E0E0E0"
PANEL = "#1E1E1E"
ACCENT = "#9146FF"
SUCCESS = "#06D6A0"
ERROR = "#EF476F"
WARN = "#FFD166"


class TwitchClient:
    def __init__(self, channel):
        self.sock = socket.socket()
        self.channel = channel.lower().replace("#", "")
        self.running = True
        self.buffer = ""
        self.connected = False

    def connect(self):
        try:
            self.sock = socket.socket()
            self.sock.settimeout(2)
            self.sock.connect(("irc.chat.twitch.tv", 6667))
            self.sock.send(f"NICK justinfan{int(time.time())}\n".encode("utf-8"))
            self.sock.send(f"JOIN #{self.channel}\n".encode("utf-8"))
            self.connected = True
            return True
        except:
            return False

    def get_messages(self):
        if not self.connected:
            return []
        try:
            try:
                resp = self.sock.recv(2048).decode("utf-8")
            except socket.timeout:
                return []
            self.buffer += resp
            msgs = []
            if "\n" in self.buffer:
                lines = self.buffer.split("\n")
                self.buffer = lines.pop()
                for line in lines:
                    if "PRIVMSG" in line:
                        parts = line.split(":", 2)
                        if len(parts) > 2:
                            user = line.split("!", 1)[0][1:]
                            message = parts[2].strip()
                            msgs.append((user, message))
            return msgs
        except:
            return []

    def close(self):
        self.running = False
        self.connected = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.sock.close()
        except:
            pass


class App:
    def __init__(self, r):
        self.r = r
        r.title("PD User Tracker")
        r.geometry("580x650")
        r.minsize(580, 650)
        r.configure(bg=BG)

        self.style()
        self.cfg = self.load()
        self.seen = self.cfg.get("history", {})
        if isinstance(self.seen, list):
            self.seen = {u: 1 for u in self.seen}

        self.listener = None
        self.run = False
        self.pause = False
        self.current_user = None
        self.processing_queue = queue.Queue()
        self.thread = None
        self.roulette_pool = []
        self.roulette_end_time = 0

        self.save_timer = None

        self.ui()

    def style(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure(".", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure(
            "TButton", background=PANEL, foreground=FG, borderwidth=0, padding=10
        )
        s.map(
            "TButton",
            background=[("active", ACCENT), ("disabled", "#2a2a2a")],
            foreground=[("disabled", "#555")],
        )
        s.configure(
            "TEntry", fieldbackground=PANEL, foreground=FG, borderwidth=0, padding=5
        )
        s.configure("TCheckbutton", background=BG, foreground=FG, padding=5)
        s.map("TCheckbutton", background=[("active", BG)])
        s.configure(
            "TCombobox",
            fieldbackground=PANEL,
            background=PANEL,
            foreground=FG,
            arrowcolor=FG,
            borderwidth=0,
        )
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", PANEL)],
            selectbackground=[("readonly", PANEL)],
            selectforeground=[("readonly", FG)],
        )
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=PANEL,
            foreground=FG,
            padding=[15, 8],
            borderwidth=0,
        )
        s.map("TNotebook.Tab", background=[("selected", ACCENT)])
        s.configure("TLabelframe", background=BG, foreground=ACCENT, bordercolor=PANEL)
        s.configure("TLabelframe.Label", background=BG, foreground=ACCENT)

    def load(self):
        if os.path.exists(CONFIG):
            try:
                loaded = json.load(open(CONFIG))
                return {**DEFAULT, **loaded}
            except:
                pass
        return DEFAULT.copy()

    def trigger_update(self, *args):
        if self.save_timer:
            self.r.after_cancel(self.save_timer)
        self.s.config(text="STATUS: Pending changes...", foreground=WARN)
        self.save_timer = self.r.after(1000, self.commit_save)

    def commit_save(self):
        was_running = self.run

        self.cfg["platform"] = self.plat_var.get()
        self.cfg["target_id"] = self.tgt_var.get()
        self.cfg["cmd_prefix"] = self.pre_var.get()
        self.cfg["limit"] = self.get_int(self.lim_var.get(), 0)

        self.cfg["auto_copy"] = self.ac_var.get()
        self.cfg["auto_restart"] = self.ar_var.get()
        self.cfg["mode_roulette"] = self.roulette_var.get()
        self.cfg["roulette_duration"] = self.get_int(self.rd_var.get(), 30)
        self.cfg["mode_latest"] = self.latest_var.get()

        self.cfg["history"] = self.seen

        try:
            json.dump(self.cfg, open(CONFIG, "w"), indent=4)
            self.status("Auto-Saved", SUCCESS)

            if was_running:
                self.status("Auto-Restarting Config...", WARN)
                self.stop()
                self.r.after(500, self.start)

        except Exception as e:
            self.status(f"Save Failed: {e}", ERROR)

    def get_int(self, val, default):
        try:
            return int(val)
        except:
            return default

    def ui(self):
        main = tk.Frame(self.r, bg=BG)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        self.s = ttk.Label(
            main, text=f"Ready", anchor="w", font=("Segoe UI", 9), foreground="#888"
        )
        self.s.pack(side="bottom", fill="x", pady=(10, 0))

        tabs = ttk.Notebook(main)
        chat_tab = ttk.Frame(tabs)
        cfg_tab = ttk.Frame(tabs)
        mode_tab = ttk.Frame(tabs)
        bl_tab = ttk.Frame(tabs)
        hist_tab = ttk.Frame(tabs)

        tabs.add(chat_tab, text="Live Feed")
        tabs.add(cfg_tab, text="Settings")
        tabs.add(mode_tab, text="Modes")
        tabs.add(bl_tab, text="Blacklist")
        tabs.add(hist_tab, text="History")
        tabs.pack(side="top", fill="both", expand=True)

        bar = ttk.Frame(chat_tab)
        bar.pack(side="bottom", fill="x", pady=(10, 0))

        self.start_btn = ttk.Button(bar, text="▶ Start", command=self.start)
        self.stop_btn = ttk.Button(bar, text="■ Stop", command=self.stop)
        self.next_btn = ttk.Button(bar, text="↠ Next", command=self.on_next)
        self.copy_btn = ttk.Button(bar, text="❐ Copy User", command=self.copy)

        for b in (self.start_btn, self.stop_btn, self.next_btn, self.copy_btn):
            b.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.stop_btn.state(["disabled"])

        self.log_box = tk.Text(
            chat_tab,
            bg=PANEL,
            fg=FG,
            font=("Segoe UI", 10),
            borderwidth=0,
            state="disabled",
        )
        self.log_box.pack(side="top", fill="both", expand=True, padx=1, pady=1)

        self.log_box.tag_config("success", foreground=SUCCESS)
        self.log_box.tag_config("error", foreground=ERROR)
        self.log_box.tag_config("warn", foreground=WARN)
        self.log_box.tag_config("normal", foreground=FG)
        self.log_box.tag_config("info", foreground="#5DADE2")

        cbox = tk.Frame(cfg_tab, bg=BG)
        cbox.pack(fill="both", expand=True, padx=20, pady=20)

        self.plat_var = tk.StringVar(value=self.cfg.get("platform", "YouTube"))
        self.tgt_var = tk.StringVar(value=self.cfg.get("target_id", ""))
        self.pre_var = tk.StringVar(value=self.cfg.get("cmd_prefix", ""))
        self.lim_var = tk.StringVar(value=str(self.cfg.get("limit", 2)))

        inputs = [
            ("Platform:", ["YouTube", "Twitch"], self.plat_var),
            ("Channel/ID:", None, self.tgt_var),
            ("Prefix:", None, self.pre_var),
            ("Limit per User (0 = infinity):", None, self.lim_var),
        ]

        for label, opts, var in inputs:
            var.trace_add("write", self.trigger_update)

            ttk.Label(cbox, text=label, background=BG, foreground="#888").pack(
                anchor="w", pady=(0, 5)
            )
            if opts:
                w = ttk.Combobox(cbox, textvariable=var, values=opts, state="readonly")
                w.bind("<<ComboboxSelected>>", self.trigger_update)
            else:
                w = ttk.Entry(cbox, textvariable=var)
            w.pack(fill="x", pady=(0, 10))

        mbox = tk.Frame(mode_tab, bg=BG)
        mbox.pack(fill="both", expand=True, padx=20, pady=20)

        self.ac_var = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.ar_var = tk.BooleanVar(value=self.cfg.get("auto_restart", True))
        self.latest_var = tk.BooleanVar(value=self.cfg.get("mode_latest", False))
        self.roulette_var = tk.BooleanVar(value=self.cfg.get("mode_roulette", False))
        self.rd_var = tk.StringVar(value=str(self.cfg.get("roulette_duration", 30)))

        for v in [
            self.ac_var,
            self.ar_var,
            self.latest_var,
            self.roulette_var,
            self.rd_var,
        ]:
            v.trace_add("write", self.trigger_update)

        ttk.Label(mbox, text="Automation", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )
        ttk.Checkbutton(mbox, text="Auto-Copy Username", variable=self.ac_var).pack(
            anchor="w", pady=5
        )
        ttk.Checkbutton(
            mbox, text="Auto-Restart on Config Change", variable=self.ar_var
        ).pack(anchor="w", pady=5)

        ttk.Separator(mbox, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(mbox, text="Behavior", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )
        ttk.Checkbutton(
            mbox, text="Process LATEST message only", variable=self.latest_var
        ).pack(anchor="w", pady=5)

        r_frame = tk.Frame(mbox, bg=BG)
        r_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(r_frame, text="Roulette Mode", variable=self.roulette_var).pack(
            side="left"
        )
        ttk.Label(r_frame, text="Duration (s):").pack(side="left", padx=(10, 5))
        ttk.Entry(r_frame, width=5, textvariable=self.rd_var).pack(side="left")

        bbox = tk.Frame(bl_tab, bg=BG)
        bbox.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(bbox, text="Edit List:", foreground="#888").pack(
            anchor="w", pady=(0, 5)
        )
        self.bl_selector = ttk.Combobox(
            bbox,
            values=["Blocked Message Content", "Blocked Message Authors"],
            state="readonly",
        )
        self.bl_selector.current(0)
        self.bl_selector.pack(fill="x", pady=(0, 15))

        self.bl_selector.bind(
            "<<ComboboxSelected>>", lambda e: self.refresh_blacklist_ui()
        )

        bl_top = tk.Frame(bbox, bg=BG)
        bl_top.pack(fill="x", pady=(0, 5))
        self.bl_entry = ttk.Entry(bl_top)
        self.bl_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(bl_top, text="+ Add", width=8, command=self.add_blacklist).pack(
            side="right"
        )

        self.bl_list = tk.Listbox(
            bbox, bg=PANEL, fg=FG, borderwidth=0, highlightthickness=0
        )
        self.bl_list.pack(fill="both", expand=True, pady=10)

        ttk.Button(bbox, text="- Remove Selected", command=self.remove_blacklist).pack(
            fill="x", pady=(0, 10)
        )

        self.refresh_blacklist_ui()

        h_box = tk.Frame(hist_tab, bg=BG)
        h_box.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(
            h_box, text="Tracked Users History", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))
        self.h_list = tk.Listbox(
            h_box, bg=PANEL, fg=FG, borderwidth=0, highlightthickness=0
        )
        self.h_list.pack(fill="both", expand=True, pady=(0, 10))
        self.h_list.bind("<<ListboxSelect>>", self.on_history_select)

        ttk.Button(h_box, text="↻ Refresh List", command=self.refresh_history_ui).pack(
            fill="x", pady=(0, 10)
        )

        r_frame = tk.Frame(h_box, bg=BG)
        r_frame.pack(fill="x", pady=5)
        self.reset_entry = ttk.Entry(r_frame)
        self.reset_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            r_frame, text="Reset User", width=15, command=self.reset_specific
        ).pack(side="right")

        ttk.Button(h_box, text="⚠ Reset All History", command=self.reset_all).pack(
            fill="x", pady=5
        )
        self.refresh_history_ui()

    def refresh_blacklist_ui(self):
        self.bl_list.delete(0, "end")
        mode = self.bl_selector.get()
        if mode == "Blocked Message Authors":
            target_list = self.cfg.get("blacklist_authors", [])
        else:
            target_list = self.cfg.get("blacklist", [])

        if not isinstance(target_list, list):
            target_list = []

        for item in target_list:
            self.bl_list.insert("end", item)

    def refresh_history_ui(self):
        self.h_list.delete(0, "end")
        for user, count in self.seen.items():
            self.h_list.insert("end", f"{user} : {count}")

    def on_history_select(self, event):
        selection = event.widget.curselection()
        if selection:
            data = event.widget.get(selection[0])
            user = data.split(" : ")[0]
            self.reset_entry.delete(0, "end")
            self.reset_entry.insert(0, user)

    def add_blacklist(self):
        name = self.bl_entry.get().strip().lower()
        if name:
            mode = self.bl_selector.get()
            key = (
                "blacklist_authors"
                if mode == "Blocked Message Authors"
                else "blacklist"
            )

            current_list = self.cfg.get(key, [])
            if not isinstance(current_list, list):
                current_list = []

            if name not in current_list:
                current_list.append(name)
                self.cfg[key] = current_list
                self.bl_entry.delete(0, "end")
                self.refresh_blacklist_ui()
                self.trigger_update()

    def remove_blacklist(self):
        sel = self.bl_list.curselection()
        if sel:
            name = self.bl_list.get(sel[0])
            mode = self.bl_selector.get()
            key = (
                "blacklist_authors"
                if mode == "Blocked Message Authors"
                else "blacklist"
            )

            current_list = self.cfg.get(key, [])
            if not isinstance(current_list, list):
                current_list = []

            if name in current_list:
                current_list.remove(name)
                self.cfg[key] = current_list
                self.refresh_blacklist_ui()
                self.trigger_update()
            else:
                self.refresh_blacklist_ui()

    def status(self, t, color=FG):
        self.s.config(text=f"STATUS: {str(t)}", foreground=color)

    def on_next(self):
        if not self.run:
            self.status("Bot is stopped. Press Start.", WARN)
            return
        self.pause = False
        self.current_user = None

        if self.cfg.get("mode_roulette"):
            self.status(
                f"Roulette Started ({self.cfg.get('roulette_duration')}s)...", "#5DADE2"
            )
            self.roulette_pool = []
            self.roulette_end_time = time.time() + self.cfg.get("roulette_duration", 30)
        else:
            self.status("Scanning...", ACCENT)

    def reset_all(self):
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.seen.clear()
            self.refresh_history_ui()
            self.trigger_update()

    def reset_specific(self):
        u = self.reset_entry.get().strip()
        if not u:
            return
        if u in self.seen:
            del self.seen[u]
            self.refresh_history_ui()
            self.reset_entry.delete(0, "end")
            self.trigger_update()

    def start(self):
        if self.run:
            return
        self.current_user = None
        with self.processing_queue.mutex:
            self.processing_queue.queue.clear()

        try:
            target = self.cfg["target_id"]
            plat = self.cfg.get("platform", "YouTube")
            if plat == "YouTube":
                self.listener = pytchat.create(video_id=target)
            else:
                self.listener = TwitchClient(target)
                if not self.listener.connect():
                    raise Exception("Twitch Connection Failed")

            self.run = True
            self.pause = False
            self.start_btn.state(["disabled"])
            self.stop_btn.state(["!disabled"])

            if self.cfg.get("mode_roulette"):
                self.roulette_end_time = time.time() + self.cfg.get(
                    "roulette_duration", 30
                )
                self.roulette_pool = []
                self.status(
                    f"Roulette Started ({self.cfg.get('roulette_duration')}s)...",
                    "#5DADE2",
                )
            else:
                self.status(f"Listening on {plat}...", ACCENT)

            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.stop()

    def stop(self):
        self.run = False
        self.pause = False
        if hasattr(self, "listener") and self.listener:
            try:
                self.listener.close()
            except:
                pass
            try:
                self.listener.terminate()
            except:
                pass
        self.listener = None
        self.start_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        self.status("Stopped", ERROR)

    def copy(self):
        if self.current_user:
            self.r.clipboard_clear()
            self.r.clipboard_append(self.current_user)
            self.status(f"Copied: {self.current_user}", SUCCESS)
        else:
            self.status("No user found yet", WARN)

    def finalize_user(self, user):
        current_count = self.seen.get(user, 0) + 1
        self.seen[user] = current_count
        self.current_user = user
        self.pause = True

        self.cfg["history"] = self.seen
        json.dump(self.cfg, open(CONFIG, "w"), indent=4)

        self.r.after(0, self.refresh_history_ui)

        lim_str = "∞" if self.cfg["limit"] == 0 else self.cfg["limit"]
        self.r.after(
            0,
            lambda u=user, c=current_count: self.add_line(
                f"✔: {u} (Count: {c}/{lim_str})", "success"
            ),
        )
        self.r.after(
            0, lambda u=user: self.status(f"Selected: {u} - Press Next", SUCCESS)
        )

        if self.ac_var.get():
            self.r.after(0, self.copy)

    def loop(self):
        while self.run:
            while self.pause and self.run:
                time.sleep(0.1)
            if not self.run:
                break

            try:
                raw_msgs = []
                if isinstance(self.listener, TwitchClient):
                    raw_msgs = self.listener.get_messages()
                else:
                    if self.listener.is_alive():
                        data = self.listener.get()
                        if data:
                            raw_msgs = [
                                (i.author.name, str(i.message)) for i in data.items
                            ]
                    else:
                        raise Exception("Connection Lost")

                if self.cfg.get("mode_latest") and raw_msgs:
                    raw_msgs = [raw_msgs[-1]]

                p = self.cfg["cmd_prefix"]
                user_limit = int(self.cfg.get("limit", 1))
                blacklist_content = [x.lower() for x in self.cfg.get("blacklist", [])]
                blacklist_authors = [
                    x.lower() for x in self.cfg.get("blacklist_authors", [])
                ]
                is_roulette = self.cfg.get("mode_roulette", False)

                for sender_name, msg in raw_msgs:
                    if sender_name.lower() in blacklist_authors:
                        continue

                    clean_msg = re.sub(r":[a-zA-Z0-9_-]+:", "", msg).strip()
                    if not clean_msg:
                        continue

                    self.r.after(
                        0,
                        lambda u=sender_name, t=clean_msg: self.add_line(
                            f"{u}: {t}", "normal"
                        ),
                    )

                    m = clean_msg.replace(" ", "").lower()
                    if m.startswith(p):
                        u = m[len(p) :]
                        times_seen = self.seen.get(u, 0)

                        if u and (user_limit == 0 or times_seen < user_limit):
                            if u.lower() in blacklist_content:
                                self.r.after(
                                    0,
                                    lambda u=u: self.status(
                                        f"Skipped Blacklisted Content: {u}", WARN
                                    ),
                                )
                                continue

                            self.processing_queue.put(u)

                while not self.processing_queue.empty() and not self.pause and self.run:
                    candidate = self.processing_queue.get()

                    if user_limit != 0 and self.seen.get(candidate, 0) >= user_limit:
                        continue

                    is_valid = self.check_user(candidate)

                    if is_valid:
                        if is_roulette:
                            if candidate not in self.roulette_pool:
                                self.roulette_pool.append(candidate)
                                self.r.after(
                                    0,
                                    lambda u=candidate: self.add_line(
                                        f"• Added to roulette: {u}", "info"
                                    ),
                                )
                        else:
                            self.finalize_user(candidate)
                            break
                    else:
                        self.r.after(
                            0, lambda u=candidate: self.status(f"Invalid: {u}", ERROR)
                        )

                if is_roulette and not self.pause and self.run:
                    remaining = int(self.roulette_end_time - time.time())
                    if remaining <= 0:
                        if self.roulette_pool:
                            winner = random.choice(self.roulette_pool)
                            self.finalize_user(winner)
                        else:
                            self.status("Roulette ended. No users found.", WARN)
                            self.pause = True
                    else:
                        if remaining % 5 == 0:
                            self.r.after(
                                0,
                                lambda r=remaining: self.status(
                                    f"Collecting... {r}s left (Roulette Pool: {len(self.roulette_pool)})",
                                    "#5DADE2",
                                ),
                            )

            except Exception:
                pass
            time.sleep(0.1)

    def check_user(self, u):
        try:
            data = json.dumps({"usernames": [u], "excludeBannedUsers": True}).encode()
            req = urllib.request.Request(
                "https://users.roproxy.com/v1/usernames/users",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                resp = json.loads(r.read())
                return bool(resp.get("data") and len(resp["data"]) > 0)
        except:
            return False

    def add_line(self, text, tag):
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    img = tk.PhotoImage(width=1, height=1)
    img.put(ACCENT, (0, 0))
    root.iconphoto(False, img)
    App(root)
    root.mainloop()
