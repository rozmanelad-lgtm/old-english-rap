import sys
import os

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QComboBox,
    QGroupBox,
    QSizePolicy,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt

# Try to import PyPDF2 for PDF support
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


# ---------------------- Core conversion logic (orthography) ---------------------- #

SHORT_VOWELS = "aAeEiIoOuUyYæÆ"
LONG_VOWELS = "āĀēĒīĪōŌūŪȳȲǣǢ"
VOWELS = set(SHORT_VOWELS + LONG_VOWELS)

FRONT_VOWELS = set("eE" "iI" "yY" "æÆ" "ēĒ" "īĪ" "ȳȲ" "ǣǢ")

COMBINING_TIE = "\u0361"


def is_vowel(ch: str) -> bool:
    return ch in VOWELS


def is_front_vowel(ch: str) -> bool:
    return ch in FRONT_VOWELS


def convert_th(text: str) -> str:
    """
    Convert 'th' → thorn/eth.
    Heuristic:
      - word-initial 'th' → þ / Þ
      - otherwise → ð / Ð
    """
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in ("t", "T") and i + 1 < len(text) and text[i + 1] in ("h", "H"):
            prev_char = text[i - 1] if i > 0 else None
            at_word_start = prev_char is None or not prev_char.isalpha()

            is_upper = ch.isupper()
            if at_word_start:
                repl = "Þ" if is_upper else "þ"
            else:
                repl = "Ð" if is_upper else "ð"

            result.append(repl)
            i += 2
            continue
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def convert_c_g_w(text: str, mode: str) -> str:
    """
    - c/C before front vowel (and not in 'sc') → ċ / Ċ
    - g/G before front vowel (except after n in 'ng') → ġ / Ġ
    - in Linguist/Expert/Reconstruction mode: plain g between vowels → ɣ / Ɣ
    - w/W → ƿ / Ƿ
    """
    result = []
    length = len(text)

    mode = mode.lower()

    for i, ch in enumerate(text):
        prev_char = text[i - 1] if i > 0 else ""
        next_char = text[i + 1] if i + 1 < length else ""

        # c -> ċ
        if ch in ("c", "C"):
            new_ch = ch
            if is_front_vowel(next_char) and prev_char not in ("s", "S"):
                new_ch = "ċ" if ch.islower() else "Ċ"
            result.append(new_ch)
            continue

        # g -> ġ / ɣ
        if ch in ("g", "G"):
            new_ch = ch

            # Palatal g -> ġ
            if is_front_vowel(next_char) and not (prev_char.lower() == "n"):
                new_ch = "ġ" if ch.islower() else "Ġ"

            # Linguist & Expert & Reconstruction: velar fricative between vowels -> ɣ / Ɣ
            if mode in ("linguist", "expert", "reconstruction"):
                if new_ch in ("g", "G"):
                    if is_vowel(prev_char) and is_vowel(next_char):
                        new_ch = "ɣ" if ch.islower() else "Ɣ"

            result.append(new_ch)
            continue

        # w -> wynn
        if ch in ("w", "W"):
            new_ch = "ƿ" if ch.islower() else "Ƿ"
            result.append(new_ch)
            continue

        result.append(ch)

    return "".join(result)


def add_diphthong_ties(text: str) -> str:
    """
    Linguist/Expert/Reconstruction mode: add combining tie to classic OE diphthongs:
      ea, eo, ie, ēa, ēo, īe (case-sensitive; mainly lower-case).
    """
    s = text.replace(COMBINING_TIE, "")  # clear existing ties

    # Lowercase variants (long first, then short)
    s = s.replace("ēa", "ē" + COMBINING_TIE + "a")
    s = s.replace("ēo", "ē" + COMBINING_TIE + "o")
    s = s.replace("īe", "ī" + COMBINING_TIE + "e")
    s = s.replace("ea", "e" + COMBINING_TIE + "a")
    s = s.replace("eo", "e" + COMBINING_TIE + "o")
    s = s.replace("ie", "i" + COMBINING_TIE + "e")

    # Uppercase variants
    s = s.replace("ĒA", "Ē" + COMBINING_TIE + "A")
    s = s.replace("ĒO", "Ē" + COMBINING_TIE + "O")
    s = s.replace("ĪE", "Ī" + COMBINING_TIE + "E")
    s = s.replace("EA", "E" + COMBINING_TIE + "A")
    s = s.replace("EO", "E" + COMBINING_TIE + "O")
    s = s.replace("IE", "I" + COMBINING_TIE + "E")

    return s


