#!/usr/bin/env python3
"""Build verses.js (all 700 verses) for the Gita app.

Inputs (download into a folder and pass it as the first argument):
  verse.json    Sanskrit text  - https://raw.githubusercontent.com/gita/gita/main/data/verse.json
                (gita/gita, released into the public domain under the Unlicense)
  verses.jsonl  Sir Edwin Arnold's "The Song Celestial" (1885; Project Gutenberg #2388,
                public domain), aligned verse-by-verse by the OpenArtha project:
                https://raw.githubusercontent.com/rittmang/openartha/main/public/data/gita-edwin-arnold-1.0.0/verses.jsonl
                (alignment metadata CC BY 4.0, https://openartha.rittmang.xyz)

Usage:  python3 scripts/build_verses.py <source-dir> > verses.js
"""
import json
import re
import sys
from pathlib import Path

# Arnold's own chapter titles, from the colophon at the end of each chapter.
CHAPTER_TITLES = {
    1: ("Arjun-Vishad", "The Book of the Distress of Arjuna"),
    2: ("Sankhya-Yog", "The Book of Doctrines"),
    3: ("Karma-Yog", "The Book of Virtue in Work"),
    4: ("Jnana Yog", "The Book of the Religion of Knowledge"),
    5: ("Karmasanyasayog", "The Book of Religion by Renouncing Fruit of Works"),
    6: ("Atmasanyamayog", "The Book of Religion by Self-Restraint"),
    7: ("Vijnanayog", "The Book of Religion by Discernment"),
    8: ("Aksharaparabrahmayog", "The Book of Religion by Devotion to the One Supreme God"),
    9: ("Rajavidyarajaguhyayog", "The Book of Religion by the Kingly Knowledge and the Kingly Mystery"),
    10: ("Vibhuti Yog", "The Book of Religion by the Heavenly Perfections"),
    11: ("Viswarupadarsanam", "The Book of the Manifesting of the One and Manifold"),
    12: ("Bhaktiyog", "The Book of the Religion of Faith"),
    13: ("Kshetrakshetrajnavibhagayog", "The Book of Religion by Separation of Matter and Spirit"),
    14: ("Gunatrayavibhagayog", "The Book of Religion by Separation from the Qualities"),
    15: ("Purushottamapraptiyog", "The Book of Religion by Attaining the Supreme"),
    16: ("Daivasarasaupadwibhagayog", "The Book of the Separateness of the Divine and Undivine"),
    17: ("Sraddhatrayavibhagayog", "The Book of Religion by the Threefold Kinds of Faith"),
    18: ("Mokshasanyasayog", "The Book of Religion by Deliverance and Renunciation"),
}

# ---------- Devanagari -> IAST ----------
VOWELS = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū", "ऋ": "ṛ", "ॠ": "ṝ",
    "ऌ": "ḷ", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
}
MATRAS = {
    "ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū", "ृ": "ṛ", "ॄ": "ṝ", "ॢ": "ḷ",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
}
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ",
    "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "ñ",
    "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "ळ": "ḻ",
    "श": "ś", "ष": "ṣ", "स": "s", "ह": "h",
}
OTHER = {"ं": "ṃ", "ः": "ḥ", "ँ": "m̐", "ऽ": "'", "।": "|", "॥": "||", "ॐ": "oṃ"}
VIRAMA, NUKTA = "्", "़"
DIGITS = {chr(0x966 + i): str(i) for i in range(10)}


def to_iast(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in CONSONANTS:
            out.append(CONSONANTS[ch])
            i += 1
            if i < n and text[i] == NUKTA:
                i += 1
            if i < n and text[i] == VIRAMA:
                i += 1
            elif i < n and text[i] in MATRAS:
                out.append(MATRAS[text[i]])
                i += 1
            else:
                out.append("a")
            continue
        if ch in VOWELS:
            out.append(VOWELS[ch])
        elif ch in OTHER:
            out.append(OTHER[ch])
        elif ch in DIGITS:
            out.append(DIGITS[ch])
        elif ch in MATRAS or ch in (VIRAMA, NUKTA, "‌", "‍"):
            pass  # stray mark; ignore
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# ---------- Sanskrit cleanup ----------
def clean_sanskrit(raw):
    t = raw.replace("​", "").strip()
    t = re.sub(r"।।\s*\d+\.\d+\s*।।", "॥", t)        # trailing verse number marker
    t = t.replace("।।", "॥")
    t = re.sub(r"((?:उ|ु)वाच)(?=\S)", r"\1\n", t)      # 'X उवाच' glued to the verse
    t = re.sub(r"।(?=[^\s॥])", "।\n", t)              # half-verses glued together
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    return "\n".join(lines)


# ---------- Arnold cleanup ----------
def clean_english(raw):
    if not raw:
        return ""
    t = re.sub(r"\s*\[FN#\d+\]", "", raw)
    lines = [re.sub(r"\s{2,}", " ", ln.strip()) for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def main():
    src = Path(sys.argv[1])
    sanskrit = json.loads((src / "verse.json").read_text(encoding="utf-8"))
    arnold = [json.loads(l) for l in (src / "verses.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # gita/gita numbers Chapter 13 with 35 verses (Arjuna's opening question as 13.1).
    # The standard 700-verse numbering (used by the Arnold alignment) has 34, so drop
    # that question and shift the rest down by one.
    sk = {}
    for v in sanskrit:
        ch, vn = v["chapter_number"], v["verse_number"]
        if ch == 13:
            if vn == 1:
                continue
            vn -= 1
        sk[(ch, vn)] = v["text"]

    groups = {}
    for a in arnold:
        groups.setdefault(a["alignment"]["id"], []).append(a["verse"])

    out = []
    for a in sorted(arnold, key=lambda a: (a["chapter"], a["verse"])):
        ch, vn = a["chapter"], a["verse"]
        dev = clean_sanskrit(sk[(ch, vn)])
        eng = clean_english(a.get("content"))
        group = groups[a["alignment"]["id"]]
        entry = {
            "c": ch,
            "v": vn,
            "d": dev,
            "t": to_iast(dev),
            "e": eng,
        }
        if len(group) > 1:
            entry["g"] = [g for g in group]  # verses that share one Arnold passage
        out.append(entry)

    assert len(out) == 700, len(out)
    assert len(sk) == 700, len(sk)

    titles = {c: {"name": n, "title": t} for c, (n, t) in CHAPTER_TITLES.items()}
    sys.stdout.write("// Generated by scripts/build_verses.py — do not edit by hand.\n")
    sys.stdout.write("// Sanskrit: public domain (gita/gita, Unlicense). Romanization: IAST, generated.\n")
    sys.stdout.write("// English: Sir Edwin Arnold, The Song Celestial (1885), public domain\n")
    sys.stdout.write("//   (Project Gutenberg #2388); verse alignment by OpenArtha (CC BY 4.0).\n")
    sys.stdout.write("window.GITA_CHAPTERS = " + json.dumps(titles, ensure_ascii=False) + ";\n")
    sys.stdout.write("window.GITA_VERSES = [\n")
    sys.stdout.write(",\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in out))
    sys.stdout.write("\n];\n")


if __name__ == "__main__":
    main()
