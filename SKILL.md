---
name: listening-test-generator
description: >
  Generate vocabulary listening tests from CSV word lists with printable answer sheets,
  teacher keys, and ElevenLabs TTS audio. Use when the user wants to: (1) create a listening
  test or quiz from vocabulary words, (2) generate audio for vocabulary dictation or
  recognition practice, (3) build printable student answer sheets and teacher grading keys,
  (4) consolidate vocabulary retention through listening exercises, or (5) work with any
  word-list CSV files to produce structured test materials with balanced male/female and
  British/American voice audio.
---

# Listening Test Generator

Generate structured listening tests from vocabulary CSV files. Produces test content JSON,
printable HTML answer sheets, teacher answer keys, audio scripts, and optional ElevenLabs MP3s.

## Workflow

1. **Locate vocabulary CSV files** in the project directory
2. **Count total vocabulary items**
3. **If vocabulary exceeds ~100 words**, ask the user what percentage to test (e.g. 30%, 50%, 70%, 90%, 100%)
4. **Ask the user** how many questions they want for each section (A, B, C, D), or use sensible defaults
5. **Run `scripts/generate_test.py`** to create test content and HTML materials
6. **Optionally run `scripts/generate_audio.py`** if the user wants ElevenLabs audio
7. **Deliver generated files** to the user

## CSV Format

The skill accepts common vocabulary CSV layouts:
- `word,meaning,,,` (trailing empty columns ignored)
- `word,translation`
- `word,part_of_speech,translation`

Header rows (`word`, `单词`, `vocabulary`) are auto-detected and skipped. Rows ending in `?`
or very long sentences without definitions are filtered out.

## Generating Test Content

```bash
python3 ~/.kimi/skills/listening-test-generator/scripts/generate_test.py \
  -i ./vocab_csvs \
  -o ./test_output \
  --sentence-templates ~/.kimi/skills/listening-test-generator/references/sentence_templates.md \
  --definition-templates ~/.kimi/skills/listening-test-generator/references/definition_templates.md
```

### Sampling a Subset for Large Vocabularies

When the vocabulary pool is very large, use `--sample-rate` to randomly select a fraction (0.0–1.0) of words before generating the test:

```bash
python3 ~/.kimi/skills/listening-test-generator/scripts/generate_test.py \
  -i ./vocab_csvs \
  -o ./test_output \
  --sample-rate 0.5 \
  --sentence-templates ~/.kimi/skills/listening-test-generator/references/sentence_templates.md \
  --definition-templates ~/.kimi/skills/listening-test-generator/references/definition_templates.md
```

The script will randomly choose 50% of the loaded vocabulary and build the test from that subset.

### Customizing Section Counts

Pass `--count-a`, `--count-b`, `--count-c`, and/or `--count-d` to override the number of items in each section without writing a config file:

```bash
python3 ~/.kimi/skills/listening-test-generator/scripts/generate_test.py \
  -i ./vocab_csvs \
  -o ./test_output \
  --count-a 30 --count-b 15 --count-c 15 --count-d 10 \
  --sentence-templates ~/.kimi/skills/listening-test-generator/references/sentence_templates.md \
  --definition-templates ~/.kimi/skills/listening-test-generator/references/definition_templates.md
```

These flags override both the default counts and any values in a `--config` JSON file.

Outputs:
- `test_content.json` — complete test data with answers
- `student_answer_sheet.html` — printable student sheet
- `teacher_answer_key.html` — grading key with answers
- `audio_script.txt` — human-readable recording script

### Customizing Section Counts

Pass a JSON config file via `--config`:

```json
{
  "title": "Unit 7 Listening Test",
  "seed": 123,
  "sections": {
    "A": {"name": "Word Dictation", "description": "...", "count": 30, "points": 1},
    "B": {"name": "Phrase Dictation", "description": "...", "count": 15, "points": 2},
    "C": {"name": "Sentence Completion", "description": "...", "count": 15, "points": 0.5},
    "D": {"name": "Multiple Choice", "description": "...", "count": 10, "points": 0.5}
  }
}
```

Default sections: A=40, B=20, C=20, D=15 items.

## Generating Audio

Requires an ElevenLabs API key. The script checks for it in this order:

1. **Environment variable** `ELEVENLABS_API_KEY` (or the custom name passed via `--api-key-env`)
2. **Local shell config files** — if the env var is not set, the script automatically searches:
   - `~/.zshrc`
   - `~/.bashrc`
   - `~/.bash_profile`
   - `~/.profile`
   - `~/.zprofile`

   It looks for `export ELEVENLABS_API_KEY="..."` and also falls back to common alternate names such as `ELEVEN_API_KEY`.

If neither source provides a key, set it explicitly before running:

```bash
export ELEVENLABS_API_KEY="your-key"
python3 ~/.kimi/skills/listening-test-generator/scripts/generate_audio.py \
  -i ./test_output/test_content.json \
  -o ./test_output/audio \
  --combine-sections
```

The script interactively asks what to generate:
1. Individual item files only
2. Individual files + **section-combined files** (`secA_combined.mp3`, etc.)
3. Individual files + full-test file
4. All of the above

For non-interactive use, add `--non-interactive` with flags:
```bash
python3 ~/.kimi/skills/listening-test-generator/scripts/generate_audio.py \
  -i ./test_output/test_content.json \
  -o ./test_output/audio \
  --combine-sections --full-test --non-interactive
```

### Slowing Down Audio

Use `--slowdown 0.8` to reduce speed by 20% (requires ffmpeg). This applies to combined section files and the full-test file:

```bash
python3 .../generate_audio.py ... --combine-sections --slowdown 0.8
```

This produces both `secA_combined.mp3` and `secA_combined_slow.mp3`.

Audio features:
- **Balanced voices**: 8-voice rotation (50% male/female, 50% British/American)
- **Safe filenames**: `secA_01.mp3` (no vocabulary words in names)
- **Individual files**: One MP3 per test item
- **Optional combined file**: `full_test.mp3` with all sections

Voice reference: see `references/voices.md`.

## Customizing Templates

### Sentence Templates (Section C)
Edit or extend `references/sentence_templates.md`. Format:
```
word | Sentence with {blank} placeholder.
```
If no custom template exists, a simple auto-generated sentence is used.

### Definition Templates (Section D)
Edit or extend `references/definition_templates.md`. Format:
```
word | Definition sentence describing the word.
```
If no custom definition exists, one is auto-generated from the CSV meaning field.

### HTML Styling
Edit `assets/answer_sheet_template.html` or `assets/answer_key_template.html`.
Placeholders: `{{title}}`, `{{subtitle}}`, `{{total_points}}`, `{{sections}}`.

## Test Structure

| Section | Name | Default Count | Points Each | Description |
|---------|------|---------------|-------------|-------------|
| A | Word Dictation | 40 | 1 | Single words, spoken twice |
| B | Phrase Dictation | 20 | 2 | Multi-word phrases, spoken twice |
| C | Sentence Completion | 20 | 0.5 | Fill-in-the-blank sentences |
| D | Multiple Choice | 15 | 0.33 | Definition + 4 options (A/B/C/D) |

Section D auto-generates 3 random distractors from the vocabulary pool and shuffles the options.

## Bundled Resources

- `scripts/generate_test.py` — test content generator
- `scripts/generate_audio.py` — ElevenLabs audio generator
- `assets/answer_sheet_template.html` — student sheet template
- `assets/answer_key_template.html` — teacher key template
- `references/sentence_templates.md` — example sentence templates
- `references/definition_templates.md` — example definition templates
- `references/voices.md` — ElevenLabs voice reference