def expert_enhancements(text: str) -> str:
    """
    Extra transformations for Expert mode:
      - sc / SC + front vowel -> sċ / Sċ + vowel  (palatal /ʃ/)
    """
    result = []
    i = 0
    length = len(text)

    while i < length:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < length else ""
        nxt2 = text[i + 2] if i + 2 < length else ""

        # sc + front vowel -> sċ
        if ch in ("s", "S") and nxt in ("c", "C") and is_front_vowel(nxt2):
            result.append(ch)  # keep s/S
            result.append("ċ" if nxt.islower() else "Ċ")
            i += 2
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def convert_to_west_saxon(text: str, mode: str = "practice") -> str:
    """
    High-level orthographic conversion (Practice / Linguist / Expert / Reconstruction).
    For 'annotation' mode – use separate pipeline.
    """
    if not text:
        return ""

    mode = mode.lower()
    if mode not in ("practice", "linguist", "expert", "reconstruction"):
        mode = "practice"

    step1 = convert_th(text)
    step2 = convert_c_g_w(step1, mode)

    if mode in ("linguist", "expert", "reconstruction"):
        step2 = add_diphthong_ties(step2)

    if mode == "expert":
        step2 = expert_enhancements(step2)

    return step2


# ---------------------- Morphological Annotation Mode ---------------------- #

ENDINGS = [
    "unga", "nesse", "ende",
    "ode", "est", "ath", "að",
    "um", "an", "on", "en", "as", "es", "st", "de",
    "a", "e", "u",
]

PREFIXES = [
    "ge", "for", "un", "be", "ā", "oð", "æt", "of", "on", "ymb", "to",
]


def annotate_word(token: str) -> str:
    if not any(ch.isalpha() for ch in token):
        return token

    core = token
    lower_core = core.lower()

    # 1. ending
    ending = ""
    stem_candidate = core
    for suf in sorted(ENDINGS, key=len, reverse=True):
        if len(lower_core) > len(suf) and lower_core.endswith(suf):
            ending = core[-len(suf):]
            stem_candidate = core[:-len(suf)]
            break

    # 2. prefix
    prefix = ""
    stem = stem_candidate
    lower_stem = stem_candidate.lower()
    for pref in sorted(PREFIXES, key=len, reverse=True):
        if lower_stem.startswith(pref) and len(stem_candidate) > len(pref) + 1:
            prefix = stem_candidate[: len(pref)]
            stem = stem_candidate[len(pref):]
            break

    # 3. compound splits
    stem_parts = [p for p in stem.replace("--", "-").split("-") if p] if stem else []

    segments = []

    if prefix:
        segments.append(f"PREFIX{{{prefix}-}}")

    if stem_parts:
        segments.append(f"STEM{{{'+'.join(stem_parts)}}}")
    elif stem:
        segments.append(f"STEM{{{stem}}}")
    else:
        if not (prefix or ending):
            segments.append(f"STEM{{{core}}}")

    if ending:
        segments.append(f"ENDING{{-{ending}}}")

    if not segments:
        segments.append(f"STEM{{{core}}}")

    return f"{token} -> " + " ".join(segments)


def annotate_text(text: str) -> str:
    if not text.strip():
        return ""
    tokens = text.split()
    lines = [annotate_word(tok) for tok in tokens]
    return "\n".join(lines)


