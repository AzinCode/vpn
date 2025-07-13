import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import urllib.parse
import base64
import re
import threading
import queue

# --- Constants ---
V2RAY_PROTOCOLS = ['vless://', 'vmess://', 'ss://', 'trojan://']
TELEGRAM_PROTOCOLS = ['https://t.me/proxy?', 'tg://proxy?']

# --- Color Palette ---
COLORS = {
    "background": "#f0f2f5",
    "frame": "#ffffff",
    "text": "#050505",
    "danger": "#d32f2f",
    "primary": "#0078d7",
    "primary_hover": "#005a9e",
    "secondary": "#5c5c5c",
    "header": "#1d2c4d",
    "odd_row": "#f0f8ff",
    "even_row": "#ffffff"
}

class VpnConfigEditorApp(tk.Tk):
    """
    نسخه بهینه‌سازی شده و پیشرفته ویرایشگر کانفیگ VPN.
    این نسخه شامل پردازشگرهای مقاوم، گزارش خطا و پردازش چندنخی است.
    """
    def __init__(self):
        super().__init__()
        self.title("ویرایشگر پیشرفته VPN و پراکسی (نسخه نهایی اصلاح‌شده)")
        self.geometry("1400x850")
        self.configure(bg=COLORS["background"])

        self.processing_queue = queue.Queue()
        self.tree_data_map = {} # {tree_iid: data_dict}

        self._configure_styles()
        self._create_widgets()

    def _configure_styles(self):
        """پیکربندی استایل‌های ttk برای ظاهر برنامه."""
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure(".", font=("Vazirmatn", 10), background=COLORS["background"], foreground=COLORS["text"])
        self.style.configure("TLabel", background=COLORS["background"])
        self.style.configure("TButton", font=("Vazirmatn", 10, "bold"), padding=9, relief="flat", background=COLORS["primary"], foreground="white")
        self.style.map("TButton", background=[('active', COLORS["primary_hover"]), ('!disabled', COLORS["primary"])])
        self.style.configure("Secondary.TButton", background=COLORS["secondary"])
        self.style.map("Secondary.TButton", background=[('active', '#757575')])
        self.style.configure("TLabelframe", background=COLORS["frame"], borderwidth=1, relief="groove")
        self.style.configure("TLabelframe.Label", background=COLORS["frame"], foreground=COLORS["secondary"])
        self.style.configure("Treeview.Heading", font=("Vazirmatn", 11, "bold"), background=COLORS["header"], foreground="white", relief="flat")
        self.style.map("Treeview.Heading", relief=[('active', 'groove')])
        self.style.configure("Treeview", rowheight=28, font=("Vazirmatn", 10), background=COLORS["frame"])
        self.style.configure("Link.TButton", font=("Vazirmatn", 8), padding=3)

        self.style.map("Treeview", background=[('selected', COLORS["primary"])])
        self.style.configure("oddrow", background=COLORS["odd_row"])
        self.style.configure("evenrow", background=COLORS["even_row"])

    def _create_widgets(self):
        """ایجاد و چیدمان تمام ویجت‌ها در پنجره اصلی."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(main_frame, width=420)
        left_pane.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        left_pane.pack_propagate(False)

        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_input_panel(left_pane)
        self._create_action_panel(left_pane)
        self._create_status_bar(left_pane)
        self._create_output_panel(right_pane)

    def _create_input_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="ورودی و تنظیمات", padding=15)
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="🔗 نام جدید کانفیگ:").pack(fill=tk.X, pady=(0, 5), anchor='e')
        self.custom_tag_entry = ttk.Entry(frame, justify='right', font=("Vazirmatn", 10))
        self.custom_tag_entry.insert(0, "@vOXsafe")
        self.custom_tag_entry.pack(fill=tk.X, pady=(0, 15))

        input_label_frame = ttk.Frame(frame)
        input_label_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(input_label_frame, text="📥 لینک‌های ورودی:").pack(side=tk.RIGHT)
        ttk.Button(input_label_frame, text="📋 جای‌گذاری", command=self.paste_from_clipboard, style="Link.TButton").pack(side=tk.LEFT)

        self.input_text = scrolledtext.ScrolledText(frame, height=15, wrap=tk.WORD, font=("Consolas", 10), relief="solid", borderwidth=1)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.remove_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="حذف لینک‌های تکراری", variable=self.remove_duplicates_var).pack(pady=(0, 10), anchor='e')

    def _create_action_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="عملیات و فایل‌ها", padding=15)
        frame.pack(fill=tk.X)

        self.process_button = ttk.Button(frame, text="⚙️ پردازش و جداسازی", command=self.start_processing)
        self.process_button.pack(fill=tk.X, pady=5)

        self.load_button = ttk.Button(frame, text="📂 انتخاب فایل(ها)", command=self.load_from_file, style="Secondary.TButton")
        self.load_button.pack(fill=tk.X, pady=5)

        # --- Added Files Section ---
        added_files_frame = ttk.Frame(frame, padding=(0, 10))
        added_files_frame.pack(fill=tk.X, expand=True)

        added_files_buttons_frame = ttk.Frame(added_files_frame)
        added_files_buttons_frame.pack(fill=tk.X, pady=(0, 5))

        self.remove_selected_file_button = ttk.Button(added_files_buttons_frame, text="حذف انتخاب شده", command=self.remove_selected_file, style="Link.TButton")
        self.remove_selected_file_button.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_added_files_button = ttk.Button(added_files_buttons_frame, text="پاک کردن لیست", command=self.clear_added_files, style="Link.TButton")
        self.clear_added_files_button.pack(side=tk.LEFT)

        self.added_files_tree = self._create_treeview_tab(added_files_frame, "", {"نام فایل": 300}, is_notebook_tab=False)
        self.added_files_tree.pack(fill=tk.BOTH, expand=True)

        self.clear_button = ttk.Button(frame, text="🗑️ پاک‌سازی همه", command=self.clear_all, style="Secondary.TButton")
        self.clear_button.pack(fill=tk.X, pady=10, side=tk.BOTTOM)

    def _create_status_bar(self, parent):
        status_frame = ttk.Frame(parent, padding=(10, 5), relief="groove", borderwidth=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(status_frame, text="آماده", anchor='w')
        self.status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        # Initially hidden

    def _create_output_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        v2ray_cols = {"پروتکل": 80, "آدرس": 200, "پورت": 60, "نام": 150, "جزئیات": 220}
        telegram_cols = {"سرور": 220, "پورت": 80, "سیکرت": 350}
        names_cols = {"نام اصلی کانفیگ": 500}
        failed_cols = {"لینک ناموفق": 400, "دلیل خطا": 350}

        self.v2ray_tree = self._create_treeview_tab(notebook, "کانفیگ‌های V2Ray/SS/Trojan", v2ray_cols)
        self.telegram_tree = self._create_treeview_tab(notebook, "پراکسی تلگرام", telegram_cols)
        self.original_names_tree = self._create_treeview_tab(notebook, "نام‌های اصلی کانفیگ", names_cols)
        self.failed_links_tree = self._create_treeview_tab(notebook, "لینک‌های ناموفق", failed_cols)

    def _create_treeview_tab(self, parent, title, columns, is_notebook_tab=True):
        if is_notebook_tab:
            frame = ttk.Frame(parent, padding=10)
            parent.add(frame, text=f" {title} ")
        else:
            frame = parent

        if is_notebook_tab:
            top_bar = ttk.Frame(frame)
            top_bar.pack(fill=tk.X, pady=(0, 10))

        tree = ttk.Treeview(frame, columns=list(columns.keys()), show='headings')

        for col, width in columns.items():
            tree.heading(col, text=col, anchor='center', command=lambda c=col, t=tree: self.sort_treeview_column(t, c, False))
            tree.column(col, anchor='w', width=width, minwidth=width)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side='left', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        hsb.pack(side='bottom', fill='x')

        if is_notebook_tab:
            ttk.Button(top_bar, text="📄 کپی همه", command=lambda t=tree: self.copy_all(t), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(top_bar, text="💾 دانلود همه", command=lambda t=tree: self.save_to_file(t), style="Secondary.TButton").pack(side=tk.LEFT)

        popup_menu = tk.Menu(self, tearoff=0)
        popup_menu.add_command(label="📄 کپی لینک انتخاب شده", command=lambda t=tree: self.copy_selected(t))
        tree.bind("<Button-3>", lambda event, t=tree, m=popup_menu: self.show_popup(event, t, m))

        tree.sort_column = None
        tree.sort_direction = False
        return tree

    # --- UI Interaction Methods ---

    def show_popup(self, event, tree, menu):
        if iid := tree.identify_row(event.y):
            tree.selection_set(iid)
            menu.post(event.x_root, event.y_root)

    def paste_from_clipboard(self):
        try:
            self.input_text.insert(tk.END, self.clipboard_get())
            self.update_status("محتوا از کلیپ‌بورد جای‌گذاری شد.")
        except tk.TclError:
            self.update_status("خطا: کلیپ‌بورد خالی است.", error=True)

    def sort_treeview_column(self, tree, col, reverse):
        if tree.sort_column == col: reverse = not tree.sort_direction

        data_list = [(tree.set(k, col), k) for k in tree.get_children('')]

        try: data_list.sort(key=lambda t: float(t[0]), reverse=reverse)
        except (ValueError, TypeError): data_list.sort(key=lambda t: str(t[0]), reverse=reverse)

        for index, (val, k) in enumerate(data_list): tree.move(k, '', index)

        tree.heading(col, command=lambda c=col, t=tree: self.sort_treeview_column(t, c, not reverse))
        tree.sort_column = col
        tree.sort_direction = reverse

        for i, k in enumerate(tree.get_children('')):
            tree.item(k, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def update_status(self, message, error=False):
        self.status_label.config(text=message, foreground=COLORS["danger"] if error else COLORS["text"])

    # --- Core Logic & Threading ---

    def start_processing(self):
        new_name = self.custom_tag_entry.get()
        if not new_name:
            messagebox.showwarning("ورودی ناقص", "لطفاً یک نام جدید برای کانفیگ‌ها وارد کنید.")
            return

        lines = [line.strip() for line in self.input_text.get("1.0", tk.END).splitlines() if line.strip()]
        if self.remove_duplicates_var.get(): lines = list(dict.fromkeys(lines))

        if not lines:
            self.update_status("هیچ لینکی برای پردازش وجود ندارد.", error=True)
            return

        self.clear_results()
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_bar['maximum'] = len(lines)
        self.process_button.config(state=tk.DISABLED)
        self.load_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.update_status(f"در حال آماده‌سازی برای پردازش {len(lines)} لینک...")

        thread = threading.Thread(target=self._run_processing_logic, args=(lines, new_name), daemon=True)
        thread.start()
        self.after(100, self._check_queue)

    def _run_processing_logic(self, lines, new_name):
        """این متد در یک ترد جداگانه اجرا می‌شود تا از فریز شدن UI جلوگیری کند."""
        for i, line in enumerate(lines):
            try:
                if parsed := self._parse_link(line, new_name):
                    self.processing_queue.put(parsed)
                else:
                    raise ValueError("پروتکل لینک شناسایی نشد.")
            except Exception as e:
                self.processing_queue.put({'type': 'failed', 'link': line, 'error': str(e)})

            self.processing_queue.put({'type': 'progress', 'value': i + 1})

        self.processing_queue.put({'type': 'finished'})

    def _check_queue(self):
        """به صورت دوره‌ای صف را برای دریافت آپدیت از ترد پردازش چک می‌کند."""
        try:
            while not self.processing_queue.empty():
                msg = self.processing_queue.get_nowait()

                if msg['type'] == 'progress':
                    self.progress_bar['value'] = msg['value']
                    self.update_status(f"در حال پردازش... ({msg['value']}/{self.progress_bar['maximum']})")

                elif msg['type'] == 'finished':
                    self.progress_bar.pack_forget()
                    self.process_button.config(state=tk.NORMAL)
                    self.load_button.config(state=tk.NORMAL)
                    self.clear_button.config(state=tk.NORMAL)
                    total_success = len(self.v2ray_tree.get_children()) + len(self.telegram_tree.get_children())
                    total_failed = len(self.failed_links_tree.get_children())
                    self.update_status(f"پردازش کامل شد: {total_success} موفق، {total_failed} ناموفق.")
                    return

                elif msg['type'] == 'failed':
                    self._add_item_to_tree(self.failed_links_tree, msg, ('link', 'error'))

                elif msg['type'] in ['v2ray', 'trojan', 'vless', 'vmess', 'ss']:
                    self._add_item_to_tree(self.v2ray_tree, msg, ("protocol", "host", "port", "name", "details"))
                    if msg.get('original_name'):
                        self._add_item_to_tree(self.original_names_tree, {'name': msg['original_name']}, ('name',))

                elif msg['type'] == 'telegram':
                    self._add_item_to_tree(self.telegram_tree, msg, ("server", "port", "secret"))
                    if msg.get('original_name'):
                        self._add_item_to_tree(self.original_names_tree, {'name': msg['original_name']}, ('name',))

        except queue.Empty:
            pass
        finally:
            if self.process_button['state'] == tk.DISABLED:
                self.after(100, self._check_queue)

    # --- Parsing Logic ---
    def _parse_link(self, line, new_name):
        """[اصلاح شده] تشخیص پروتکل با اولویت تلگرام."""
        # ابتدا لینک‌های تلگرام بررسی می‌شوند چون از پروتکل استاندارد https استفاده می‌کنند
        if any(line.lower().startswith(p) for p in TELEGRAM_PROTOCOLS):
            return self._parse_telegram(line, new_name)

        # سپس سایر پروتکل‌های خاص بررسی می‌شوند
        protocol_match = re.match(r"(\w+)://", line)
        if not protocol_match:
            return None # فرمت لینک شناخته شده نیست

        protocol = protocol_match.group(1).lower()
        if f"{protocol}://" in V2RAY_PROTOCOLS:
            parser_func = getattr(self, f"_parse_{protocol}", None)
            if parser_func:
                return parser_func(line, new_name)

        return None

    def _parse_vmess(self, line, new_name):
        content = line.replace("vmess://", "", 1)
        try:
            vmess_data = json.loads(base64.b64decode(content + '=' * (-len(content) % 4)).decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("رشته VMess دارای فرمت Base64 یا JSON نامعتبر است.")

        data = {
            'type': 'vmess', 'protocol': 'VMESS', 'name': new_name,
            'host': vmess_data.get('add', 'N/A'), 'port': vmess_data.get('port', 'N/A'),
            'details': f"SNI:{vmess_data.get('sni', vmess_data.get('host', 'N/A'))} | Net:{vmess_data.get('net', 'N/A')}",
            'original_name': urllib.parse.unquote(vmess_data.get('ps', '(بدون نام)'))
        }
        vmess_data['ps'] = new_name
        new_b64 = base64.b64encode(json.dumps(vmess_data, separators=(',', ':')).encode('utf-8')).decode('utf-8').rstrip("=")
        data['modified_link'] = f"vmess://{new_b64}"
        return data

    def _parse_ss(self, line, new_name):
        """[اصلاح شده] پردازشگر مقاوم برای لینک‌های Shadowsocks."""
        data = {'type': 'ss', 'protocol': 'SS', 'name': new_name}

        # Standard format: ss://<user_info>@<host>:<port>#<tag>
        match = re.match(r"ss://(?P<user_info>[^@#?]+)@(?P<host>[^:@#?]+):(?P<port>\d+)(?:\?(?P<query>[^#]*))?(?:#(?P<tag>.*))?$", line)

        if match:
            parts = match.groupdict()
            user_info_raw = parts['user_info']
            tag = parts.get('tag')
            data['original_name'] = urllib.parse.unquote(tag) if tag else '(بدون نام)'

            try:
                # The user_info part is base64 encoded (and might be URL-encoded)
                user_info = urllib.parse.unquote(user_info_raw)
                decoded_part = base64.urlsafe_b64decode(user_info + '=' * (-len(user_info) % 4)).decode('utf-8')
                method, password = decoded_part.split(':', 1)
            except Exception:
                raise ValueError("بخش اطلاعات کاربری (Base64) لینک SS نامعتبر است.")

            data.update({'host': parts['host'], 'port': parts['port'], 'details': f"Method: {method}"})
            if parts.get('query'):
                data['details'] += f" | Plugin: {parts['query'][:30]}"

            base_link = line.split('#')[0]
            data['modified_link'] = f"{base_link}#{urllib.parse.quote(new_name)}"
            return data

        # Alternative format: ss://<base64_encoded_string>
        if not re.match(r"ss://.+@.+", line):
            try:
                content_part = line.replace("ss://", "", 1)

                # Split fragment identifier (#tag)
                fragment = ''
                if '#' in content_part:
                    content_part, fragment = content_part.rsplit('#', 1)
                    data['original_name'] = urllib.parse.unquote(fragment)
                else:
                    data['original_name'] = '(بدون نام)'

                # Decode the main content
                decoded_str = base64.urlsafe_b64decode(content_part + '=' * (-len(content_part) % 4)).decode('utf-8')

                # Expected format: method:password@host:port
                creds, host_port = decoded_str.rsplit('@', 1)
                method, password = creds.split(':', 1)
                host, port = host_port.split(':', 1)

                data.update({'host': host, 'port': port, 'details': f"Method: {method}"})

                # Re-encode for the modified link
                new_user_info_b64 = base64.urlsafe_b64encode(f"{method}:{password}".encode('utf-8')).decode('utf-8').rstrip("=")

                # Reconstruct the original link structure before adding the new tag
                base_link = f"ss://{new_user_info_b64}@{host}:{port}"
                data['modified_link'] = f"{base_link}#{urllib.parse.quote(new_name)}"
                return data

            except Exception:
                 raise ValueError("ساختار لینک Base64 SS نامعتبر است.")

        raise ValueError("ساختار لینک SS نامعتبر است یا پشتیبانی نمی‌شود.")

    def _parse_vless_or_trojan(self, line, new_name, protocol_type):
        """پردازشگر عمومی و مقاوم برای لینک‌های VLESS و Trojan."""
        data = {'type': protocol_type, 'protocol': protocol_type.upper(), 'name': new_name}

        pattern = re.compile(
            r"^(?P<protocol>vless|trojan)://"
            r"(?P<user_info>[^@]+)@"
            r"(?P<host>[^:?#]+):(?P<port>\d+)"
            r"\??(?P<query>[^#]*)"
            r"#?(?P<fragment>.*)$"
        )
        match = pattern.match(line)
        if not match:
            raise ValueError(f"ساختار لینک {protocol_type.upper()} نامعتبر است.")

        parts = match.groupdict()
        data['host'] = parts['host']
        data['port'] = parts['port']
        data['original_name'] = urllib.parse.unquote(parts['fragment']) if parts['fragment'] else '(بدون نام)'

        query_params = dict(urllib.parse.parse_qsl(parts['query']))
        sni = query_params.get('sni', query_params.get('peer', parts['host']))
        path = query_params.get('path', 'N/A')
        net_type = query_params.get('type', 'N/A')
        data['details'] = f"SNI: {sni} | Net: {net_type} | Path: {path[:20]}"

        base_link = f"{parts['protocol']}://{parts['user_info']}@{parts['host']}:{parts['port']}"
        if parts['query']:
            base_link += f"?{parts['query']}"
        data['modified_link'] = f"{base_link}#{urllib.parse.quote(new_name)}"
        return data

    def _parse_vless(self, line, new_name):
        return self._parse_vless_or_trojan(line, new_name, 'vless')

    def _parse_trojan(self, line, new_name):
        # Trojan links can have passwords with special characters.
        # Handle them by not including the password in the regex
        try:
            return self._parse_vless_or_trojan(line, new_name, 'trojan')
        except ValueError:
            # Fallback for complex passwords
            match = re.match(r"trojan://(?P<user_info>[^@]+)@(?P<host_port_and_fragment>.+)", line)
            if not match:
                raise ValueError("ساختار لینک Trojan نامعتبر است.")

            parts = match.groupdict()
            user_info = parts['user_info']
            host_port_and_fragment = parts['host_port_and_fragment']

            # The rest of the URL can be parsed normally
            parsed_url = urllib.parse.urlparse(f"trojan://{host_port_and_fragment}")

            data = {'type': 'trojan', 'protocol': 'TROJAN', 'name': new_name}
            data['host'] = parsed_url.hostname
            data['port'] = parsed_url.port
            data['original_name'] = urllib.parse.unquote(parsed_url.fragment) if parsed_url.fragment else '(بدون نام)'

            query_params = dict(urllib.parse.parse_qsl(parsed_url.query))
            sni = query_params.get('sni', query_params.get('peer', parsed_url.hostname))
            path = query_params.get('path', 'N/A')
            net_type = query_params.get('type', 'N/A')
            data['details'] = f"SNI: {sni} | Net: {net_type} | Path: {path[:20]}"

            base_link = f"trojan://{user_info}@{data['host']}:{data['port']}"
            if parsed_url.query:
                base_link += f"?{parsed_url.query}"
            data['modified_link'] = f"{base_link}#{urllib.parse.quote(new_name)}"
            return data

    def _parse_telegram(self, line, new_name):
        """پردازشگر پراکسی تلگرام با قابلیت استخراج نام از فرگمنت (#)."""
        try:
            parsed_url = urllib.parse.urlsplit(line)
            params = dict(urllib.parse.parse_qsl(parsed_url.query))
        except Exception:
            raise ValueError("ساختار URL لینک تلگرام نامعتبر است.")

        if not all(k in params for k in ["server", "port", "secret"]):
            raise ValueError("لینک تلگرام ناقص است (فاقد سرور، پورت یا سکرت).")

        data = {
            'type': 'telegram',
            'server': params.get("server"),
            'port': params.get("port"),
            'secret': params.get("secret"),
            'modified_link': line,
            'original_link': line,
            'original_name': urllib.parse.unquote(parsed_url.fragment) if parsed_url.fragment else params.get("server")
        }
        return data

    # --- Rendering and Data Management ---

    def _add_item_to_tree(self, tree, data, columns):
        """یک آیتم به جدول (Treeview) اضافه کرده و آن را در مپ داده‌ها ذخیره می‌کند."""
        values = tuple(data.get(k, 'N/A') for k in columns)
        tag = 'evenrow' if len(tree.get_children()) % 2 == 0 else 'oddrow'
        iid = tree.insert("", "end", values=values, tags=(tag,))
        self.tree_data_map[iid] = data

    def clear_results(self):
        """تمام جداول خروجی و داده‌های ذخیره شده را پاک می‌کند."""
        self.tree_data_map.clear()
        for tree in [self.v2ray_tree, self.telegram_tree, self.original_names_tree, self.failed_links_tree]:
            tree.delete(*tree.get_children())

    def clear_all(self):
        if messagebox.askyesno("تایید", "تمام ورودی و خروجی‌ها پاک شوند؟"):
            self.input_text.delete("1.0", tk.END)
            self.clear_results()
            self.clear_added_files()
            self.update_status("آماده")

    def get_full_links_from_tree(self, tree):
        """لینک‌های کامل را از آیتم‌های موجود در یک جدول استخراج می‌کند."""
        links = []
        for iid in tree.get_children():
            if data := self.tree_data_map.get(iid):
                links.append(data.get('modified_link', data.get('link', '')))
        return links

    def copy_selected(self, tree):
        """لینک مربوط به آیتم انتخاب شده را با استفاده از iid کپی می‌کند (بدون باگ)."""
        if not (selected_iid := tree.focus()): return

        if data := self.tree_data_map.get(selected_iid):
            link_to_copy = data.get('modified_link', data.get('link', ''))
            self.clipboard_clear()
            self.clipboard_append(link_to_copy)
            self.update_status("لینک انتخاب شده کپی شد.")
        else:
            self.update_status("خطا در بازیابی لینک.", error=True)

    def copy_all(self, tree):
        if links := self.get_full_links_from_tree(tree):
            # Filter out empty or None links before joining
            valid_links = [link for link in links if link]
            if valid_links:
                self.clipboard_clear()
                self.clipboard_append("\n".join(valid_links))
                self.update_status(f"{len(valid_links)} لینک در کلیپ‌بورد کپی شد.")
            else:
                self.update_status("محتوایی برای کپی کردن وجود ندارد.", error=True)
        else:
            self.update_status("محتوایی برای کپی کردن وجود ندارد.", error=True)

    def save_to_file(self, tree):
        links = self.get_full_links_from_tree(tree)
        valid_links = [link for link in links if link]

        if not valid_links:
            self.update_status("محتوایی برای ذخیره کردن وجود ندارد.", error=True)
            return

        if not (filepath := filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")], title="ذخیره فایل")):
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(valid_links))
            self.update_status(f"فایل با موفقیت در {filepath} ذخیره شد.")
        except Exception as e:
            self.update_status(f"خطا در ذخیره فایل: {e}", error=True)

    # --- File Operations ---
    def load_from_file(self):
        if not (filepaths := filedialog.askopenfilenames(title="انتخاب فایل(ها)")): return
        all_links = []
        if not hasattr(self, 'file_contents'):
            self.file_contents = {}
        for path in filepaths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Generate a unique key for the file based on its path and content
                    if path in self.file_contents and self.file_contents.get(path) == content:
                        continue
                    self.file_contents[path] = content

                    if path.lower().endswith('.json'):
                        all_links.extend(self._extract_links_from_json(json.loads(content)))
                    else:
                        all_links.extend(content.splitlines())
                self._add_item_to_tree(self.added_files_tree, {'نام فایل': path, 'path': path}, ('نام فایل',))
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در خواندن فایل {path}:\n{e}")

        if all_links:
            self.input_text.insert(tk.END, "\n".join(all_links) + "\n")
            self.update_status(f"{len(filepaths)} فایل با موفقیت بارگذاری شد.")

    def remove_selected_file(self):
        selected_items = self.added_files_tree.selection()
        if not selected_items:
            return

        for item_id in selected_items:
            file_path = self.tree_data_map[item_id]['path']
            if file_path in self.file_contents:
                del self.file_contents[file_path]
            self.added_files_tree.delete(item_id)
            del self.tree_data_map[item_id]

    def clear_added_files(self):
        self.added_files_tree.delete(*self.added_files_tree.get_children())
        self.file_contents.clear()

    def _extract_links_from_json(self, data):
        links = []
        if isinstance(data, str) and any(data.lower().startswith(p) for p in V2RAY_PROTOCOLS + TELEGRAM_PROTOCOLS): links.append(data)
        elif isinstance(data, list): [links.extend(self._extract_links_from_json(item)) for item in data]
        elif isinstance(data, dict): [links.extend(self._extract_links_from_json(value)) for value in data.values()]
        return links

if __name__ == "__main__":
    app = VpnConfigEditorApp()
    app.mainloop()
