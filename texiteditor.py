#!/usr/bin/env python3
# TexitEditor - A modern text editor with a retro vibe
# Author: almamun80git + Copilot
# License: MIT

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

try:
    from pygments import lex
    from pygments.lexers import guess_lexer_for_filename, TextLexer
    from pygments.token import Token
except Exception:
    # Graceful message for missing dependency
    lex = None
    guess_lexer_for_filename = None
    TextLexer = None
    Token = None


APP_NAME = "TexitEditor"
APP_VERSION = "1.0.0"
DEFAULT_AUTOSAVE_SECS = 10
SETTINGS_DIR = Path.home() / ".texiteditor"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


DEFAULT_SETTINGS = {
    "theme": "blue",
    "font_family": "Fira Code",
    "font_size": 12,
    "show_line_numbers": True,
    "autosave_enabled": True,
    "autosave_secs": DEFAULT_AUTOSAVE_SECS,
}

THEMES = {
    "blue": {
        "name": "Blue",
        "bg": "#0d1b2a",
        "fg": "#e0e1dd",
        "gutter_bg": "#1b263b",
        "gutter_fg": "#9fb0c1",
        "caret": "#e0e1dd",
        "select_bg": "#2f3e57",
        "select_fg": "#ffffff",
        "accent": "#415a77",
        "token": {
            "kw": "#89b4fa",
            "builtin": "#89dceb",
            "str": "#a6e3a1",
            "num": "#fab387",
            "com": "#6c7a89",
            "op": "#f38ba8",
            "func": "#f9e2af",
            "cls": "#cba6f7",
            "punc": "#cdd6f4",
            "text": "#e0e1dd",
        },
    },
    "green": {
        "name": "Green",
        "bg": "#0f1f1a",
        "fg": "#e6f4ea",
        "gutter_bg": "#1a3028",
        "gutter_fg": "#a7cdb9",
        "caret": "#e6f4ea",
        "select_bg": "#24463b",
        "select_fg": "#ffffff",
        "accent": "#2f5d50",
        "token": {
            "kw": "#7bd389",
            "builtin": "#7ad3c1",
            "str": "#b9f6ca",
            "num": "#ffd59e",
            "com": "#6c8f80",
            "op": "#ff8a80",
            "func": "#fff59d",
            "cls": "#b39ddb",
            "punc": "#dcedc8",
            "text": "#e6f4ea",
        },
    },
    "purple": {
        "name": "Purple",
        "bg": "#1b1325",
        "fg": "#f1e6ff",
        "gutter_bg": "#2a1f39",
        "gutter_fg": "#c8b5e6",
        "caret": "#f1e6ff",
        "select_bg": "#3a2c4f",
        "select_fg": "#ffffff",
        "accent": "#5d3f79",
        "token": {
            "kw": "#c7a0ff",
            "builtin": "#a0d7ff",
            "str": "#b5ffa0",
            "num": "#ffc997",
            "com": "#8f84a6",
            "op": "#ff9ec7",
            "func": "#ffe39e",
            "cls": "#d2a0ff",
            "punc": "#e8dbff",
            "text": "#f1e6ff",
        },
    },
}


def ensure_settings_dir():
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> Dict[str, Any]:
    ensure_settings_dir()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # merge defaults
                merged = {**DEFAULT_SETTINGS, **data}
                return merged
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]):
    ensure_settings_dir()
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


class TextLineNumbers(tk.Canvas):
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.text_widget.bind("<<Change>>", self._on_change)
        self.text_widget.bind("<Configure>", self._on_change)
        self.text_widget.bind("<MouseWheel>", self._on_change)
        self.text_widget.bind("<Button-4>", self._on_change)  # Linux scroll up
        self.text_widget.bind("<Button-5>", self._on_change)  # Linux scroll down

    def _on_change(self, event=None):
        self.redraw()

    def redraw(self):
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(4, y, anchor="nw", text=linenum, font=self.text_widget["font"], fill=self.cget("fg"))
            i = self.text_widget.index(f"{i}+1line")


class CustomText(tk.Text):
    # Text widget that generates <<Change>> virtual event
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, command, *args):
        # let actual widget perform the requested action
        try:
            result = self.tk.call(self._orig, command, *args)
        except tk.TclError as e:
            raise e
        # generate an event if something was added or deleted, or scroll, or cursor moved
        if command in ("insert", "delete", "replace") or \
           command in ("yview", "scroll") or \
           command == "mark" and args[0] == "set" and args[1] == "insert":
            self.event_generate("<<Change>>", when="tail")
        return result