# ---------------------- Full Grammar Reconstruction Mode ---------------------- #

def reconstruction_morphology(word: str) -> str:
    """
    Deterministic pseudo-OE morphological rewrite of a modern-looking English word:
    -ing -> -ung, -ness -> -nes, -tion/-sion -> -ung, -ly -> -līce, -ed -> -ode, plural -s -> -as, etc.
    """
    w = word
    lw = w.lower()

    def repl_suffix(old: str, new: str) -> bool:
        nonlocal w, lw
        if lw.endswith(old) and len(lw) > len(old) + 1:
            w = w[:-len(old)] + new
            lw = w.lower()
            return True
        return False

    # Order: long/complex first
    # Adverb / adjective
    if repl_suffix("lessness", "lēasnes"):
        pass
    elif repl_suffix("lessnesses", "lēasnessas"):
        pass
    elif repl_suffix("lessness", "lēasnes"):
        pass
    elif repl_suffix("less", "lēas"):
        pass
    elif repl_suffix("fulness", "fullnes"):
        pass
    elif repl_suffix("fulnesses", "fullnessas"):
        pass
    elif repl_suffix("fulness", "fullnes"):
        pass
    elif repl_suffix("full", "full"):
        pass
    elif repl_suffix("nesses", "nessas"):
        pass
    elif repl_suffix("ness", "nes"):
        pass
    elif repl_suffix("ment", "ung"):
        pass
    elif repl_suffix("tion", "ung"):
        pass
    elif repl_suffix("sion", "ung"):
        pass
    elif repl_suffix("ings", "ungas"):
        pass
    elif repl_suffix("ing", "ung"):
        pass
    elif repl_suffix("ly", "līce"):
        pass
    elif repl_suffix("ied", "ode"):
        pass
    elif repl_suffix("ed", "ode"):
        pass
    else:
        # plural -s -> -as (rough heuristic)
        if lw.endswith("s") and not lw.endswith(("ss", "us", "is")) and len(lw) > 2:
            w = w[:-1] + "as"
            lw = w.lower()

    return w


def reconstruct_word_core(word: str) -> str:
    """
    Deterministic pseudo-OE "full grammar reconstruction" of a word:
    1) Morphological rewrite (suffixes)
    2) Grapheme-level OE-like mappings
    3) Pass through orthography engine in 'reconstruction' mode.
    """
    # 1. morphology
    base = reconstruction_morphology(word.lower())

    # 2. grapheme rewrites
    w = base
    out = []
    i = 0
    while i < len(w):
        ch = w[i]
        nxt = w[i + 1] if i + 1 < len(w) else ""

        # digraphs / clusters
        if w.startswith("qu", i):
            out.append("cw")
            i += 2
            continue
        if w.startswith("wh", i):
            out.append("hw")
            i += 2
            continue
        if w.startswith("sh", i):
            out.append("sc")
            i += 2
            continue
        if w.startswith("ch", i):
            out.append("ċ")
            i += 2
            continue
        if w.startswith("ph", i):
            out.append("f")
            i += 2
            continue
        if w.startswith("gh", i):
            out.append("h")
            i += 2
            continue
        if w.startswith("ck", i):
            out.append("c")
            i += 2
            continue

        # single letters
        if ch == "j":
            out.append("ġ")
        elif ch == "v":
            out.append("f")
        elif ch == "q":
            out.append("cw")
        elif ch == "k":
            out.append("c")
        elif ch == "x":
            out.append("cs")
        elif ch == "z":
            out.append("s")
        else:
            out.append(ch)
        i += 1

    base2 = "".join(out)

    # 3. pass through orthography engine
    refined = convert_to_west_saxon(base2, mode="reconstruction")
    return refined


def apply_casing(original: str, reconstructed: str) -> str:
    if not original:
        return reconstructed
    if original.isupper():
        return reconstructed.upper()
    if original[0].isupper() and original[1:].islower():
        return reconstructed[0].upper() + reconstructed[1:]
    return reconstructed


