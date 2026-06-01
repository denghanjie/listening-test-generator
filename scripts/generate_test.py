#!/usr/bin/env python3
"""
Listening Test Generator
Parses vocabulary CSV files and generates test content, answer sheets, and audio scripts.
"""

import argparse
import csv
import json
import random
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

DEFAULT_CONFIG = {
    "title": "Listening Test",
    "subtitle": "Vocabulary Retention & Listening Recognition",
    "seed": 42,
    "sections": {
        "A": {"name": "Word Dictation", "description": "Listen and write down the words you hear. Each word will be spoken twice.", "count": 40, "points": 1},
        "B": {"name": "Phrase Dictation", "description": "Listen and write down the phrases you hear. Each phrase will be spoken twice.", "count": 20, "points": 2},
        "C": {"name": "Sentence Completion", "description": "Listen to the sentence and fill in the blank with the correct word or phrase.", "count": 20, "points": 0.5},
        "D": {"name": "Multiple Choice", "description": "Listen to the definition and the four options. Choose the correct answer A, B, C, or D.", "count": 15, "points": 0.33}
    }
}


@dataclass
class VocabItem:
    word: str
    meaning: str
    source: str


@dataclass
class TestItem:
    number: int
    section: str
    word: str
    meaning: str
    prompt: str
    answer: str
    audio_text: str
    source: str
    options: List[str] = None

    def __post_init__(self):
        if self.options is None:
            self.options = []


