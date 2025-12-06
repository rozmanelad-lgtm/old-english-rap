West Saxon Orthography Converter

West Saxon Orthography Converter is a fan-made / hobbyist–linguistic desktop tool built with PyQt6.
It lets you:

convert English / Old English text into a custom West Saxon–style orthography

run a purely formal morphological annotation

generate pseudo–Old English forms using deterministic rules (no dictionary, no “real” translation)

process full PDF / TXT documents page by page and export the converted text

This is not an academic tool and not a finished product. It’s an experimental playground for Old English nerds. Use at your own risk, and feel free to break it and improve it.

Goals

The main idea of this project is:

to explore what happens if we push Old English orthography, morphology and phonology to the max,

while staying strictly rule-based and deterministic (no hidden AI, no magic translation),

and make it usable in a friendly GUI so anyone can play with it.

It is not trying to be:

a correct historical reconstruction of every form,

a proper Old English translator,

or a substitute for real linguistic scholarship.

Think of it as a fan + linguistics experiment, not as a reliable grammar engine.

Features
1. Multiple conversion modes

The app currently supports five modes:

Practice (simple)
Basic Old English–style orthography:

th → þ (word-initial), ð (elsewhere)

w → ƿ (wynn)

c before front vowels → ċ

g before front vowels → ġ

Linguist (advanced)
Adds more phonological detail:

all rules from Practice

plain g between vowels → ɣ / Ɣ

classic OE diphthongs (ea, eo, ie, ēa, ēo, īe) marked with a combining tie (e͡a, ē͡a, etc.)

Expert (historical/phonological)
For people who like pain:

all rules from Linguist

sc before front vowels → sċ (palatal /ʃ/)

Annotation (morphological)
A purely formal morphological analyzer:

backwards search for known suffixes (e.g. -um, -an, -es, -as, -ende, -nesse) → ENDING

forwards search for common prefixes (ge-, for-, un-, be-, etc.) → PREFIX

everything in between → STEM

compound stems with - are split into parts

output per token, e.g.:
geardagum -> PREFIX{ge-} STEM{ār+dag} ENDING{-um}

It does not understand meaning, it only looks at formal patterns.

Full Grammar Reconstruction
The “maximum madness” mode:
a deterministic, rule-based attempt to make any English word look like a plausible Old English–style form.

Morphological rewrites of common modern suffixes, for example:

-ing → -ung

-ness → -nes

-less → -lēas

-tion / -sion / -ment → -ung

-ly → -līce

-ed → -ode

plural -s → -as (very rough heuristic)

Grapheme mappings inspired by OE:

qu → cw, wh → hw, sh → sc, ch → ċ, ph → f, gh → h

j → ġ, v → f, k → c, x → cs, z → s

Then everything goes through the orthography engine (like an advanced Expert mode) to apply:

ċ, ġ, ƿ, þ/ð, diphthongs with ◌͡, ɣ, etc.

Capitalization is preserved.
The same input word always produces the same output form.

⚠ Important:
This mode does not guarantee correct Old English grammar, syntax or semantics.
It is a deterministic fan-made reconstruction engine, not a real historical grammar model.

File support

Open file…

PDF: loaded page by page (each page → one “chapter” in the export)

TXT: loaded as a single page

Export converted…

exports the current mode’s output to a .txt file (UTF-8)

pages are separated by markers like:

=== Page 1 ===
...
=== Page 2 ===
...

Installation

Requirements (example):

pip install PyQt6 PyPDF2


Then run:

python west_saxon_converter.py

Disclaimer

This is a fan–linguistic project, built with:

limited access to proper Old English grammars and corpora,

a lot of simplifications,

and many hand-written rules.

Because of that:

there WILL be mistakes,

there WILL be inaccuracies in morphology and phonology,

there MAY be bugs, weird edge cases and wrong forms,

nothing here should be taken as authoritative Old English.

If you are a professional linguist, historical philologist, or just know Old English better than this code (which is very likely) — please treat this as an experiment, not as a reference.

Contributing

If you:

notice wrong forms,

want to add better rules,

have ideas for more accurate declensions / conjugations,

or just want to refactor the code,

pull requests and issues are very welcome.

You can:

propose better suffix rules for Full Grammar Reconstruction,

extend the list of prefixes/endings for Annotation mode,

improve the orthography logic,

or plug in real lexical data and grammatical paradigms.

This project exists because someone thought:

“What if I try to push Old English orthography and grammar as far as possible in code, just for fun?”

If you think the same — you’re exactly the right person to hack on it.
