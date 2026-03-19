import gc
import json
import os
import queue
import re
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font as tkfont
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)

# ── Performance tuning ────────────────────────────────────────────────────────
_CPU_CORES = os.cpu_count() or 4
torch.set_num_threads(_CPU_CORES)
torch.set_num_interop_threads(max(1, _CPU_CORES // 2))
torch.backends.mkldnn.enabled = True

# Optional voice support
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    pyttsx3 = None
    TTS_AVAILABLE = False

DEFAULT_MODEL    = "fdtn-ai/Foundation-Sec-8B-Instruct"
MODELS_DB_FILE   = "models.json"

CODING_SYSTEM_PROMPTS = {
    "General Coding Assistant": (
        "You are an expert software engineer. When answering:\n"
        "- Always wrap code in ```language blocks\n"
        "- Explain your reasoning before and after code\n"
        "- Mention time/space complexity for algorithms\n"
        "- Point out potential bugs or edge cases\n"
        "- Prefer idiomatic, production-ready code"
    ),
    "Code Reviewer": (
        "You are a senior code reviewer. Analyse code for:\n"
        "- Bugs and logic errors\n"
        "- Security vulnerabilities\n"
        "- Performance issues\n"
        "- Style and readability\n"
        "- Test coverage gaps\n"
        "Always provide specific line references and improved versions."
    ),
    "Python Expert": (
        "You are a Python expert (3.10+). Favour:\n"
        "- Type hints and dataclasses\n"
        "- Pythonic idioms and comprehensions\n"
        "- asyncio where appropriate\n"
        "- PEP-8 style\n"
        "Always wrap Python code in ```python blocks."
    ),
    "Debugging Assistant": (
        "You are a debugging specialist. For every problem:\n"
        "1. Identify the root cause\n"
        "2. Explain WHY the bug occurs\n"
        "3. Show a minimal reproducer\n"
        "4. Provide a corrected version\n"
        "5. Suggest how to prevent similar issues"
    ),
    "Architecture & Design": (
        "You are a software architect. Focus on:\n"
        "- SOLID principles and design patterns\n"
        "- Scalability and maintainability\n"
        "- Trade-offs between approaches\n"
        "- Provide diagrams as ASCII art where helpful\n"
        "- Suggest testing strategies"
    ),
}

LANG_COLORS = {
    "python":     "#3b7dd8",
    "javascript": "#f0b429",
    "typescript": "#2f74c0",
    "rust":       "#ce412b",
    "go":         "#00acd7",
    "java":       "#e76f00",
    "c":          "#555555",
    "cpp":        "#004482",
    "bash":       "#3d9970",
    "sql":        "#e88d1c",
    "html":       "#e44d26",
    "css":        "#264de4",
    "json":       "#888",
    "yaml":       "#cb171e",
    "":           "#555",
}

PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
}

JS_KEYWORDS = {
    "break", "case", "catch", "class", "const", "continue", "debugger",
    "default", "delete", "do", "else", "export", "extends", "finally",
    "for", "function", "if", "import", "in", "instanceof", "let", "new",
    "return", "static", "super", "switch", "this", "throw", "try", "typeof",
    "var", "void", "while", "with", "yield", "async", "await", "of", "from",
    "true", "false", "null", "undefined",
}


# ─────────────────────────────────────────────────────────────────────────────
# Syntax highlighting
# ─────────────────────────────────────────────────────────────────────────────

def _highlight_code(widget: tk.Text, start: str, end: str, lang: str):
    lang = lang.lower().strip()
    keywords = set()
    if lang == "python":
        keywords = PYTHON_KEYWORDS
    elif lang in ("javascript", "typescript", "js", "ts"):
        keywords = JS_KEYWORDS

    for tag in ("kw", "str_lit", "comment", "number", "decorator"):
        widget.tag_remove(tag, start, end)

    code = widget.get(start, end)
    base_idx = widget.index(start)
    base_line, base_col = map(int, base_idx.split("."))

    def pos(i):
        before = code[:i]
        lines  = before.split("\n")
        line   = base_line + len(lines) - 1
        col    = len(lines[-1]) if len(lines) > 1 else base_col + len(lines[-1])
        return f"{line}.{col}"

    def pos_end(i):
        before = code[:i]
        lines  = before.split("\n")
        line   = base_line + len(lines) - 1
        col    = len(lines[-1]) if len(lines) > 1 else base_col + len(lines[-1])
        return f"{line}.{col}"

    for m in re.finditer(
        r'(\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'|'
        r'\"[^\"\\]*(?:\\.[^\"\\]*)*\"|\'[^\'\\]*(?:\\.[^\'\\]*)*\')',
        code,
    ):
        widget.tag_add("str_lit", pos(m.start()), pos_end(m.end()))

    cpat = r'(#[^\n]*)' if lang == "python" else r'(//[^\n]*|/\*[\s\S]*?\*/)'
    for m in re.finditer(cpat, code):
        widget.tag_add("comment", pos(m.start()), pos_end(m.end()))

    for m in re.finditer(r'\b(\d+\.?\d*)\b', code):
        widget.tag_add("number", pos(m.start()), pos_end(m.end()))

    if lang == "python":
        for m in re.finditer(r'@\w+', code):
            widget.tag_add("decorator", pos(m.start()), pos_end(m.end()))

    if keywords:
        pat = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
        for m in re.finditer(pat, code):
            widget.tag_add("kw", pos(m.start()), pos_end(m.end()))


# ─────────────────────────────────────────────────────────────────────────────
# VoiceEngine
# ─────────────────────────────────────────────────────────────────────────────

class VoiceEngine:
    def __init__(self):
        self.enabled   = TTS_AVAILABLE
        self.engine    = None
        self.lock      = threading.Lock()
        self.stop_flag = False
        if self.enabled:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 185)
                self.engine.setProperty("volume", 1.0)
            except Exception:
                self.enabled = False
                self.engine  = None

    def speak(self, text):
        if not self.enabled or not self.engine or not text.strip():
            return
        with self.lock:
            try:
                self.stop_flag = False
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                pass

    def stop(self):
        if not self.enabled or not self.engine:
            return
        with self.lock:
            try:
                self.stop_flag = True
                self.engine.stop()
            except Exception:
                pass

    def get_voice_names(self):
        if not self.enabled or not self.engine:
            return []
        try:
            return [v.name for v in self.engine.getProperty("voices")]
        except Exception:
            return []

    def set_voice_by_name(self, voice_name):
        if not self.enabled or not self.engine:
            return False
        try:
            for voice in self.engine.getProperty("voices"):
                if voice.name == voice_name:
                    self.engine.setProperty("voice", voice.id)
                    return True
        except Exception:
            pass
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ChatBubble
# ─────────────────────────────────────────────────────────────────────────────

