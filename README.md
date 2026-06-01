# 🎧 Listening Test Generator

A [Kimi Code CLI](https://github.com/MoonshotAI/kimi-cli) skill that generates vocabulary listening tests from CSV word lists. It creates printable student answer sheets, teacher grading keys, and ElevenLabs TTS audio with balanced male/female and British/American voices.

## Features

- **Printable Materials**: Auto-generated answer sheets and teacher keys in HTML format
- **TTS Audio**: Uses ElevenLabs API for high-quality text-to-speech
- **Voice Variety**: Balanced male/female and British/American English voices
- **Batch Generation**: Process entire word lists in one command
- **Customizable Templates**: Adjust sentence templates and definitions to your needs

## Prerequisites

- Python 3.8+
- [Kimi Code CLI](https://moonshotai.github.io/kimi-cli/) installed
- ElevenLabs API key (for audio generation)

## Installation

### Step 1: Install Kimi Code CLI

```bash
# Using uv (recommended)
uv tool install kimi-cli

# Or using pipx
pipx install kimi-cli

# Or using pip
pip install kimi-cli
```

For detailed installation instructions, see the [official documentation](https://moonshotai.github.io/kimi-cli/en/guides/getting-started.html).

### Step 2: Install This Skill

#### Option A: Manual Installation

1. Download the latest `listening-test-generator.skill` file from [Releases](../../releases)
2. Create the skills directory if it doesn't exist:
   ```bash
   mkdir -p ~/.kimi/skills/listening-test-generator
   ```
3. Extract the `.skill` file (it's a zip archive):
   ```bash
   # Rename .skill to .zip
   mv listening-test-generator.skill listening-test-generator.zip
   
   # Extract to the skills directory
   unzip listening-test-generator.zip -d ~/.kimi/skills/listening-test-generator/
   ```
4. Restart Kimi Code CLI. The skill will be automatically loaded.

#### Option B: Clone from GitHub

```bash
# Clone directly into your Kimi skills directory
git clone https://github.com/denghanjie/listening-test-generator.git ~/.kimi/skills/listening-test-generator
```

#### Option C: Copy Script (One-liner)

```bash
mkdir -p ~/.kimi/skills/listening-test-generator && \
curl -L https://github.com/denghanjie/listening-test-generator/archive/refs/heads/main.zip -o /tmp/ltg.zip && \
unzip -q /tmp/ltg.zip -d /tmp/ltg && \
cp -r /tmp/ltg/listening-test-generator-main/* ~/.kimi/skills/listening-test-generator/ && \
rm -rf /tmp/ltg /tmp/ltg.zip
```

### Step 3: Verify Installation

Start Kimi Code CLI and check if the skill is loaded:

```bash
kimi
```

You should see `listening-test-generator` listed under **User Skills**.

## Usage

Once installed, simply ask Kimi to generate a listening test:

```
Generate a listening test from my vocabulary list: words.csv
```

Or invoke the skill directly:

```
/skill:listening-test-generator Create a listening test with 20 vocabulary words about science
```

### Input Format

Prepare a CSV file with your vocabulary words:

```csv
word,definition
abundant,existing in large quantities; plentiful
analyze,examine methodically and in detail
```

### Output Files

The skill generates:
- `listening_test_audio.mp3` — The audio file with all words and sentences
- `answer_sheet.html` — Printable student answer sheet
- `answer_key.html` — Teacher's answer key with correct answers

## Project Structure

```
listening-test-generator/
├── SKILL.md                          # Skill definition and instructions
├── scripts/
│   ├── generate_audio.py             # ElevenLabs TTS integration
│   └── generate_test.py              # Test material generator
├── assets/
│   ├── answer_sheet_template.html    # Student answer sheet template
│   └── answer_key_template.html      # Teacher answer key template
└── references/
    ├── voices.md                     # Available voice configurations
    ├── sentence_templates.md         # Sentence structure templates
    └── definition_templates.md       # Definition format templates
```

## Requirements

- `elevenlabs` Python package (auto-installed when scripts run)
- Valid ElevenLabs API key set in environment:
  ```bash
  export ELEVENLABS_API_KEY="your-api-key-here"
  ```

## License

MIT License — feel free to use and modify for your classroom or personal needs.

## Contributing

This skill is part of a collection of educational tools for standardized test preparation. Suggestions and improvements are welcome!
