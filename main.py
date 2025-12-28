"""
╔════════════════════════════════════════════════════════════╗
║  Author  : pygot                                           ║
║  GitHub  : https://github.com/pygot                        ║
╚════════════════════════════════════════════════════════════╝
"""

from tkinter import ttk, messagebox

import threading, json, os, time, urllib.request, re, socket, queue
import tkinter as tk
import pytchat

CONFIG = "config.json"
DEFAULT = {
    "platform": "YouTube",
    "target_id": "dQw4w9WgXcQ",
    "cmd_prefix": "",
    "limit": 2,
    "auto_copy": False,
    "history": {},
    "blacklist": ["roblox", "builderman", "robux"],
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

        r.geometry("520x680")
        r.minsize(520, 680)

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
            padding=[20, 8],
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

    def save(self):
        self.cfg["platform"] = self.plat_var.get()
        self.cfg["target_id"] = self.tgt.get()
        self.cfg["cmd_prefix"] = self.pre.get()
        self.cfg["auto_copy"] = self.ac_var.get()
        try:
            self.cfg["limit"] = int(self.lim.get())
        except:
            self.cfg["limit"] = 1

        self.cfg["history"] = self.seen

        if "blacklist" not in self.cfg:
            self.cfg["blacklist"] = []

        try:
            json.dump(self.cfg, open(CONFIG, "w"), indent=4)
            self.status("Configuration Saved", SUCCESS)
        except Exception as e:
            self.status(f"Save Failed: {e}", ERROR)

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
        tabs.add(chat_tab, text="Live Feed")
        tabs.add(cfg_tab, text="Settings")
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

        cbox = tk.Frame(cfg_tab, bg=BG)
        cbox.pack(fill="both", expand=True, padx=20, pady=20)

        inputs = [
            ("Platform:", ["YouTube", "Twitch"], "platform"),
            ("Channel/ID:", None, "target_id"),
            ("Prefix:", None, "cmd_prefix"),
            ("Limit per User (0 = infinity):", None, "limit"),
        ]

        for label, opts, key in inputs:
            ttk.Label(cbox, text=label, background=BG, foreground="#888").pack(
                anchor="w", pady=(0, 5)
            )
            if opts:
                v = tk.StringVar(value=self.cfg.get(key))
                self.plat_var = v
                w = ttk.Combobox(cbox, textvariable=v, values=opts, state="readonly")
            else:
                w = ttk.Entry(cbox)
                w.insert(0, self.cfg.get(key))
                if key == "target_id":
                    self.tgt = w
                if key == "cmd_prefix":
                    self.pre = w
                if key == "limit":
                    self.lim = w
            w.pack(fill="x", pady=(0, 10))

        self.ac_var = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        ttk.Checkbutton(cbox, text="Auto-Copy Username", variable=self.ac_var).pack(
            anchor="w", pady=(0, 10)
        )

        ttk.Button(cbox, text="Save Configuration", command=self.save).pack(
            fill="x", pady=(0, 10)
        )

        bl_frame = ttk.LabelFrame(cbox, text=" Blacklist Manager ", padding=10)
        bl_frame.pack(fill="both", expand=True, pady=10)

        bl_top = tk.Frame(bl_frame, bg=BG)
        bl_top.pack(fill="x", pady=(0, 5))

        self.bl_entry = ttk.Entry(bl_top)
        self.bl_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(bl_top, text="+ Add", width=8, command=self.add_blacklist).pack(
            side="right"
        )

        self.bl_list = tk.Listbox(
            bl_frame, bg=PANEL, fg=FG, borderwidth=0, highlightthickness=0, height=4
        )
        self.bl_list.pack(fill="both", expand=True, pady=5)

        ttk.Button(
            bl_frame, text="- Remove Selected", command=self.remove_blacklist
        ).pack(fill="x")

        self.refresh_blacklist_ui()

        ttk.Separator(cbox, orient="horizontal").pack(fill="x", pady=10)

        r_frame = tk.Frame(cbox, bg=BG)
        r_frame.pack(fill="x", pady=5)
        self.reset_entry = ttk.Entry(r_frame)
        self.reset_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            r_frame, text="Reset User", width=15, command=self.reset_specific
        ).pack(side="right")

        ttk.Button(cbox, text="⚠ Reset All History", command=self.reset_all).pack(
            fill="x", pady=5
        )

    def refresh_blacklist_ui(self):
        self.bl_list.delete(0, "end")
        for user in self.cfg.get("blacklist", []):
            self.bl_list.insert("end", user)

    def add_blacklist(self):
        name = self.bl_entry.get().strip().lower()
        if name:
            current_list = self.cfg.get("blacklist", [])
            if name not in current_list:
                current_list.append(name)
                self.cfg["blacklist"] = current_list
                self.save()
                self.refresh_blacklist_ui()
                self.bl_entry.delete(0, "end")
                self.status(f"Added '{name}' to blacklist", SUCCESS)
            else:
                self.status("User already in blacklist", WARN)

    def remove_blacklist(self):
        sel = self.bl_list.curselection()
        if sel:
            name = self.bl_list.get(sel[0])
            current_list = self.cfg.get("blacklist", [])
            if name in current_list:
                current_list.remove(name)
                self.cfg["blacklist"] = current_list
                self.save()
                self.refresh_blacklist_ui()
                self.status(f"Removed '{name}'", WARN)

    def status(self, t, color=FG):
        self.s.config(text=f"STATUS: {str(t)}", foreground=color)

    def on_next(self):
        if not self.run:
            self.status("Bot is stopped. Press Start.", WARN)
            return
        self.pause = False
        self.current_user = None
        self.status("Scanning...", ACCENT)

    def reset_all(self):
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.seen.clear()
            self.save()
            self.status("History Cleared", WARN)

    def reset_specific(self):
        u = self.reset_entry.get().strip()
        if not u:
            return
        if u in self.seen:
            del self.seen[u]
            self.save()
            self.reset_entry.delete(0, "end")
            self.status(f"Reset count for '{u}'", SUCCESS)
        else:
            self.status(f"User '{u}' not in history", ERROR)

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

            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            self.status(f"Listening on {plat}...", ACCENT)
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
                            raw_msgs = [(i.author.name, str(i.message)) for i in data.items]
                    else:
                        raise Exception("Connection Lost")

                p = self.cfg["cmd_prefix"]
                user_limit = int(self.lim.get())

                blacklist = [x.lower() for x in self.cfg.get("blacklist", [])]

                for user, msg in raw_msgs:
                    clean_msg = re.sub(r":[a-zA-Z0-9_-]+:", "", msg).strip()
                    if not clean_msg:
                        continue
                    self.r.after(
                        0,
                        lambda u=user, t=clean_msg: self.add_line(f"{u}: {t}", "normal")
                    )

                    m = clean_msg.replace(" ", "").lower()
                    if m.startswith(p):
                        u = m[len(p) :]
                        times_seen = self.seen.get(u, 0)
                        if u and (user_limit == 0 or times_seen < user_limit):
                            self.processing_queue.put(u)

                while not self.processing_queue.empty() and not self.pause and self.run:
                    candidate = self.processing_queue.get()

                    if candidate.lower() in blacklist:
                        self.r.after(
                            0,
                            lambda u=candidate: self.status(
                                f"Skipped Blacklisted: {u}", WARN
                            ),
                        )
                        continue

                    if user_limit != 0 and self.seen.get(candidate, 0) >= user_limit:
                        continue

                    is_valid = self.check_user(candidate)
                    if is_valid:
                        current_count = self.seen.get(candidate, 0) + 1
                        self.seen[candidate] = current_count

                        self.current_user = candidate
                        self.pause = True

                        self.r.after(0, self.save)

                        lim_str = "∞" if user_limit == 0 else user_limit
                        self.r.after(
                            0,
                            lambda u=candidate, c=current_count: self.add_line(
                                f"✓ FOUND: {u} (Count: {c}/{lim_str})", "success"
                            ),
                        )
                        self.r.after(
                            0,
                            lambda u=candidate: self.status(
                                f"Found: {u} - Press Next", SUCCESS
                            ),
                        )

                        if self.ac_var.get():
                            self.r.after(0, self.copy)

                        break
                    else:
                        self.r.after(
                            0, lambda u=candidate: self.status(f"Invalid: {u}", ERROR)
                        )
            except:
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