class ChatBubble(tk.Frame):
    ROLE_STYLE = {
        "user":      {"bubble": "#1e3a5f", "text": "#dbeafe", "meta": "#93c5fd"},
        "assistant": {"bubble": "#0f1f0f", "text": "#d1fae5", "meta": "#6ee7b7"},
        "system":    {"bubble": "#1c1917", "text": "#cbd5e1", "meta": "#64748b"},
    }

    def __init__(self, parent, text="", role="assistant", timestamp=None, mono_font=None):
        bg_outer = parent["bg"]
        style    = self.ROLE_STYLE.get(role, self.ROLE_STYLE["assistant"])
        super().__init__(parent, bg=bg_outer)

        side   = "right" if role == "user" else "left"
        anchor = "e"     if role == "user" else "w"

        container = tk.Frame(self, bg=bg_outer)
        container.pack(fill="x", padx=10, pady=5)

        self._bubble = tk.Frame(
            container,
            bg=style["bubble"],
            highlightbackground="#1f2937",
            highlightthickness=1,
            padx=14, pady=10,
        )
        self._bubble.pack(
            side=side, anchor=anchor,
            fill="x" if role != "user" else None,
            expand=role != "user",
        )

        self._style      = style
        self._mono_font  = mono_font or ("Courier New", 10)
        self._prose_font = ("Segoe UI", 11)
        self._role       = role
        self._full_text  = ""
        self._widgets: list[tk.Widget] = []

        ts = timestamp or datetime.now().strftime("%H:%M")
        self._meta = tk.Label(
            self._bubble, text=ts,
            bg=style["bubble"], fg=style["meta"],
            font=("Segoe UI", 8),
        )
        self._meta.pack(anchor="e", pady=(4, 0))

        if text:
            self.set_text(text)

    def append_text(self, chunk: str):
        self._full_text += chunk
        self._render(self._full_text)

    def set_text(self, text: str):
        self._full_text = text
        self._render(text)

    def get_text(self) -> str:
        return self._full_text

    def _clear_widgets(self):
        for w in self._widgets:
            w.destroy()
        self._widgets.clear()

    def _render(self, text: str):
        self._clear_widgets()
        self._meta.pack_forget()
        for seg in self._parse(text):
            if seg["type"] == "code":
                self._add_code_block(seg["lang"], seg["code"])
            else:
                self._add_prose(seg["text"])
        self._meta.pack(anchor="e", pady=(4, 0))

    def _parse(self, text: str) -> list[dict]:
        pattern = re.compile(r'```(\w*)\n?([\s\S]*?)```', re.MULTILINE)
        result, last = [], 0
        for m in pattern.finditer(text):
            if m.start() > last:
                result.append({"type": "prose", "text": text[last:m.start()]})
            result.append({"type": "code", "lang": m.group(1).lower(), "code": m.group(2)})
            last = m.end()
        tail = text[last:]
        if tail:
            unclosed = re.match(r'```(\w*)\n?([\s\S]*)', tail)
            if unclosed:
                result.append({"type": "code", "lang": unclosed.group(1).lower(), "code": unclosed.group(2)})
            else:
                result.append({"type": "prose", "text": tail})
        return result

    def _add_prose(self, text: str):
        if not text.strip():
            return
        prose_w = tk.Text(
            self._bubble, wrap="word",
            bg=self._style["bubble"], fg=self._style["text"],
            font=self._prose_font, relief="flat", bd=0,
            padx=0, pady=2, cursor="arrow",
            state="normal", height=1, width=80,
        )
        prose_w.tag_config("bold", font=(self._prose_font[0], self._prose_font[1], "bold"))
        prose_w.tag_config(
            "inline_code",
            font=self._mono_font,
            background="#1a2a1a",
            foreground="#86efac",
        )
        pattern = re.compile(r'\*\*(.+?)\*\*|`([^`]+)`', re.DOTALL)
        last = 0
        for m in pattern.finditer(text):
            if m.start() > last:
                prose_w.insert("end", text[last:m.start()])
            if m.group(1) is not None:
                prose_w.insert("end", m.group(1), "bold")
            else:
                prose_w.insert("end", m.group(2), "inline_code")
            last = m.end()
        if last < len(text):
            prose_w.insert("end", text[last:])
        line_count = int(prose_w.index("end-1c").split(".")[0])
        prose_w.config(height=max(1, line_count), state="disabled")
        prose_w.pack(fill="x", pady=(0, 2))
        self._widgets.append(prose_w)

    def _add_code_block(self, lang: str, code: str):
        lang_disp  = lang.upper() if lang else "CODE"
        lang_color = LANG_COLORS.get(lang, LANG_COLORS[""])

        header = tk.Frame(self._bubble, bg="#0d1117")
        header.pack(fill="x", pady=(6, 0))
        tk.Label(
            header, text=f" {lang_disp}",
            bg="#0d1117", fg=lang_color,
            font=("Consolas", 9, "bold"),
        ).pack(side="left", padx=6, pady=4)
        tk.Button(
            header, text="⎘ Copy",
            bg="#21262d", fg="#8b949e",
            activebackground="#30363d", activeforeground="#e6edf3",
            relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 8), padx=8, pady=3,
            command=lambda c=code: self._copy(c),
        ).pack(side="right", padx=6, pady=3)
        self._widgets.append(header)

        code_w = tk.Text(
            self._bubble, wrap="none",
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            font=self._mono_font, relief="flat", bd=0,
            padx=12, pady=8, cursor="xterm",
            state="normal", width=80,
        )
        code_w.tag_config("kw",        foreground="#ff7b72")
        code_w.tag_config("str_lit",   foreground="#a5d6ff")
        code_w.tag_config("comment",   foreground="#8b949e",
                           font=(self._mono_font[0], self._mono_font[1], "italic"))
        code_w.tag_config("number",    foreground="#79c0ff")
        code_w.tag_config("decorator", foreground="#ffa657")
        code_w.insert("1.0", code)
        try:
            _highlight_code(code_w, "1.0", "end", lang)
        except Exception:
            pass
        line_count = code.count("\n") + 1
        code_w.config(height=min(line_count, 35), state="disabled")

        xscroll = tk.Scrollbar(self._bubble, orient="horizontal", command=code_w.xview)
        code_w.config(xscrollcommand=xscroll.set)
        code_w.pack(fill="x")
        xscroll.pack(fill="x", pady=(0, 6))
        self._widgets.extend([code_w, xscroll])

    def _copy(self, text: str):
        self._bubble.clipboard_clear()
        self._bubble.clipboard_append(text)