class FindReplaceDialog(tk.Toplevel):
    def __init__(self, master, text: tk.Text):
        super().__init__(master)
        self.title("Find & Replace")
        self.transient(master)
        self.text = text
        self.resizable(False, False)

        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.regex_var = tk.BooleanVar(value=False)
        self.case_var = tk.BooleanVar(value=False)

        frm = ttk.Frame(self)
        frm.pack(padx=10, pady=10, fill="x")

        ttk.Label(frm, text="Find:").grid(row=0, column=0, sticky="w")
        e_find = ttk.Entry(frm, textvariable=self.find_var, width=40)
        e_find.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(6, 0))
        e_find.focus_set()

        ttk.Label(frm, text="Replace:").grid(row=1, column=0, sticky="w")
        e_replace = ttk.Entry(frm, textvariable=self.replace_var, width=40)
        e_replace.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 0))

        ttk.Checkbutton(frm, text="Regex", variable=self.regex_var).grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Checkbutton(frm, text="Match case", variable=self.case_var).grid(row=2, column=2, sticky="w", pady=(6, 0))

        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky="e")

        ttk.Button(btn_frm, text="Find Next", command=self.find_next).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frm, text="Replace", command=self.replace_one).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frm, text="Replace All", command=self.replace_all).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frm, text="Close", command=self.destroy).grid(row=0, column=3, padx=4)

        self.bind("<Return>", lambda e: self.find_next())

    def _search(self, start="insert"):
        import re
        needle = self.find_var.get()
        if not needle:
            return None
        flags = 0 if self.case_var.get() else re.IGNORECASE
        if self.regex_var.get():
            pattern = re.compile(needle, flags)
        else:
            pattern = re.compile(re.escape(needle), flags)

        text = self.text.get("1.0", "end-1c")
        start_idx = self.text.index(start)
        start_index = self._index_to_int(start_idx, text)
        match = pattern.search(text, pos=start_index + 1)
        if not match:
            # wrap search
            match = pattern.search(text, pos=0)
        if not match:
            return None
        return self._int_to_index(match.start()), self._int_to_index(match.end())

    def _index_to_int(self, index: str, text: str) -> int:
        # Convert Tk index to absolute int offset
        line, col = map(int, index.split("."))
        lines = text.splitlines(True)  # keepending
        pos = sum(len(lines[i]) for i in range(min(line - 1, len(lines))))
        pos += col
        return pos

    def _int_to_index(self, pos: int) -> str:
        # Convert absolute int offset to Tk index
        text = self.text.get("1.0", "end-1c")
        if pos <= 0:
            return "1.0"
        if pos >= len(text):
            last_line = len(text.splitlines())
            last_col = len(text.splitlines()[-1]) if last_line else 0
            return f"{max(1,last_line)}.{last_col}"
        line = 1
        col = 0
        for ch in text:
            if pos == 0:
                break
            if ch == "\n":
                line += 1
                col = 0
            else:
                col += 1
            pos -= 1
        return f"{line}.{col}"

    def find_next(self):
        res = self._search(start="insert")
        if res:
            start, end = res
            self.text.tag_remove("sel", "1.0", "end")
            self.text.tag_add("sel", start, end)
            self.text.mark_set("insert", end)
            self.text.see(start)

    def replace_one(self):
        if self.text.tag_ranges("sel"):
            self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", self.replace_var.get())
        else:
            self.find_next()

    def replace_all(self):
        import re
        needle = self.find_var.get()
        repl = self.replace_var.get()
        if not needle:
            return
        text = self.text.get("1.0", "end-1c")
        flags = 0 if self.case_var.get() else re.IGNORECASE
        if self.regex_var.get():
            pattern = re.compile(needle, flags)
        else:
            pattern = re.compile(re.escape(needle), flags)
        new_text = pattern.sub(repl, text)
        if new_text != text:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", new_text)