def reconstruct_text(text: str) -> str:
    """
    Apply reconstruct_word_core to all alphabetic tokens,
    preserving punctuation and spacing.
    """
    if not text:
        return ""

    result = []
    current = []
    in_word = False

    def flush():
        nonlocal current, in_word
        if not current:
            return
        token = "".join(current)
        if in_word:
            recon = reconstruct_word_core(token)
            recon = apply_casing(token, recon)
            result.append(recon)
        else:
            result.append(token)
        current = []
        in_word = False

    for ch in text:
        if ch.isalpha():
            if not in_word and current:
                flush()
            in_word = True
            current.append(ch)
        else:
            if in_word:
                flush()
            in_word = False
            current.append(ch)

    flush()
    return "".join(result)


# ---------------------- HELP & ABOUT dialogs ---------------------- #

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help – West Saxon Orthography Converter")
        self.setMinimumSize(600, 540)

        layout = QVBoxLayout()
        self.setLayout(layout)

        text = QLabel()
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        text.setText(
            """
            <h2>West Saxon Orthography Converter – Help</h2>
            <p>This tool converts English / Old English text into a custom West Saxon-style orthography,
            can perform purely formal morphological annotation, and can reconstruct words into a
            pseudo-Old English form using deterministic rules.</p>

            <h3>Modes</h3>
            <ul>
              <li><b>Practice (simple)</b><br>
                  Orthographic conversion:
                  <ul>
                    <li><code>th</code> → <code>þ</code> (word-initial), <code>ð</code> (elsewhere)</li>
                    <li><code>w</code> → <code>ƿ</code> (wynn)</li>
                    <li><code>c</code> before front vowels → <code>ċ</code></li>
                    <li><code>g</code> before front vowels → <code>ġ</code></li>
                  </ul>
              </li>

              <li><b>Linguist (advanced)</b><br>
                  Adds phonological detail:
                  <ul>
                    <li>All rules from Practice mode</li>
                    <li>Plain <code>g</code> between vowels → <code>ɣ</code> (velar fricative)</li>
                    <li>Diphthongs <code>ea, eo, ie, ēa, ēo, īe</code> get a combining tie:
                        <code>e͡a, ē͡a, e͡o, i͡e, ī͡e</code>, etc.</li>
                  </ul>
              </li>

              <li><b>Expert (historical/phonological)</b><br>
                  For hardcore historical phonology:
                  <ul>
                    <li>All rules from Linguist mode</li>
                    <li><code>sc</code> before front vowels → <code>sċ</code> (palatal /ʃ/)</li>
                  </ul>
              </li>

              <li><b>Annotation (morphological)</b><br>
                  Purely formal, rule-based morphological segmentation:
                  <ul>
                    <li>Backwards search for known endings → <code>ENDING</code></li>
                    <li>Forwards search for prefixes → <code>PREFIX</code></li>
                    <li>Everything in between → <code>STEM</code></li>
                    <li>Compound stems with <code>-</code> are split into parts.</li>
                  </ul>
                  Output is one token per line:
                  <pre>geardagum -> PREFIX{ge-} STEM{ār+dag} ENDING{-um}</pre>
              </li>

              <li><b>Full Grammar Reconstruction</b><br>
                  Deterministic per-word pseudo-Old-English “full grammar” reconstruction:
                  <ul>
                    <li>No dictionary and no semantic translation – only formal rules.</li>
                    <li>Morphological rewriting of common English suffixes:
                        <ul>
                          <li><code>-ing → -ung</code>, <code>-ness → -nes</code>, <code>-less → -lēas</code>,</li>
                          <li><code>-tion / -sion / -ment → -ung</code>, <code>-ly → -līce</code>,</li>
                          <li><code>-ed → -ode</code>, plural <code>-s → -as</code> (heuristic)</li>
                        </ul>
                    </li>
                    <li>Grapheme mappings:
                        <code>qu → cw</code>, <code>wh → hw</code>, <code>sh → sc</code>,
                        <code>ch → ċ</code>, <code>ph → f</code>, <code>gh → h</code>,
                        <code>j → ġ</code>, <code>v → f</code>, <code>k → c</code>,
                        <code>x → cs</code>, <code>z → s</code>.</li>
                    <li>The result is passed through the orthography engine (like an advanced Expert mode)
                        for <code>ċ, ġ, ƿ, þ/ð</code>, diphthongs, etc.</li>
                    <li>Capitalization is preserved, and the same input word always produces the same output form.</li>
                  </ul>
              </li>
            </ul>

            <h3>Files</h3>
            <ul>
              <li><b>Open file…</b> can load PDF (page by page) or plain text files.</li>
              <li>PDF pages are preserved as separate pages when exporting.</li>
              <li><b>Export converted…</b> saves a UTF-8 <code>.txt</code> file with page markers:
                  <code>=== Page 1 ===</code>, <code>=== Page 2 ===</code>, etc.</li>
            </ul>

            <p>All processing is rule-based. There is no true automatic translation or full semantic grammar engine.</p>
            """
        )

        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About – West Saxon Orthography Converter")
        self.setMinimumSize(500, 300)

        layout = QVBoxLayout()
        self.setLayout(layout)

        text = QLabel()
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        text.setText(
            """
            <h2>West Saxon Orthography Converter</h2>
            <p>An experimental tool for:</p>
            <ul>
              <li>West Saxon-style orthographic conversion</li>
              <li>Purely formal morphological annotation</li>
              <li>Deterministic pseudo-Old-English “Full Grammar Reconstruction”</li>
            </ul>

            <p>Features:</p>
            <ul>
              <li>Five modes: Practice, Linguist, Expert, Annotation, Full Grammar Reconstruction</li>
              <li>Interactive GUI based on PyQt6</li>
              <li>PDF and TXT input, with per-page export</li>
              <li>Rule-based, fully Unicode, no external dictionary</li>
            </ul>

            <p>Designed both for general users who want to play with Old English orthography
            and for users who care about explicit morphology and phonology.</p>
            """
        )

        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