# ─────────────────────────────────────────────────────────────────────────────
# ScrollableChat
# ─────────────────────────────────────────────────────────────────────────────

class ScrollableChat(tk.Frame):
    def __init__(self, parent, bg="#0a0f0a", mono_font=None):
        super().__init__(parent, bg=bg)
        self._mono_font = mono_font or ("Courier New", 10)

        self.canvas    = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, relief="flat")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner     = tk.Frame(self.canvas, bg=bg)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width),
        )
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

    def add_bubble(self, text="", role="assistant") -> ChatBubble:
        bubble = ChatBubble(self.inner, text=text, role=role, mono_font=self._mono_font)
        bubble.pack(fill="x", anchor="w", pady=2)
        self.after(40, lambda: self.canvas.yview_moveto(1.0))
        return bubble

    def scroll_bottom(self):
        self.after(40, lambda: self.canvas.yview_moveto(1.0))

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.scroll_bottom()


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

class AIChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Local AI — Coding Assistant")
        self.root.geometry("1480x900")
        self.root.minsize(1100, 720)
        self.root.configure(bg="#020c02")

        self.ui_queue: queue.Queue       = queue.Queue()
        self.messages: list[dict]        = []
        self.model_loaded                = False
        self.is_generating               = False
        self.stop_generation             = False
        self.current_assistant_bubble: ChatBubble | None = None
        self.typing_job                  = None
        self.typing_state                = 0

        self.model              = None
        self.tokenizer          = None
        self.current_model_repo = DEFAULT_MODEL
        self.current_model_name = DEFAULT_MODEL
        self.voice              = VoiceEngine()

        self._attached_file_content: str | None = None
        self._attached_file_name:    str | None = None

        self._build_theme()
        self.ensure_model_db()
        self.model_db = self.load_model_db()

        available       = list(tkfont.families())
        mono_pref       = ["Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas", "Courier New"]
        self._mono_font = next((f for f in mono_pref if f in available), "Courier New")
        self._mono      = (self._mono_font, 10)

        self._build_layout()
        self.refresh_models_ui()
        self.refresh_voice_ui()
        self.log_system("Loading default model… first launch may take a while.")

        threading.Thread(
            target=self.load_model_dynamic,
            args=(self.current_model_repo, True),
            daemon=True,
        ).start()

        self.root.after(50, self.process_ui_queue)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _build_theme(self):
        self.c = {
            "bg":        "#020c02",
            "panel":     "#0a1a0a",
            "panel2":    "#0d1a0d",
            "panel3":    "#111f11",
            "accent":    "#16a34a",
            "accent2":   "#15803d",
            "text":      "#e2ffe2",
            "muted":     "#6b9e6b",
            "green":     "#4ade80",
            "red":       "#f87171",
            "yellow":    "#fbbf24",
            "border":    "#1a2e1a",
            "input_bg":  "#060f06",
            "header_bg": "#030f03",
        }

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.main = tk.Frame(self.root, bg=self.c["bg"])
        self.main.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.main, bg=self.c["panel2"], width=300)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.main, bg=self.c["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_header()
        self._build_chat_area()
        self._build_input_area()
        self._build_statusbar()

    def _build_sidebar(self):
        top = tk.Frame(self.sidebar, bg=self.c["panel2"])
        top.pack(fill="x", padx=14, pady=(14, 6))
        tk.Label(
            top, text="</> Tim's Coding AI",
            bg=self.c["panel2"], fg=self.c["green"],
            font=(self._mono_font, 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            top, text="Local inference · no cloud",
            bg=self.c["panel2"], fg=self.c["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self._sep(self.sidebar)

        bf = tk.Frame(self.sidebar, bg=self.c["panel2"])
        bf.pack(fill="x", padx=14)
        for label, cmd, color in [
            ("＋ New Chat",     self.new_chat,                None),
            ("■ Stop",          self.stop_current_generation, self.c["red"]),
            ("📎 Attach File",  self.attach_file,             None),
            ("💾 Save Chat",    self.save_chat,               None),
            ("🗑 Clear",        self.clear_messages,          None),
            ("⏏ Unload Model", self.unload_model,            None),
        ]:
            self._btn(bf, label, cmd, bg=color).pack(fill="x", pady=3)

        self._sep(self.sidebar)

        tk.Label(
            self.sidebar, text="System Prompt Preset",
            bg=self.c["panel2"], fg=self.c["muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(8, 4))

        self._preset_var = tk.StringVar(value=list(CODING_SYSTEM_PROMPTS.keys())[0])
        preset_menu = tk.OptionMenu(
            self.sidebar, self._preset_var,
            *CODING_SYSTEM_PROMPTS.keys(),
            command=self._apply_preset,
        )
        preset_menu.config(
            bg=self.c["panel3"], fg=self.c["text"],
            activebackground=self.c["accent2"], activeforeground="#fff",
            relief="flat", bd=0, font=("Segoe UI", 9), width=28,
        )
        preset_menu["menu"].config(
            bg=self.c["panel3"], fg=self.c["text"],
            activebackground=self.c["accent2"], activeforeground="#fff",
        )
        preset_menu.pack(fill="x", padx=14, pady=(0, 8))

        tk.Label(
            self.sidebar, text="System Prompt",
            bg=self.c["panel2"], fg=self.c["muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(0, 4))

        self.system_prompt = tk.Text(
            self.sidebar, height=9, wrap="word",
            bg=self.c["input_bg"], fg=self.c["text"],
            insertbackground=self.c["text"],
            relief="flat", bd=0, padx=10, pady=10,
            font=("Segoe UI", 9),
        )
        self.system_prompt.pack(fill="x", padx=14)
        self._apply_preset(self._preset_var.get())

        self._sep(self.sidebar)
        self._build_gen_params()
        self._sep(self.sidebar)
        self._build_model_manager()
        self._sep(self.sidebar)
        self._build_voice_box()
        self._sep(self.sidebar)
        self._build_tips()

    def _build_gen_params(self):
        box = self._box(self.sidebar, "Generation Parameters")
        self._temp_var   = tk.DoubleVar(value=0.2)
        self._topp_var   = tk.DoubleVar(value=0.95)
        self._maxtok_var = tk.IntVar(value=1024)
        self._repen_var  = tk.DoubleVar(value=1.05)
        for label, var, from_, to_, res in [
            ("Temp",    self._temp_var,   0.0, 2.0,  0.05),
            ("Top-p",   self._topp_var,   0.1, 1.0,  0.05),
            ("Max tok", self._maxtok_var, 64,  4096, 64),
            ("Rep pen", self._repen_var,  1.0, 1.5,  0.01),
        ]:
            self._param_row(box, label, var, from_, to_, res)

    def _param_row(self, parent, label, var, from_, to_, res):
        f = tk.Frame(parent, bg=self.c["panel"])
        f.pack(fill="x", padx=10, pady=2)
        tk.Label(
            f, text=f"{label}:", width=8, anchor="w",
            bg=self.c["panel"], fg=self.c["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left")
        val_lbl = tk.Label(
            f, text=str(var.get()), width=6,
            bg=self.c["panel"], fg=self.c["green"],
            font=(self._mono_font, 9),
        )
        val_lbl.pack(side="right")
        tk.Scale(
            f, variable=var, from_=from_, to=to_,
            resolution=res, orient="horizontal",
            bg=self.c["panel"], fg=self.c["text"],
            troughcolor=self.c["panel3"],
            highlightthickness=0, activebackground=self.c["accent"],
            sliderrelief="flat", bd=0, showvalue=False,
            command=lambda v, lbl=val_lbl: lbl.config(text=v),
        ).pack(side="left", fill="x", expand=True)

    def _build_model_manager(self):
        box = self._box(self.sidebar, "Model Manager")
        self.model_label = tk.Label(
            box, text="Current: none",
            bg=self.c["panel"], fg=self.c["text"],
            wraplength=260, justify="left",
            font=("Segoe UI", 8),
        )
        self.model_label.pack(anchor="w", padx=10, pady=(0, 6))

        self.model_listbox = tk.Listbox(
            box,
            bg=self.c["input_bg"], fg=self.c["text"],
            selectbackground=self.c["accent"], selectforeground="#fff",
            relief="flat", highlightthickness=0, bd=0,
            height=5, font=("Segoe UI", 9),
        )
        self.model_listbox.pack(fill="x", padx=10, pady=(0, 6))

        for r1, r2 in [
            [("Load",    self.load_selected_model),  ("Add",     self.add_model_prompt)],
            [("Remove",  self.remove_selected_model), ("Refresh", self.refresh_models_ui)],
        ]:
            row = tk.Frame(box, bg=self.c["panel"])
            row.pack(fill="x", padx=10, pady=(0, 4))
            for label, cmd in [r1, r2]:
                self._btn(row, label, cmd).pack(side="left", fill="x", expand=True, padx=2)

    def _build_voice_box(self):
        box    = self._box(self.sidebar, "Voice Output")
        status = "Available" if self.voice.enabled else "Unavailable (install pyttsx3)"
        self.voice_status_label = tk.Label(
            box, text=f"TTS: {status}",
            bg=self.c["panel"], fg=self.c["text"],
            font=("Segoe UI", 9),
        )
        self.voice_status_label.pack(anchor="w", padx=10, pady=(0, 4))

        self.voice_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            box, text="Enable voice responses",
            variable=self.voice_enabled_var,
            bg=self.c["panel"], fg=self.c["text"],
            selectcolor=self.c["panel"], activebackground=self.c["panel"],
            command=self.on_voice_toggle,
        ).pack(anchor="w", padx=10)

        self.voice_names    = self.voice.get_voice_names()
        self.voice_name_var = tk.StringVar(
            value=self.voice_names[0] if self.voice_names else "Default"
        )
        tk.OptionMenu(
            box, self.voice_name_var,
            *(self.voice_names if self.voice_names else ["Default"]),
            command=lambda v: self.voice.set_voice_by_name(v),
        ).pack(fill="x", padx=10, pady=(4, 8))

    def _build_tips(self):
        box = self._box(self.sidebar, "Keyboard Shortcuts")
        tk.Label(
            box,
            text=(
                "Enter        → send message\n"
                "Shift+Enter  → new line\n"
                "Ctrl+L       → clear input\n"
                "Ctrl+K       → copy last response\n"
                "■ Stop       → interrupt generation"
            ),
            bg=self.c["panel"], fg=self.c["text"],
            justify="left", font=(self._mono_font, 8),
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def _build_header(self):
        header = tk.Frame(self.content, bg=self.c["header_bg"])
        header.pack(fill="x")

        left = tk.Frame(header, bg=self.c["header_bg"])
        left.pack(side="left", fill="x", expand=True, padx=18, pady=12)
        tk.Label(
            left, text="Tim's AI -- Chat",
            bg=self.c["header_bg"], fg=self.c["text"],
            font=(self._mono_font, 18, "bold"),
        ).pack(anchor="w")
        self.subtitle_label = tk.Label(
            left, text="Offline · local inference",
            bg=self.c["header_bg"], fg=self.c["muted"],
            font=("Segoe UI", 9),
        )
        self.subtitle_label.pack(anchor="w")

        right = tk.Frame(header, bg=self.c["header_bg"])
        right.pack(side="right", padx=18)

        self.pill = tk.Label(
            right, text="LOADING",
            bg="#3b0000", fg="#fca5a5",
            font=("Segoe UI Semibold", 9), padx=12, pady=6,
        )
        self.pill.pack(side="right", pady=6)

        self.token_label = tk.Label(
            right, text="tokens: —",
            bg=self.c["header_bg"], fg=self.c["muted"],
            font=(self._mono_font, 9),
        )
        self.token_label.pack(side="right", padx=12)

        tk.Frame(self.content, bg=self.c["border"], height=1).pack(fill="x")

    def _build_chat_area(self):
        self.chat_frame = ScrollableChat(
            self.content, bg=self.c["bg"], mono_font=self._mono
        )
        self.chat_frame.pack(fill="both", expand=True)

    def _build_input_area(self):
        wrapper = tk.Frame(self.content, bg=self.c["bg"])
        wrapper.pack(fill="x", padx=14, pady=(0, 10))

        self.attach_label = tk.Label(
            wrapper, text="",
            bg=self.c["bg"], fg=self.c["yellow"],
            font=("Segoe UI", 9),
        )
        self.attach_label.pack(anchor="w", pady=(0, 2))

        card = tk.Frame(
            wrapper, bg=self.c["panel"],
            highlightbackground=self.c["border"], highlightthickness=1,
        )
        card.pack(fill="x")

        self.input_box = tk.Text(
            card, height=5, wrap="word",
            bg=self.c["input_bg"], fg=self.c["text"],
            insertbackground=self.c["green"],
            relief="flat", bd=0, padx=14, pady=12,
            font=("Segoe UI", 11),
        )
        self.input_box.pack(fill="x", padx=2, pady=2)
        self.input_box.bind("<Return>",      self.on_enter_pressed)
        self.input_box.bind("<Shift-Return>", lambda e: "break" if self._insert_newline() else None)
        self.input_box.bind("<KeyRelease>",  self.update_input_stats)
        self.input_box.bind("<Control-l>",   lambda e: self._clear_input())
        self.input_box.bind("<Control-k>",   lambda e: self._copy_last_response())

        controls = tk.Frame(card, bg=self.c["panel"])
        controls.pack(fill="x", padx=12, pady=(0, 8))

        self.input_stats = tk.Label(
            controls, text="0 chars · 0 lines",
            bg=self.c["panel"], fg=self.c["muted"],
            font=(self._mono_font, 9),
        )
        self.input_stats.pack(side="left")

        self.mono_input_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            controls, text="mono input",
            variable=self.mono_input_var,
            bg=self.c["panel"], fg=self.c["muted"],
            selectcolor=self.c["panel"], activebackground=self.c["panel"],
            font=("Segoe UI", 8),
            command=self._toggle_mono_input,
        ).pack(side="left", padx=10)

        self._btn(controls, "⎘ Copy Response", self._copy_last_response).pack(
            side="right", padx=(4, 0)
        )
        self.send_btn = self._btn(controls, "Send ⏎", self.send, bg=self.c["accent"])
        self.send_btn.pack(side="right")

    def _build_statusbar(self):
        bar = tk.Frame(self.content, bg=self.c["panel2"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_label = tk.Label(
            bar, text="Starting…",
            bg=self.c["panel2"], fg=self.c["muted"],
            font=("Segoe UI", 8),
        )
        self.status_label.pack(side="left", padx=10)

        self.clock_label = tk.Label(
            bar, text="",
            bg=self.c["panel2"], fg=self.c["muted"],
            font=(self._mono_font, 8),
        )
        self.clock_label.pack(side="right", padx=10)
        self.update_clock()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sep(self, parent):
        tk.Frame(parent, bg=self.c["border"], height=1).pack(fill="x", padx=14, pady=6)

    def _box(self, parent, title) -> tk.Frame:
        tk.Label(
            parent, text=title,
            bg=self.c["panel2"], fg=self.c["muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(4, 4))
        box = tk.Frame(
            parent, bg=self.c["panel"],
            highlightbackground=self.c["border"], highlightthickness=1,
        )
        box.pack(fill="x", padx=14, pady=(0, 4))
        return box

    def _btn(self, parent, text, command, bg=None) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=bg or self.c["panel3"], fg="#ffffff",
            activebackground=self.c["accent2"], activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=7, font=("Segoe UI", 9),
        )

    def _apply_preset(self, name: str):
        self.system_prompt.delete("1.0", "end")
        self.system_prompt.insert("1.0", CODING_SYSTEM_PROMPTS.get(name, ""))

    def _insert_newline(self) -> bool:
        self.input_box.insert(tk.INSERT, "\n")
        self.update_input_stats()
        return True

    def _clear_input(self):
        self.input_box.delete("1.0", "end")
        self.update_input_stats()

    def _toggle_mono_input(self):
        self.input_box.config(
            font=self._mono if self.mono_input_var.get() else ("Segoe UI", 11)
        )

    def _copy_last_response(self):
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                self.root.clipboard_clear()
                self.root.clipboard_append(msg["content"])
                self.set_status("Last response copied to clipboard.")
                return
        self.set_status("No assistant response found.")

    def update_input_stats(self, event=None):
        text  = self.input_box.get("1.0", "end-1c")
        chars = len(text)
        lines = text.count("\n") + 1
        self.input_stats.config(text=f"{chars} chars · {lines} lines")
        est = max(1, chars // 4)
        self.token_label.config(text=f"~{est} input tokens")

    def update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    # ── File attachment ───────────────────────────────────────────────────────

    def attach_file(self):
        path = filedialog.askopenfilename(
            title="Attach a code file",
            filetypes=[
                ("Code / Text",
                 "*.py *.js *.ts *.jsx *.tsx *.java *.c *.cpp *.h *.rs "
                 "*.go *.rb *.php *.sh *.bat *.md *.txt *.json *.yaml *.yml "
                 "*.toml *.csv *.html *.css *.sql"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if len(content) > 32_000:
                if not messagebox.askyesno(
                    "Large file",
                    f"File is {len(content)} chars. Truncate to 32 000?",
                ):
                    return
                content = content[:32_000] + "\n\n[…truncated…]"
            self._attached_file_content = content
            self._attached_file_name    = os.path.basename(path)
            self.attach_label.config(
                text=f"📎 {self._attached_file_name} (will be included in next message)"
            )
        except Exception as e:
            messagebox.showerror("Error reading file", str(e))

    def _consume_attachment(self) -> str:
        if self._attached_file_content:
            ext   = os.path.splitext(self._attached_file_name or "")[1].lstrip(".")
            block = f"```{ext}\n{self._attached_file_content}\n```"
            self._attached_file_content = None
            self._attached_file_name    = None
            self.attach_label.config(text="")
            return block
        return ""

    # ── Model DB ──────────────────────────────────────────────────────────────

    def ensure_model_db(self):
        if os.path.exists(MODELS_DB_FILE):
            return
        default = {"models": [
            {"name": "Foundation-Sec-8B (default)", "repo": DEFAULT_MODEL,                                    "loads": 0, "last_used": ""},
            {"name": "Qwen2.5 7B Instruct",          "repo": "Qwen/Qwen2.5-7B-Instruct",                     "loads": 0, "last_used": ""},
            {"name": "Mistral 7B Instruct v0.3",     "repo": "mistralai/Mistral-7B-Instruct-v0.3",           "loads": 0, "last_used": ""},
            {"name": "DeepSeek Coder 6.7B",          "repo": "deepseek-ai/deepseek-coder-6.7b-instruct",     "loads": 0, "last_used": ""},
            {"name": "CodeLlama 7B Instruct",        "repo": "codellama/CodeLlama-7b-Instruct-hf",           "loads": 0, "last_used": ""},
        ]}
        with open(MODELS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)

    def load_model_db(self):
        try:
            with open(MODELS_DB_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if "models" in data else {"models": []}
        except Exception:
            return {"models": []}

    def save_model_db(self):
        with open(MODELS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.model_db, f, indent=2)

    def refresh_models_ui(self):
        self.model_db = self.load_model_db()
        self.model_listbox.delete(0, tk.END)
        for item in self.model_db["models"]:
            name  = item.get("name", "Unnamed")
            loads = item.get("loads", 0)
            last  = item.get("last_used", "")
            label = f"{name} [{loads}↑]"
            if last:
                try:
                    label += f" {datetime.fromisoformat(last).strftime('%m/%d %H:%M')}"
                except Exception:
                    pass
            self.model_listbox.insert(tk.END, label)
        self.model_label.config(text=f"Current: {self.current_model_repo}")

    def refresh_voice_ui(self):
        status = "Available" if self.voice.enabled else "Unavailable (install pyttsx3)"
        self.voice_status_label.config(text=f"TTS: {status}")

    # ── Chat management ───────────────────────────────────────────────────────

    def new_chat(self):
        if self.is_generating:
            messagebox.showinfo("Busy", "Stop generation first.")
            return
        self.messages = []
        self.chat_frame.clear()
        self.current_assistant_bubble = None
        self.log_system("New chat started.")

    def clear_messages(self):
        if self.is_generating:
            messagebox.showinfo("Busy", "Stop generation first.")
            return
        self.messages = []
        self.chat_frame.clear()

    def save_chat(self):
        path = filedialog.asksaveasfilename(
            title="Save Chat",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Chat — {self.current_model_repo}\n")
                f.write(f"_Saved: {datetime.now().isoformat()}_\n\n")
                for msg in self.messages:
                    role = msg.get("role", "?").upper()
                    f.write(f"## {role}\n{msg.get('content', '')}\n\n---\n\n")
            messagebox.showinfo("Saved", f"Chat saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Model actions ─────────────────────────────────────────────────────────

    def add_model_prompt(self):
        name = simpledialog.askstring("Model Name", "Display name:")
        if not name:
            return
        repo = simpledialog.askstring(
            "Hugging Face Repo",
            "Repo ID (e.g. deepseek-ai/deepseek-coder-6.7b-instruct):",
        )
        if not repo:
            return
        if any(m.get("repo", "").lower() == repo.strip().lower() for m in self.model_db["models"]):
            messagebox.showinfo("Exists", "That repo is already listed.")
            return
        self.model_db["models"].append(
            {"name": name.strip(), "repo": repo.strip(), "loads": 0, "last_used": ""}
        )
        self.save_model_db()
        self.refresh_models_ui()

    def remove_selected_model(self):
        sel = self.model_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select a model first.")
            return
        info = self.model_db["models"][sel[0]]
        if not messagebox.askyesno("Remove", f"Remove '{info.get('name', info.get('repo'))}'?"):
            return
        del self.model_db["models"][sel[0]]
        self.save_model_db()
        self.refresh_models_ui()

    def load_selected_model(self):
        sel = self.model_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select a model first.")
            return
        repo = self.model_db["models"][sel[0]].get("repo", "").strip()
        if not repo:
            messagebox.showerror("Invalid", "No repo for this entry.")
            return
        if self.is_generating:
            messagebox.showinfo("Busy", "Stop generation first.")
            return
        threading.Thread(
            target=self.load_model_dynamic, args=(repo, False), daemon=True
        ).start()

    def unload_model(self):
        if self.is_generating:
            messagebox.showinfo("Busy", "Stop generation first.")
            return
        self.model_loaded = False
        self.model        = None
        self.tokenizer    = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.set_loaded_state(False)
        self.set_status("Model unloaded")
        self.log_system("Model unloaded.")

    def load_model_dynamic(self, repo: str, startup: bool = False):
        try:
            self.ui_queue.put(("status", f"Loading tokenizer: {repo}"))
            self.ui_queue.put(("loading_state", None))
            self.model_loaded = False

            old_m, old_t  = self.model, self.tokenizer
            self.model    = None
            self.tokenizer = None
            del old_m, old_t
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            tokenizer = AutoTokenizer.from_pretrained(repo)
            self.ui_queue.put(("status", f"Loading weights: {repo}"))

            if torch.cuda.is_available():
                dtype      = torch.float16
                device_map = "auto"
            else:
                # bfloat16 is faster on modern CPUs with AVX-512 BF16 support
                dtype      = torch.bfloat16
                device_map = None

            model = AutoModelForCausalLM.from_pretrained(
                repo,
                torch_dtype=dtype,
                device_map=device_map,
                low_cpu_mem_usage=True,
            )

            if not torch.cuda.is_available():
                model = model.to("cpu")

            # Attempt torch.compile for faster repeated inference (PyTorch 2.x)
            try:
                model = torch.compile(model, mode="reduce-overhead")
                self.ui_queue.put(("status", "Model compiled ✓"))
            except Exception:
                pass

            self.tokenizer    = tokenizer
            self.model        = model
            self.model_loaded = True
            self.current_model_repo = repo

            matched = False
            for item in self.model_db["models"]:
                if item.get("repo", "").lower() == repo.lower():
                    item["loads"]     = item.get("loads", 0) + 1
                    item["last_used"] = datetime.now().isoformat()
                    self.current_model_name = item.get("name", repo)
                    matched = True
                    break
            if not matched:
                self.model_db["models"].append(
                    {"name": repo.split("/")[-1], "repo": repo,
                     "loads": 1, "last_used": datetime.now().isoformat()}
                )
            self.save_model_db()

            device_name = "CUDA" if torch.cuda.is_available() else "CPU"
            self.ui_queue.put(("status", f"Ready on {device_name}"))
            self.ui_queue.put(("loaded", None))
            self.ui_queue.put(("refresh_models", None))
            self.ui_queue.put(("system", f"{'Loaded' if startup else 'Switched to'}: {repo}"))

        except Exception as e:
            self.model_loaded = False
            self.ui_queue.put(("status", "Load failed"))
            self.ui_queue.put(("system", f"Failed to load model: {e}"))

    # ── Send & generate ───────────────────────────────────────────────────────

    def send(self):
        if not self.model_loaded or self.model is None:
            messagebox.showinfo("Loading", "Model not ready yet.")
            return
        if self.is_generating:
            messagebox.showinfo("Busy", "Still generating.")
            return

        user_text = self.input_box.get("1.0", "end-1c").strip()
        if not user_text:
            return

        attachment = self._consume_attachment()
        if attachment:
            full_user_text = f"{attachment}\n\n{user_text}"
            display_text   = f"[📎 file attached]\n{user_text}"
        else:
            full_user_text = user_text
            display_text   = user_text

        self._clear_input()
        self.chat_frame.add_bubble(display_text, role="user")
        self.messages.append({"role": "user", "content": full_user_text})

        self.current_assistant_bubble = self.chat_frame.add_bubble("", role="assistant")
        self.current_assistant_bubble.set_text("Thinking")
        self.start_typing_animation()

        self.is_generating   = True
        self.stop_generation = False
        self.set_status("Generating…")
        threading.Thread(target=self.generate, daemon=True).start()

    def stop_current_generation(self):
        if self.is_generating:
            self.stop_generation = True
            self.voice.stop()
            self.set_status("Stopping…")

    def start_typing_animation(self):
        self.typing_state = 0

        def animate():
            if not self.is_generating or not self.current_assistant_bubble:
                return
            dots = "." * (self.typing_state % 4)
            self.current_assistant_bubble.set_text(f"Thinking{dots}")
            self.typing_state += 1
            self.typing_job = self.root.after(350, animate)

        animate()

    def stop_typing_animation(self):
        if self.typing_job is not None:
            self.root.after_cancel(self.typing_job)
            self.typing_job = None

    def generate(self):
        try:
            system_text = self.system_prompt.get("1.0", "end-1c").strip()
            prompt_messages = []
            if system_text:
                prompt_messages.append({"role": "system", "content": system_text})
            prompt_messages.extend(self.messages)

            prompt = self.tokenizer.apply_chat_template(
                prompt_messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            # Robust device detection — works with and without device_map
            device = next(
                (p.device for p in self.model.parameters() if p.device.type != "meta"),
                torch.device("cpu"),
            )

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=3072,
            ).to(device)

            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_special_tokens=True,
                skip_prompt=True,
            )

            temp = float(self._temp_var.get())
            gen_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=int(self._maxtok_var.get()),
                repetition_penalty=float(self._repen_var.get()),
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=True,          # KV-cache — big speedup on CPU
            )
            if temp > 0:
                gen_kwargs.update(
                    temperature=temp,
                    top_p=float(self._topp_var.get()),
                    do_sample=True,
                )
            else:
                gen_kwargs["do_sample"] = False

            def _run():
                with torch.no_grad():
                    self.model.generate(**gen_kwargs)

            threading.Thread(target=_run, daemon=True).start()

            response = ""
            first    = True
            for token in streamer:
                if self.stop_generation:
                    break
                cleaned = token.replace("<think>", "").replace("</think>", "")
                if not cleaned:
                    continue
                response += cleaned
                if first:
                    self.ui_queue.put(("assistant_start", cleaned))
                    first = False
                else:
                    self.ui_queue.put(("assistant_chunk", cleaned))

            response = response.strip()
            if self.stop_generation:
                response = (response + "\n\n*[Generation stopped]*").strip()

            self.ui_queue.put(("assistant_done", response or "[No response]"))

        except Exception as e:
            self.ui_queue.put(("assistant_error", str(e)))

    # ── UI queue ──────────────────────────────────────────────────────────────

    def process_ui_queue(self):
        try:
            while True:
                event, payload = self.ui_queue.get_nowait()

                if event == "status":
                    self.set_status(payload)

                elif event == "loaded":
                    self.set_loaded_state(True)

                elif event == "loading_state":
                    self.set_loaded_state(False)

                elif event == "system":
                    self.log_system(payload)

                elif event == "refresh_models":
                    self.refresh_models_ui()

                elif event == "assistant_start":
                    self.stop_typing_animation()
                    if self.current_assistant_bubble:
                        self.current_assistant_bubble.set_text(payload)
                    self.chat_frame.scroll_bottom()

                elif event == "assistant_chunk":
                    if self.current_assistant_bubble:
                        self.current_assistant_bubble.append_text(payload)
                    self.chat_frame.scroll_bottom()

                elif event == "assistant_done":
                    self.stop_typing_animation()
                    if self.current_assistant_bubble:
                        self.current_assistant_bubble.set_text(payload)
                    self.messages.append({"role": "assistant", "content": payload})
                    self.current_assistant_bubble = None
                    self.is_generating            = False
                    self.stop_generation          = False
                    self.set_status("Ready")
                    if self.voice_enabled_var.get() and self.voice.enabled:
                        threading.Thread(
                            target=self.voice.speak, args=(payload,), daemon=True
                        ).start()

                elif event == "assistant_error":
                    self.stop_typing_animation()
                    if self.current_assistant_bubble:
                        self.current_assistant_bubble.set_text(f"⚠ Error: {payload}")
                    self.messages.append({"role": "assistant", "content": f"Error: {payload}"})
                    self.current_assistant_bubble = None
                    self.is_generating            = False
                    self.stop_generation          = False
                    self.set_status("Error")

        except queue.Empty:
            pass

        self.root.after(50, self.process_ui_queue)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def set_status(self, text: str):
        self.status_label.config(text=text)

    def set_loaded_state(self, loaded: bool):
        if loaded:
            self.pill.config(text="● READY", bg="#052e1d", fg="#bbf7d0")
            self.subtitle_label.config(text=f"Offline · {self.current_model_repo}")
        else:
            self.pill.config(text="○ LOADING", bg="#3b0000", fg="#fca5a5")
            self.subtitle_label.config(text="Offline · loading…")

    def log_system(self, text: str):
        self.chat_frame.add_bubble(f"⚙ {text}", role="system")

    def on_enter_pressed(self, event):
        self.send()
        return "break"

    def on_voice_toggle(self):
        if not self.voice.enabled and self.voice_enabled_var.get():
            self.voice_enabled_var.set(False)
            messagebox.showinfo("Voice unavailable", "Install pyttsx3 to enable voice.")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = AIChatApp(root)
    root.mainloop()