def load_templates(templates_path: Optional[Path]) -> Dict[str, str]:
    """Load sentence or definition templates from a markdown reference file."""
    templates = {}
    if not templates_path or not templates_path.exists():
        return templates
    with open(templates_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                parts = line.split("|", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    templates[key] = val
    return templates


def parse_csv(filepath: Path) -> List[VocabItem]:
    """Parse a vocabulary CSV file. Supports multiple column layouts."""
    items = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0].strip():
                continue
            word = row[0].strip()
            # Skip header-like rows
            if word.lower() in ("word", "单词", "vocabulary", "term", "english"):
                continue
            # Skip non-vocab rows (questions, very long sentences without meaning)
            if word.endswith("?"):
                continue
            meaning = ""
            if len(row) > 1 and row[1].strip():
                meaning = row[1].strip()
            # Skip rows that look like full sentences with no definition
            if not meaning and len(word.split()) > 8:
                continue
            items.append(VocabItem(word=word, meaning=meaning, source=filepath.stem))
    return items


def load_all_vocab(input_dir: Path) -> List[VocabItem]:
    """Load vocabulary from all CSV files in the input directory."""
    all_items = []
    for csv_file in sorted(input_dir.glob("*.csv")):
        items = parse_csv(csv_file)
        all_items.extend(items)
    return all_items


def is_phrase(word: str) -> bool:
    return len(word.split()) > 1 or "-" in word or "……" in word


def auto_sentence(word: str, meaning: str) -> Optional[str]:
    """Auto-generate a simple sentence template if no custom one exists."""
    w = word.lower()
    # Basic patterns
    if w.startswith("a ") or w.startswith("an ") or w.startswith("the "):
        return f"In class, we learned about {{blank}}."
    if meaning.startswith("v.") or w.endswith("e") or w.endswith("y"):
        return f"Please {{blank}} this sentence with the correct word."
    if meaning.startswith("a.") or meaning.startswith("adj."):
        return f"The weather today is very {{blank}}."
    if meaning.startswith("adv."):
        return f"She spoke very {{blank}} to the children."
    return f"Can you use the word {{blank}} in a sentence?"


def auto_definition(word: str, meaning: str) -> Optional[str]:
    """Auto-generate a definition from the meaning field."""
    if not meaning:
        return None
    # Strip part-of-speech prefixes
    cleaned = re.sub(r"^(n\.|v\.|a\.|adj\.|adv\.|conj\.|prep\.)\s*", "", meaning)
    if cleaned:
        return f"A word that means {cleaned}."
    return None


def generate_section_a(vocab: List[VocabItem], count: int) -> List[TestItem]:
    candidates = [v for v in vocab if not is_phrase(v.word) and len(v.word) < 25]
    if len(candidates) < count:
        candidates = vocab
    selected = random.sample(candidates, min(count, len(candidates)))
    items = []
    for i, v in enumerate(selected, 1):
        items.append(TestItem(
            number=i, section="A", word=v.word, meaning=v.meaning,
            prompt="Write the word you hear.", answer=v.word,
            audio_text=v.word, source=v.source))
    return items


def generate_section_b(vocab: List[VocabItem], count: int) -> List[TestItem]:
    candidates = [v for v in vocab if is_phrase(v.word) and len(v.word) < 40]
    if len(candidates) < count:
        candidates = [v for v in vocab if len(v.word) < 40]
    selected = random.sample(candidates, min(count, len(candidates)))
    items = []
    for i, v in enumerate(selected, 1):
        items.append(TestItem(
            number=i, section="B", word=v.word, meaning=v.meaning,
            prompt="Write the phrase you hear.", answer=v.word,
            audio_text=v.word, source=v.source))
    return items


def generate_section_c(vocab: List[VocabItem], count: int, templates: Dict[str, str]) -> List[TestItem]:
    eligible = []
    for v in vocab:
        if v.word in templates or auto_sentence(v.word, v.meaning):
            eligible.append(v)
    selected = random.sample(eligible, min(count, len(eligible)))
    items = []
    for i, v in enumerate(selected, 1):
        sentence = templates.get(v.word) or auto_sentence(v.word, v.meaning)
        if not sentence:
            sentence = f"Can you use the word {{blank}} in a sentence?"
        blanked = sentence.replace("{blank}", "__________")
        items.append(TestItem(
            number=i, section="C", word=v.word, meaning=v.meaning,
            prompt=blanked, answer=v.word,
            audio_text=sentence.replace("{blank}", v.word), source=v.source))
    return items


def generate_section_d(vocab: List[VocabItem], count: int, templates: Dict[str, str]) -> List[TestItem]:
    eligible = []
    for v in vocab:
        if v.word in templates or auto_definition(v.word, v.meaning):
            eligible.append(v)
    selected = random.sample(eligible, min(count, len(eligible)))
    all_words = [v.word for v in vocab]
    items = []
    for i, v in enumerate(selected, 1):
        definition = templates.get(v.word) or auto_definition(v.word, v.meaning)
        if not definition:
            definition = f"A word that means {v.meaning}."
        distractors = [w for w in all_words if w != v.word]
        if len(distractors) >= 3:
            chosen_distractors = random.sample(distractors, 3)
        else:
            chosen_distractors = distractors + ["unknown"] * (3 - len(distractors))
        options = [v.word] + chosen_distractors
        random.shuffle(options)
        correct_letter = chr(65 + options.index(v.word))
        option_texts = [f"{chr(65 + j)}) {opt}" for j, opt in enumerate(options)]
        audio_text = f"{definition} {' '.join(option_texts)}"
        prompt_html = "<br>".join(option_texts)
        items.append(TestItem(
            number=i, section="D", word=v.word, meaning=v.meaning,
            prompt=prompt_html, answer=correct_letter,
            audio_text=audio_text, source=v.source, options=options))
    return items


def generate_test(vocab: List[VocabItem], config: Dict, sentence_templates: Dict[str, str], definition_templates: Dict[str, str]) -> Dict:
    random.seed(config.get("seed", 42))
    test_data = {
        "title": config.get("title", "Listening Test"),
        "subtitle": config.get("subtitle", "Vocabulary Retention & Listening Recognition"),
        "instructions": "This test contains 4 sections. Each audio will be played twice. Write your answers clearly.",
        "sections": {}
    }
    for sec_id, sec_cfg in config["sections"].items():
        count = sec_cfg["count"]
        if sec_id == "A":
            items = generate_section_a(vocab, count)
        elif sec_id == "B":
            items = generate_section_b(vocab, count)
        elif sec_id == "C":
            items = generate_section_c(vocab, count, sentence_templates)
        elif sec_id == "D":
            items = generate_section_d(vocab, count, definition_templates)
        else:
            items = []
        test_data["sections"][sec_id] = {
            "name": sec_cfg["name"],
            "description": sec_cfg["description"],
            "count": len(items),
            "points": sec_cfg.get("points", 1),
            "items": [asdict(item) for item in items]
        }
    return test_data


def render_html(template_path: Path, replacements: Dict[str, str]) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    for key, val in replacements.items():
        html = html.replace(f"{{{{{key}}}}}", val)
    return html


def build_answer_sheet(test_data: Dict, template_path: Path) -> str:
    total_points = sum(s["count"] * s.get("points", 1) for s in test_data["sections"].values())
    
    def build_grid(items: List[Dict]) -> str:
        lines = []
        for item in items:
            lines.append(f'            <div class="item"><span class="item-num">{item["number"]}. </span><span class="item-blank"></span></div>')
        return "\n".join(lines)
    
    def build_sentences(items: List[Dict]) -> str:
        lines = []
        for item in items:
            lines.append(f'''        <div class="sentence-item">
            <div class="sentence-text">{item["number"]}. {item["prompt"]}</div>
            <div>Answer: <span class="sentence-answer"></span></div>
        </div>''')
        return "\n".join(lines)
    
    def build_multiple_choice(items: List[Dict]) -> str:
        lines = []
        for item in items:
            opts = item.get("options", [])
            opt_rows = "\n".join([f'                <div class="mc-option-row"><span class="mc-circle"></span><span class="mc-label">{chr(65 + j)}) {opt}</span></div>' for j, opt in enumerate(opts)]) if opts else ""
            lines.append(f'''        <div class="mc-item">
            <div class="mc-number">{item["number"]}.</div>
            <div class="mc-options">
{opt_rows}
            </div>
        </div>''')
        return "\n".join(lines)
    
    sections_html = ""
    for sec_id in ["A", "B", "C", "D"]:
        sec = test_data["sections"][sec_id]
        sec_points = sec["count"] * sec.get("points", 1)
        sections_html += f'''<div class="section">
        <div class="section-header">Section {sec_id}: {sec["name"]} ({sec["count"]} &times; {sec.get("points", 1)} = {sec_points} points)</div>
        <div class="section-desc">{sec["description"]}</div>
'''
        if sec_id in ("A", "B"):
            sections_html += f'        <div class="items-grid">\n{build_grid(sec["items"])}\n        </div>\n'
        elif sec_id == "C":
            sections_html += f'{build_sentences(sec["items"])}\n'
        elif sec_id == "D":
            sections_html += f'{build_multiple_choice(sec["items"])}\n'
        sections_html += "    </div>\n"
        if sec_id == "B":
            sections_html += '<div class="page-break"></div>\n'
    
    return render_html(template_path, {
        "title": test_data["title"],
        "subtitle": test_data["subtitle"],
        "total_points": str(total_points),
        "sections": sections_html
    })


def build_answer_key(test_data: Dict, template_path: Path) -> str:
    total_points = sum(s["count"] * s.get("points", 1) for s in test_data["sections"].values())
    
    def clean_meaning(meaning: str) -> str:
        return re.sub(r"^(n\.|v\.|a\.|adj\.|adv\.|conj\.|prep\.)\s*", "", meaning)
    
    sections_html = ""
    for sec_id in ["A", "B", "C", "D"]:
        sec = test_data["sections"][sec_id]
        sections_html += f'''<div class="section">
    <div class="section-header">Section {sec_id}: {sec["name"]} ({sec["count"]} items)</div>
    <table>
        <tr><th class="num">#</th><th class="answer">Answer</th><th>Meaning / Context</th><th class="source">Source</th></tr>
'''
        for item in sec["items"]:
            meaning = clean_meaning(item["meaning"])
            if sec_id == "D":
                opts = item.get("options", [])
                opt_text = " | ".join([f"{chr(65+j)}) {opt}" for j, opt in enumerate(opts)])
                answer_text = f"{item['answer']} — {item['word']}"
                meaning = f"{opt_text}<br><em>{meaning}</em>"
            else:
                answer_text = item["answer"]
            sections_html += f'        <tr><td class="num">{item["number"]}</td><td class="answer">{answer_text}</td><td class="meaning">{meaning}</td><td class="source">{item["source"]}</td></tr>\n'
        sections_html += "    </table>\n</div>\n"
    
    return render_html(template_path, {
        "title": test_data["title"],
        "total_points": str(total_points),
        "sections": sections_html
    })


def build_audio_script(test_data: Dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"LISTENING TEST AUDIO SCRIPT")
    lines.append(f"{test_data['title']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("[INTRO MUSIC]")
    lines.append("")
    lines.append(f"Welcome to the {test_data['title']}.")
    lines.append("This test has four sections. Each item will be read twice.")
    lines.append("Please write your answers in the spaces provided.")
    lines.append("You may start now.")
    lines.append("")
    
    for section_id in ["A", "B", "C", "D"]:
        section = test_data["sections"][section_id]
        lines.append("=" * 60)
        lines.append(f"SECTION {section_id}: {section['name'].upper()}")
        lines.append("=" * 60)
        lines.append(section["description"])
        lines.append("")
        for item in section["items"]:
            lines.append(f"Number {item['number']}.")
            if section_id in ("A", "B"):
                lines.append(f"    {item['audio_text']}")
                lines.append(f"    (repeat)")
                lines.append(f"    {item['audio_text']}")
            elif section_id == "D":
                lines.append(f"    {item['audio_text']}")
            else:
                lines.append(f"    {item['audio_text']}")
            lines.append("")
        lines.append(f"[End of Section {section_id}]")
        lines.append("")
    
    lines.append("=" * 60)
    lines.append("END OF TEST")
    lines.append("Please check your answers.")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a listening test from vocabulary CSV files.")
    parser.add_argument("-i", "--input-dir", type=Path, default=Path("."), help="Directory containing vocabulary CSV files")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."), help="Output directory for generated files")
    parser.add_argument("-c", "--config", type=Path, default=None, help="JSON config file for test settings")
    parser.add_argument("--sentence-templates", type=Path, default=None, help="Markdown file with sentence templates")
    parser.add_argument("--definition-templates", type=Path, default=None, help="Markdown file with definition templates")
    parser.add_argument("--sample-rate", type=float, default=None, help="Randomly sample this fraction of vocabulary (0.0-1.0) before generating the test")
    parser.add_argument("--count-a", type=int, default=None, help="Number of items for Section A (overrides config)")
    parser.add_argument("--count-b", type=int, default=None, help="Number of items for Section B (overrides config)")
    parser.add_argument("--count-c", type=int, default=None, help="Number of items for Section C (overrides config)")
    parser.add_argument("--count-d", type=int, default=None, help="Number of items for Section D (overrides config)")
    args = parser.parse_args()
    
    # Load config
    config = DEFAULT_CONFIG.copy()
    if args.config and args.config.exists():
        with open(args.config, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config.update(user_config)
    
    # Apply CLI section count overrides
    section_count_overrides = {
        "A": args.count_a,
        "B": args.count_b,
        "C": args.count_c,
        "D": args.count_d,
    }
    for sec_id, count in section_count_overrides.items():
        if count is not None and sec_id in config.get("sections", {}):
            config["sections"][sec_id]["count"] = count
    
    # Load vocab
    print(f"Loading vocabulary from: {args.input_dir}")
    vocab = load_all_vocab(args.input_dir)
    print(f"Loaded {len(vocab)} vocabulary items")
    
    if len(vocab) == 0:
        print("No vocabulary found. Exiting.")
        return
    
    # Optionally sample a subset of vocabulary
    if args.sample_rate is not None:
        if not (0.0 < args.sample_rate <= 1.0):
            print("Error: --sample-rate must be between 0.0 and 1.0 (exclusive of 0).")
            return
        sample_count = max(1, int(len(vocab) * args.sample_rate))
        random.seed(config.get("seed", 42))
        vocab = random.sample(vocab, sample_count)
        print(f"Sampled {len(vocab)} vocabulary items ({args.sample_rate*100:.0f}%)")
    
    # Load templates
    sentence_templates = load_templates(args.sentence_templates)
    definition_templates = load_templates(args.definition_templates)
    print(f"Custom sentence templates: {len(sentence_templates)}")
    print(f"Custom definition templates: {len(definition_templates)}")
    
    # Generate test
    print("Generating test content...")
    test_data = generate_test(vocab, config, sentence_templates, definition_templates)
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    json_path = args.output_dir / "test_content.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Test content: {json_path}")
    
    # Save audio script
    script_path = args.output_dir / "audio_script.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(build_audio_script(test_data))
    print(f"✓ Audio script: {script_path}")
    
    # Determine template paths
    skill_dir = Path(__file__).parent.parent
    sheet_template = skill_dir / "assets" / "answer_sheet_template.html"
    key_template = skill_dir / "assets" / "answer_key_template.html"
    
    # Generate answer sheet
    sheet_path = args.output_dir / "student_answer_sheet.html"
    with open(sheet_path, "w", encoding="utf-8") as f:
        f.write(build_answer_sheet(test_data, sheet_template))
    print(f"✓ Answer sheet: {sheet_path}")
    
    # Generate answer key
    key_path = args.output_dir / "teacher_answer_key.html"
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(build_answer_key(test_data, key_template))
    print(f"✓ Answer key: {key_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    total_items = 0
    total_points = 0
    for sec_id in ["A", "B", "C", "D"]:
        sec = test_data["sections"][sec_id]
        pts = sec["count"] * sec.get("points", 1)
        total_items += sec["count"]
        total_points += pts
        print(f"Section {sec_id}: {sec['count']} items × {sec.get('points', 1)} = {pts} pts")
    print(f"\nTotal: {total_items} items, {total_points} points")
    print("=" * 60)


if __name__ == "__main__":
    main()