# ---------------------- PyQt6 GUI ---------------------- #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("West Saxon Orthography Converter")
        self.setMinimumSize(980, 640)

        self.mode = "practice"

        self.loaded_pages_original = []
        self.loaded_source_path = None

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        title_label = QLabel("West Saxon Orthography Converter")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: 600; margin-bottom: 4px;"
        )

        subtitle_label = QLabel(
            "Convert English / Old English text into your custom West Saxon system,\n"
            "run formal morphological annotation, or try Full Grammar Reconstruction."
        )
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: gray; margin-bottom: 12px;")

        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)

        # Top controls
        top_group = QGroupBox("Controls")
        top_layout = QHBoxLayout()
        top_group.setLayout(top_layout)

        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Practice (simple)")
        self.mode_combo.addItem("Linguist (advanced)")
        self.mode_combo.addItem("Expert (historical/phonological)")
        self.mode_combo.addItem("Annotation (morphological)")
        self.mode_combo.addItem("Full Grammar Reconstruction")
        self.mode_combo.setCurrentIndex(0)

        sample_label = QLabel("Sample text:")
        self.sample_combo = QComboBox()
        self.sample_combo.addItem("Insert sample…")
        self.sample_combo.addItem("Beowulf opening (OE-style)")
        self.sample_combo.addItem("Modern English example")

        self.open_button = QPushButton("Open file…")
        self.export_button = QPushButton("Export converted…")

        self.help_button = QPushButton("Help")
        self.about_button = QPushButton("About")

        top_layout.addWidget(mode_label)
        top_layout.addWidget(self.mode_combo)
        top_layout.addSpacing(16)
        top_layout.addWidget(sample_label)
        top_layout.addWidget(self.sample_combo)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.open_button)
        top_layout.addWidget(self.export_button)
        top_layout.addStretch()
        top_layout.addWidget(self.help_button)
        top_layout.addWidget(self.about_button)

        main_layout.addWidget(top_group)

        # Text areas
        io_group = QGroupBox("Text")
        io_layout = QGridLayout()
        io_group.setLayout(io_layout)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Paste or type your text here...")
        self.input_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Converted / annotated text will appear here...")
        self.output_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        io_layout.addWidget(QLabel("Input"), 0, 0)
        io_layout.addWidget(QLabel("Output"), 0, 1)
        io_layout.addWidget(self.input_edit, 1, 0)
        io_layout.addWidget(self.output_edit, 1, 1)

        main_layout.addWidget(io_group, stretch=1)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.convert_button = QPushButton("Convert / Annotate")
        self.copy_button = QPushButton("Copy Output")
        self.clear_button = QPushButton("Clear")

        self.convert_button.setToolTip("Apply selected mode to the input text")
        self.copy_button.setToolTip("Copy the output to clipboard")
        self.clear_button.setToolTip("Clear both input and output")

        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.copy_button)

        main_layout.addLayout(button_layout)

        self.status = self.statusBar()
        self.status.showMessage("Ready – Mode: Practice (simple)")

        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.convert_button.clicked.connect(self.update_output)
        self.copy_button.clicked.connect(self.copy_output)
        self.clear_button.clicked.connect(self.clear_text)
        self.input_edit.textChanged.connect(self.update_output_live)
        self.help_button.clicked.connect(self.open_help)
        self.about_button.clicked.connect(self.open_about)
        self.sample_combo.currentIndexChanged.connect(self.insert_sample)
        self.open_button.clicked.connect(self.open_document)
        self.export_button.clicked.connect(self.export_document)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QGroupBox {
                font-weight: 600;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px 0 4px;
            }
            QTextEdit {
                font-family: 'Consolas', 'Fira Code', 'JetBrains Mono', monospace;
                font-size: 13px;
            }
            QPushButton {
                padding: 6px 14px;
            }
            """
        )

    # ------------- logic -------------

    def on_mode_changed(self, index: int):
        if index == 0:
            self.mode = "practice"
            self.status.showMessage("Mode: Practice (simple)")
        elif index == 1:
            self.mode = "linguist"
            self.status.showMessage("Mode: Linguist (advanced)")
        elif index == 2:
            self.mode = "expert"
            self.status.showMessage("Mode: Expert (historical/phonological)")
        elif index == 3:
            self.mode = "annotation"
            self.status.showMessage("Mode: Annotation (morphological)")
        else:
            self.mode = "reconstruction"
            self.status.showMessage("Mode: Full Grammar Reconstruction")

        if self.loaded_pages_original:
            self.update_output_from_loaded()
        else:
            self.update_output()

    def apply_mode_to_text(self, text: str) -> str:
        if self.mode == "annotation":
            return annotate_text(text)
        elif self.mode == "reconstruction":
            return reconstruct_text(text)
        else:
            return convert_to_west_saxon(text, self.mode)

    def update_output_from_loaded(self):
        if not self.loaded_pages_original:
            self.update_output()
            return

        parts_in = []
        parts_out = []
        multi_page = len(self.loaded_pages_original) > 1

        for idx, page in enumerate(self.loaded_pages_original, start=1):
            header = f"=== Page {idx} ===\n" if multi_page else ""
            parts_in.append(header + (page or ""))
            converted = self.apply_mode_to_text(page or "")
            parts_out.append(header + converted)

        preview_in = "\n\n".join(parts_in)
        preview_out = "\n\n".join(parts_out)

        self.input_edit.blockSignals(True)
        self.input_edit.setPlainText(preview_in)
        self.input_edit.blockSignals(False)

        self.output_edit.blockSignals(True)
        self.output_edit.setPlainText(preview_out)
        self.output_edit.blockSignals(False)

    def update_output(self):
        text = self.input_edit.toPlainText()
        converted = self.apply_mode_to_text(text)
        self.output_edit.blockSignals(True)
        self.output_edit.setPlainText(converted)
        self.output_edit.blockSignals(False)

    def update_output_live(self):
        if self.loaded_pages_original:
            self.loaded_pages_original = []
            self.loaded_source_path = None
        self.update_output()

    def copy_output(self):
        text = self.output_edit.toPlainText()
        if not text:
            self.status.showMessage("Nothing to copy")
            return
        QApplication.clipboard().setText(text)
        self.status.showMessage("Output copied to clipboard")

    def clear_text(self):
        self.input_edit.blockSignals(True)
        self.output_edit.blockSignals(True)
        self.input_edit.clear()
        self.output_edit.clear()
        self.input_edit.blockSignals(False)
        self.output_edit.blockSignals(False)
        self.loaded_pages_original = []
        self.loaded_source_path = None
        self.status.showMessage("Cleared")

    def open_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def open_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def insert_sample(self, index: int):
        if index == 0:
            return

        self.loaded_pages_original = []
        self.loaded_source_path = None

        if index == 1:
            sample = (
                "Hwæt! We Gardena in geardagum, þeodcyninga, þrym gefrunon,\n"
                "hu ða æþelingas ellen fremedon."
            )
        elif index == 2:
            sample = (
                "This is a simple example text to demonstrate how the converter "
                "changes English into a West Saxon style orthography."
            )
        else:
            sample = ""

        self.input_edit.blockSignals(True)
        self.input_edit.setPlainText(sample)
        self.input_edit.blockSignals(False)

        self.sample_combo.setCurrentIndex(0)
        self.status.showMessage("Sample text inserted")
        self.update_output()

    def open_document(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open document",
            "",
            "PDF files (*.pdf);;Text files (*.txt);;All files (*)",
        )
        if not fname:
            return

        ext = os.path.splitext(fname)[1].lower()
        pages = []

        if ext == ".pdf":
            if PyPDF2 is None:
                self.status.showMessage("PyPDF2 not installed – cannot open PDF.")
                return
            try:
                with open(fname, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        txt = page.extract_text() or ""
                        pages.append(txt)
            except Exception as e:
                self.status.showMessage(f"Error reading PDF: {e}")
                return
        else:
            try:
                with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                pages = [content]
            except Exception as e:
                self.status.showMessage(f"Error reading file: {e}")
                return

        self.loaded_pages_original = pages
        self.loaded_source_path = fname

        self.status.showMessage(
            f"Loaded {len(pages)} page(s) from '{os.path.basename(fname)}'"
        )

        self.update_output_from_loaded()

    def export_document(self):
        if not self.loaded_pages_original:
            self.status.showMessage("No loaded document to export.")
            return

        base_name = "converted.txt"
        if self.loaded_source_path:
            root = os.path.splitext(os.path.basename(self.loaded_source_path))[0]
            if self.mode == "annotation":
                suffix = "_annotated"
            elif self.mode == "reconstruction":
                suffix = "_fullgrammar"
            else:
                suffix = "_converted"
            base_name = f"{root}{suffix}.txt"

        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Save output",
            base_name,
            "Text files (*.txt);;All files (*)",
        )
        if not fname:
            return

        parts = []
        multi_page = len(self.loaded_pages_original) > 1

        for idx, page in enumerate(self.loaded_pages_original, start=1):
            header = f"=== Page {idx} ===\n" if multi_page else ""
            converted = self.apply_mode_to_text(page or "")
            block = header + converted.strip() + "\n"
            parts.append(block)

        full_text = "\n".join(parts)

        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(full_text)
        except Exception as e:
            self.status.showMessage(f"Error saving file: {e}")
            return

        self.status.showMessage(f"Output saved to '{os.path.basename(fname)}'")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