class FontDialog(tk.Toplevel):
    def __init__(self, master, current_family, current_size):
        super().__init__(master)
        self.title("Font")
        self.resizable(False, False)
        self.selected_family = tk.StringVar(value=current_family)
        self.selected_size = tk.IntVar(value=current_size)

        frm = ttk.Frame(self)
        frm.pack(padx=10, pady=10, fill="both", expand=True)

        fam_frame = ttk.LabelFrame(frm, text="Font Family")
        fam_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        size_frame = ttk.LabelFrame(frm, text="Size")
        size_frame.grid(row=0, column=1, sticky="nsew")

        fam_list = tk.Listbox(fam_frame, height=12, exportselection=False)
        fam_list.pack(fill="both", expand=True)
        families = sorted(set(tkfont.families()))
        for f in families:
            fam_list.insert("end", f)
        if current_family in families:
            idx = families.index(current_family)
            fam_list.selection_set(idx)
            fam_list.see(idx)

        def on_select_family(evt=None):
            sel = fam_list.curselection()
            if sel:
                self.selected_family.set(families[sel[0]])

        fam_list.bind("<<ListboxSelect>>", on_select_family)

        size_list = tk.Listbox(size_frame, height=12, exportselection=False)
        size_list.pack(fill="both", expand=True)
        sizes = [8,9,10,11,12,13,14,16,18,20,22,24,28,32,36]
        for s in sizes:
            size_list.insert("end", s)
        if current_size in sizes:
            idx = sizes.index(current_size)
            size_list.selection_set(idx)
            size_list.see(idx)

        def on_select_size(evt=None):
            sel = size_list.curselection()
            if sel:
                self.selected_size.set(sizes[sel[0]])

        size_list.bind("<<ListboxSelect>>", on_select_size)

        btns = ttk.Frame(frm)
        btns.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="OK", command=self._ok).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=4)

        self.grab_set()
        self.wait_visibility()
        self.focus()

    def _ok(self):
        self.destroy()


class EditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME}")
        self.root.geometry("1024x700")
        self.file_path: Optional[Path] = None
        self.dirty = False
        self.settings = load_settings()
        self.theme_key = self.settings.get("theme", "blue")
        self.theme = THEMES.get(self.theme_key, THEMES["blue"])

        # Configure styles
        self.style = ttk.Style(self.root)
        self._set_ttk_theme()

        # Main containers
        self._create_menu()
        self._create_toolbar()
        self._create_editor()
        self._create_statusbar()

        # Apply theme and font
        self.font_family = self.settings.get("font_family", DEFAULT_SETTINGS["font_family"])
        self.font_size = int(self.settings.get("font_size", DEFAULT_SETTINGS["font_size"]))
        self.text_font = tkfont.Font(family=self.font_family, size=self.font_size)
        self.text.configure(font=self.text_font, insertwidth=2, undo=True, maxundo=-1, autoseparators=True)

        # Line numbers initial visibility
        self.show_line_numbers = bool(self.settings.get("show_line_numbers", True))
        self._toggle_line_numbers(force_value=self.show_line_numbers)

        # Bindings
        self._bind_shortcuts()

        # Syntax highlighting debounce
        self._highlight_after_id = None
        self._autosave_after_id = None

        # Setup tags and theme
        self.apply_theme()

        # Autosave
        if self.settings.get("autosave_enabled", True):
            self.schedule_autosave()

    # UI creation
    def _create_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Alt+F4", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.text.event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find & Replace...", accelerator="Ctrl+F", command=self.open_find_replace)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label="Line Numbers", onvalue=True, offvalue=False,
                                  variable=tk.BooleanVar(value=self.settings.get("show_line_numbers", True)),
                                  command=self.toggle_line_numbers)
        menubar.add_cascade(label="View", menu=view_menu)

        format_menu = tk.Menu(menubar, tearoff=0)
        format_menu.add_command(label="Font...", command=self.change_font)
        theme_menu = tk.Menu(format_menu, tearoff=0)
        for key, th in THEMES.items():
            theme_menu.add_command(label=th["name"], command=lambda k=key: self.set_theme(k))
        format_menu.add_cascade(label="Color Scheme", menu=theme_menu)
        menubar.add_cascade(label="Format", menu=format_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_checkbutton(label="Auto-save", command=self.toggle_autosave)
        tools_menu.add_command(label="Auto-save Interval...", command=self.change_autosave_interval)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self._view_menu_ref = view_menu  # keep ref to manage check state

    def _create_toolbar(self):
        tb = ttk.Frame(self.root)
        tb.pack(side="top", fill="x")

        ttk.Button(tb, text="New", command=self.new_file).pack(side="left", padx=(6, 0), pady=4)
        ttk.Button(tb, text="Open", command=self.open_file).pack(side="left", padx=6, pady=4)
        ttk.Button(tb, text="Save", command=self.save_file).pack(side="left", padx=6, pady=4)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)
        ttk.Button(tb, text="Find", command=self.open_find_replace).pack(side="left", padx=6, pady=4)

        self.toolbar = tb

    def _create_editor(self):
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # Line number gutter + text + scrollbar
        self.text_frame = ttk.Frame(main)
        self.text_frame.pack(fill="both", expand=True)

        self.v_scroll = ttk.Scrollbar(self.text_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.h_scroll = ttk.Scrollbar(self.text_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")

        self.text = CustomText(
            self.text_frame,
            wrap="none",
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
            tabs=("1c"),
            insertbackground=self.theme["caret"],
            spacing1=2,
            spacing3=2,
            padx=8,
            pady=6,
            borderwidth=0,
            highlightthickness=0,
        )
        self.text.pack(side="right", fill="both", expand=True)
        self.v_scroll.config(command=self.text.yview)
        self.h_scroll.config(command=self.text.xview)

        self.linenumbers = TextLineNumbers(self.text_frame, self.text, width=48)
        self.linenumbers.pack(side="left", fill="y")

        # Bind modified
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<<Change>>", self._on_text_changed)
        self.text.bind("<KeyRelease>", self._schedule_highlight)
        self.text.bind("<ButtonRelease>", self._update_status_caret)

    def _create_statusbar(self):
        sb = ttk.Frame(self.root)
        sb.pack(side="bottom", fill="x")
        self.status_label = ttk.Label(sb, text="Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=6)
        self.caret_label = ttk.Label(sb, text="Ln 1, Col 1", anchor="e", width=16)
        self.caret_label.pack(side="right", padx=6)

    def _set_ttk_theme(self):
        # Try to use 'clam' for a modern neutral base
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

    # Theme, fonts, tags
    def apply_theme(self):
        th = self.theme
        # Text widget colors
        self.text.configure(
            background=th["bg"],
            foreground=th["fg"],
            insertbackground=th["caret"],
            selectbackground=th["select_bg"],
            selectforeground=th["select_fg"],
        )
        # Line number colors
        self.linenumbers.configure(
            background=th["gutter_bg"]
        )
        self.linenumbers.configure(fg=th["gutter_fg"])

        # Toolbar and statusbar background approximations via ttk style maps
        self.style.configure("TFrame", background=th["gutter_bg"])
        self.style.configure("TLabel", background=th["gutter_bg"], foreground=th["fg"])
        self.style.configure("TButton", background=th["gutter_bg"])
        self.style.configure("TSeparator", background=th["gutter_bg"])
        self.style.map("TButton", background=[("active", th["accent"])])

        # Configure syntax tags
        self._configure_syntax_tags()

        # Redraw
        self.linenumbers.redraw()
        self._schedule_highlight()

    def _configure_syntax_tags(self):
        token_colors = self.theme["token"]

        def conf(tag, fg=None, bold=False, italic=False):
            options = {}
            if fg:
                options["foreground"] = fg
            if bold or italic:
                # configure font variant
                base = tkfont.Font(font=self.text_font)
                base.configure(weight=("bold" if bold else "normal"), slant=("italic" if italic else "roman"))
                options["font"] = base
            self.text.tag_configure(tag, **options)

        conf("tok-kw", token_colors["kw"], bold=True)
        conf("tok-builtin", token_colors["builtin"])
        conf("tok-str", token_colors["str"])
        conf("tok-num", token_colors["num"])
        conf("tok-com", token_colors["com"], italic=True)
        conf("tok-op", token_colors["op"])
        conf("tok-func", token_colors["func"])
        conf("tok-cls", token_colors["cls"])
        conf("tok-punc", token_colors["punc"])
        conf("tok-text", token_colors["text"])

    # Events and handlers
    def _on_text_modified(self, event=None):
        self.text.edit_modified(0)
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self._update_status_caret()

    def _on_text_changed(self, event=None):
        self.linenumbers.redraw()
        self._update_status_caret()

    def _update_status_caret(self, event=None):
        idx = self.text.index("insert")
        line, col = map(int, idx.split("."))
        self.caret_label.config(text=f"Ln {line}, Col {col + 1}")

    def _schedule_highlight(self, event=None):
        if self._highlight_after_id:
            self.root.after_cancel(self._highlight_after_id)
        self._highlight_after_id = self.root.after(250, self._highlight_now)

    # Syntax highlighting
    def _get_lexer(self):
        if lex is None:
            return None
        text = self.text.get("1.0", "end-1c")
        filename = str(self.file_path) if self.file_path else "untitled.txt"
        try:
            lexer = guess_lexer_for_filename(filename, text)
        except Exception:
            lexer = TextLexer()
        return lexer

    def _clear_syntax_tags(self):
        for tag in ("tok-kw","tok-builtin","tok-str","tok-num","tok-com","tok-op","tok-func","tok-cls","tok-punc","tok-text"):
            self.text.tag_remove(tag, "1.0", "end")

    def _highlight_now(self):
        self._highlight_after_id = None
        if lex is None:
            # Pygments not installed, skip highlighting
            return

        self._clear_syntax_tags()
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            return

        lexer = self._get_lexer()
        if lexer is None:
            return

        # Token mapping
        def tag_for(toktype):
            if toktype in Token.Keyword:
                return "tok-kw"
            if toktype in Token.Name.Builtin:
                return "tok-builtin"
            if toktype in Token.Literal.String:
                return "tok-str"
            if toktype in Token.Literal.Number:
                return "tok-num"
            if toktype in Token.Comment:
                return "tok-com"
            if toktype in Token.Operator:
                return "tok-op"
            if toktype in Token.Punctuation:
                return "tok-punc"
            if toktype in Token.Name.Function:
                return "tok-func"
            if toktype in Token.Name.Class:
                return "tok-cls"
            return "tok-text"

        # Apply tags by walking text via index math
        index = "1.0"
        pos = 0
        for toktype, value in lex(content, lexer):
            length = len(value)
            if length == 0:
                continue
            # Compute start and end indexes
            start_index = self._int_to_index(pos, content)
            end_index = self._int_to_index(pos + length, content)
            self.text.tag_add(tag_for(toktype), start_index, end_index)
            pos += length

    def _int_to_index(self, pos: int, text: str) -> str:
        if pos <= 0:
            return "1.0"
        if pos >= len(text):
            lines = text.splitlines()
            if not lines:
                return "1.0"
            return f"{len(lines)}.{len(lines[-1])}"
        line = 1
        col = 0
        for ch in text:
            if pos == 0:
                break
            if ch == "\n":
                line += 1
                col = 0
            else:
                col += 1
            pos -= 1
        return f"{line}.{col}"

    # File operations
    def new_file(self, event=None):
        if not self._maybe_save_changes():
            return
        self.text.delete("1.0", "end")
        self.file_path = None
        self.dirty = False
        self._update_title()
        self._schedule_highlight()

    def open_file(self, event=None):
        if not self._maybe_save_changes():
            return
        filetypes = [
            ("All Files", "*.*"),
            ("Text Files", "*.txt"),
            ("Python", "*.py"),
            ("JavaScript", "*.js"),
            ("JSON", "*.json"),
            ("Markdown", "*.md"),
            ("HTML", "*.html;*.htm"),
            ("CSS", "*.css"),
            ("C/C++", "*.c;*.h;*.cpp;*.hpp"),
            ("Java", "*.java"),
        ]
        path = filedialog.askopenfilename(title="Open File", filetypes=filetypes)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", data)
            self.file_path = Path(path)
            self.dirty = False
            self._update_title()
            self._schedule_highlight()
            self.status(f"Opened {self.file_path.name}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Failed to open file:\n{e}")

    def save_file(self, event=None):
        if self.file_path is None:
            return self.save_file_as()
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            self.dirty = False
            self._update_title()
            self.status(f"Saved {self.file_path.name}")
            return True
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Failed to save file:\n{e}")
            return False

    def save_file_as(self, event=None):
        filetypes = [
            ("Text Files", "*.txt"),
            ("All Files", "*.*"),
        ]
        path = filedialog.asksaveasfilename(title="Save As", defaultextension=".txt", filetypes=filetypes)
        if not path:
            return False
        self.file_path = Path(path)
        return self.save_file()

    def _maybe_save_changes(self) -> bool:
        if not self.dirty:
            return True
        resp = messagebox.askyesnocancel(APP_NAME, "You have unsaved changes. Save now?")
        if resp is None:
            return False
        if resp:
            return bool(self.save_file())
        return True

    # Autosave
    def schedule_autosave(self):
        if self._autosave_after_id:
            self.root.after_cancel(self._autosave_after_id)
        secs = int(self.settings.get("autosave_secs", DEFAULT_AUTOSAVE_SECS))
        self._autosave_after_id = self.root.after(secs * 1000, self._autosave_tick)

    def _autosave_tick(self):
        self._autosave_after_id = None
        if self.settings.get("autosave_enabled", True):
            try:
                if self.file_path:
                    # Save directly to file to prevent data loss
                    if self.dirty:
                        self.save_file()
                else:
                    # Save to temp
                    tmp_dir = Path(tempfile.gettempdir()) / "texiteditor_autosave"
                    tmp_dir.mkdir(exist_ok=True)
                    tmp_file = tmp_dir / f"untitled_{int(time.time())}.txt"
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        f.write(self.text.get("1.0", "end-1c"))
                self.status("Auto-saved")
            except Exception:
                pass
            finally:
                self.schedule_autosave()

    def toggle_autosave(self):
        enabled = not self.settings.get("autosave_enabled", True)
        self.settings["autosave_enabled"] = enabled
        save_settings(self.settings)
        if enabled:
            self.schedule_autosave()
            self.status("Auto-save enabled")
        else:
            if self._autosave_after_id:
                self.root.after_cancel(self._autosave_after_id)
                self._autosave_after_id = None
            self.status("Auto-save disabled")

    def change_autosave_interval(self):
        from tkinter.simpledialog import askinteger
        secs = askinteger("Auto-save Interval", "Seconds between auto-saves (5-300):", minvalue=5, maxvalue=300,
                          initialvalue=int(self.settings.get("autosave_secs", DEFAULT_AUTOSAVE_SECS)))
        if secs:
            self.settings["autosave_secs"] = int(secs)
            save_settings(self.settings)
            if self.settings.get("autosave_enabled", True):
                self.schedule_autosave()
            self.status(f"Auto-save interval set to {secs}s")

    # View toggles
    def toggle_line_numbers(self):
        self._toggle_line_numbers(force_value=not self.show_line_numbers)

    def _toggle_line_numbers(self, force_value: Optional[bool] = None):
        val = self.show_line_numbers if force_value is None else force_value
        self.show_line_numbers = val
        if self.show_line_numbers:
            self.linenumbers.pack(side="left", fill="y")
        else:
            self.linenumbers.pack_forget()
        self.settings["show_line_numbers"] = self.show_line_numbers
        save_settings(self.settings)

    # Font and theme
    def change_font(self):
        dlg = FontDialog(self.root, self.font_family, self.font_size)
        self.root.wait_window(dlg)
        # Apply selection
        fam = dlg.selected_family.get()
        size = dlg.selected_size.get()
        if fam and size:
            self.font_family = fam
            self.font_size = int(size)
            self.text_font.configure(family=self.font_family, size=self.font_size)
            self._configure_syntax_tags()
            self.settings["font_family"] = self.font_family
            self.settings["font_size"] = self.font_size
            save_settings(self.settings)

    def set_theme(self, key: str):
        if key not in THEMES:
            return
        self.theme_key = key
        self.theme = THEMES[key]
        self.apply_theme()
        self.settings["theme"] = key
        save_settings(self.settings)

    # Find & Replace
    def open_find_replace(self, event=None):
        FindReplaceDialog(self.root, self.text)

    # Helpers
    def _update_title(self):
        name = self.file_path.name if self.file_path else "Untitled"
        mark = "*" if self.dirty else ""
        self.root.title(f"{name}{mark} - {APP_NAME}")

    def status(self, text: str):
        self.status_label.config(text=text)
        # reset after a while
        self.root.after(3000, lambda: self.status_label.config(text="Ready"))

    def about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\nA modern text editor with a retro vibe.\nSyntax highlighting powered by Pygments."
        )

    def _bind_shortcuts(self):
        # File
        self.root.bind("<Control-n>", self.new_file)
        self.root.bind("<Control-o>", self.open_file)
        self.root.bind("<Control-s>", self.save_file)
        self.root.bind("<Control-S>", self.save_file_as)  # Ctrl+Shift+S
        # Edit
        self.root.bind("<Control-f>", self.open_find_replace)
        # Undo/Redo handled by default bindings

    def quit(self):
        if self._maybe_save_changes():
            self.root.destroy()


def main():
    root = tk.Tk()
    app = EditorApp(root)
    if len(sys.argv) > 1:
        try:
            path = sys.argv[1]
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    app.text.insert("1.0", f.read())
                app.file_path = Path(path)
                app._update_title()
                app._schedule_highlight()
        except Exception:
            pass
    root.mainloop()


if __name__ == "__main__":
    main()