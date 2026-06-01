#!/usr/bin/env python3
"""
ElevenLabs Audio Generator for Listening Tests
Generates MP3 files with balanced male/female and British/American voices.
Filenames do NOT contain vocabulary words to prevent answer leakage.
Supports individual files, section-combined files, and full-test combined file.
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List

try:
    from elevenlabs import ElevenLabs, VoiceSettings
except ImportError:
    ElevenLabs = None

DEFAULT_VOICES = [
    {"id": "CwhRBWXzGAHq8TQ4Fs17", "name": "Roger",    "gender": "male",   "accent": "british"},
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George",   "gender": "male",   "accent": "british"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah",    "gender": "female", "accent": "british"},
    {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda",  "gender": "female", "accent": "british"},
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie",  "gender": "male",   "accent": "american"},
    {"id": "bIHbv24MWmeRgasZH58o", "name": "Will",     "gender": "male",   "accent": "american"},
    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice",    "gender": "female", "accent": "american"},
    {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica",  "gender": "female", "accent": "american"},
]

VOICE_SETTINGS = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True
)


def _extract_export_value(line: str, var_name: str) -> str:
    """Extract the quoted value from an export line like: export VAR=<value>"""
    prefix = f"export {var_name}="
    stripped = line.strip()
    if not stripped.startswith(prefix):
        return ""
    rest = stripped[len(prefix):]
    for quote in ('"', "'"):
        if rest.startswith(quote):
            end = rest.find(quote, 1)
            if end != -1:
                return rest[1:end]
    return ""


def _search_env_files(var_name: str) -> str:
    """Search common shell config files for an exported variable.
    Falls back to common alternate names (e.g. ELEVEN_API_KEY for ELEVENLABS_API_KEY).
    """
    home = Path.home()
    candidates = [
        home / ".zshrc",
        home / ".bashrc",
        home / ".bash_profile",
        home / ".profile",
        home / ".zprofile",
    ]
    # Also try common alternate names
    alt_names = [var_name]
    if var_name == "ELEVENLABS_API_KEY":
        alt_names.append("ELEVEN_API_KEY")

    for path in candidates:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            for name in alt_names:
                val = _extract_export_value(line, name)
                if val:
                    return val
    return ""


def get_client(api_key_env: str) -> ElevenLabs:
    if ElevenLabs is None:
        raise RuntimeError("elevenlabs package not installed. Run: pip install elevenlabs")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        api_key = _search_env_files(api_key_env)
        if api_key:
            os.environ[api_key_env] = api_key
    if not api_key:
        raise ValueError(f"Environment variable {api_key_env} not set.")
    return ElevenLabs(api_key=api_key)


def generate_item_audio(client, text: str, output_path: Path, voice_id: str, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                voice_settings=VOICE_SETTINGS
            )
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"    Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    FAILED: {output_path.name}")
                return False
    return False


def generate_section_audios(client, section_id: str, section_data: Dict, output_dir: Path, voices: List[Dict]) -> List[Path]:
    generated = []
    items = section_data["items"]
    print(f"\n{'='*60}")
    print(f"Section {section_id}: {section_data['name']} ({len(items)} items)")
    print(f"{'='*60}")
    for i, item in enumerate(items):
        voice = voices[i % len(voices)]
        if section_id in ("A", "B"):
            audio_text = f"Number {item['number']}. {item['audio_text']}. {item['audio_text']}."
        else:
            audio_text = f"Number {item['number']}. {item['audio_text']}"
        output_path = output_dir / f"sec{section_id}_{item['number']:02d}.mp3"
        print(f"  [{i+1:>2}/{len(items)}] #{item['number']:>2} | {voice['name']:>7} ({voice['gender']}, {voice['accent']})")
        if generate_item_audio(client, audio_text, output_path, voice["id"]):
            generated.append(output_path)
            time.sleep(0.3)
    return generated


def combine_section_files(files: List[Path], output_path: Path) -> bool:
    """Combine individual MP3s into one section file using ffmpeg."""
    if not files:
        return False
    # Create concat list file for ffmpeg
    list_path = output_path.parent / f"{output_path.stem}_concat_list.txt"
    with open(list_path, "w") as f:
        for mp3 in sorted(files):
            f.write(f"file '{mp3.absolute()}'\n")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_path),
                "-c:a", "libmp3lame", "-q:a", "2",
                str(output_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        list_path.unlink()
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ffmpeg error: {e.stderr[:200]}")
        return False
    except FileNotFoundError:
        print("    ffmpeg not found. Cannot combine audio files.")
        return False


def generate_full_test_audio(client, test_data: Dict, output_dir: Path, voice_id: str) -> Path:
    print("\n" + "=" * 60)
    print("Generating FULL TEST audio")
    print("=" * 60)
    lines = []
    lines.append(f"Welcome to the {test_data['title']}.")
    lines.append("This test has four sections. Each item will be read twice.")
    lines.append("Please write your answers in the spaces provided.")
    lines.append("You may start now.")
    for section_id in ["A", "B", "C", "D"]:
        section = test_data["sections"][section_id]
        lines.append(f"Section {section_id}. {section['name']}. {section['description']}")
        for item in section["items"]:
            if section_id in ("A", "B"):
                lines.append(f"Number {item['number']}. {item['audio_text']}. {item['audio_text']}.")
            else:
                lines.append(f"Number {item['number']}. {item['audio_text']}")
        lines.append(f"End of Section {section_id}.")
    lines.append("End of test. Please check your answers.")
    full_text = " ".join(lines)
    output_path = output_dir / "full_test.mp3"
    print(f"  Length: {len(full_text)} chars. Generating...")
    if generate_item_audio(client, full_text, output_path, voice_id, retries=5):
        print(f"  ✓ Full test: {output_path}")
        return output_path
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate listening test audio via ElevenLabs.")
    parser.add_argument("-i", "--input", type=Path, default=Path("test_content.json"), help="Path to test_content.json")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("audio"), help="Output directory for MP3s")
    parser.add_argument("--api-key-env", default="ELEVENLABS_API_KEY", help="Environment variable name for API key")
    parser.add_argument("--full-test", action="store_true", help="Also generate a single combined audio file")
    parser.add_argument("--combine-sections", action="store_true", help="Also generate combined section audio files")
    parser.add_argument("--slowdown", type=float, default=None, help="Slow down combined files by this factor (e.g., 0.8 for 20%% slower). Requires ffmpeg.")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive prompts; use flags only")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"✗ Input not found: {args.input}")
        return

    client = get_client(args.api_key_env)
    print("✓ ElevenLabs client initialized")

    with open(args.input, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    print(f"✓ Loaded: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output: {args.output_dir}")

    # Interactive menu if not disabled
    want_individual = True
    want_combine_sections = args.combine_sections
    want_full_test = args.full_test

    if not args.non_interactive:
        print("\nWhat would you like to generate?")
        print("  1. Individual item files only")
        print("  2. Individual files + section-combined files")
        print("  3. Individual files + full-test file")
        print("  4. All (individual + sections + full test)")
        choice = input("Enter choice (1/2/3/4): ").strip()
        if choice == "1":
            want_combine_sections = False
            want_full_test = False
        elif choice == "2":
            want_combine_sections = True
            want_full_test = False
        elif choice == "3":
            want_combine_sections = False
            want_full_test = True
        elif choice == "4":
            want_combine_sections = True
            want_full_test = True
        else:
            print("Invalid choice. Defaulting to individual files only.")
            want_combine_sections = False
            want_full_test = False

    # Generate individual files
    generated = []
    section_files = {}
    for section_id in ["A", "B", "C", "D"]:
        sec = test_data["sections"][section_id]
        files = generate_section_audios(client, section_id, sec, args.output_dir, DEFAULT_VOICES)
        generated.extend(files)
        section_files[section_id] = files

    # Combine sections
    if want_combine_sections:
        print("\n" + "=" * 60)
        print("Combining section audio files")
        print("=" * 60)
        for section_id in ["A", "B", "C", "D"]:
            files = section_files.get(section_id, [])
            output_path = args.output_dir / f"sec{section_id}_combined.mp3"
            print(f"  Section {section_id}: combining {len(files)} files...")
            if combine_section_files(files, output_path):
                print(f"  ✓ {output_path.name}")
                generated.append(output_path)
            else:
                print(f"  ✗ Failed to combine Section {section_id}")

    # Full test
    if want_full_test:
        full = generate_full_test_audio(client, test_data, args.output_dir, DEFAULT_VOICES[0]["id"])
        if full:
            generated.append(full)

    # Slowdown via ffmpeg
    if args.slowdown and args.slowdown < 1.0:
        print("\n" + "=" * 60)
        print(f"Applying {((1 - args.slowdown) * 100):.0f}% slowdown via ffmpeg")
        print("=" * 60)
        targets = []
        if want_combine_sections:
            for sec in ["A", "B", "C", "D"]:
                p = args.output_dir / f"sec{sec}_combined.mp3"
                if p.exists():
                    targets.append(p)
        if want_full_test:
            p = args.output_dir / "full_test.mp3"
            if p.exists():
                targets.append(p)
        for src in targets:
            dst = src.with_stem(f"{src.stem}_slow")
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(src),
                    "-filter:a", f"atempo={args.slowdown}",
                    "-c:a", "libmp3lame", "-q:a", "2",
                    str(dst)
                ], capture_output=True, check=True)
                print(f"  ✓ {dst.name}")
                generated.append(dst)
            except Exception as e:
                print(f"  ✗ {src.name}: {e}")

    existing = [f for f in generated if f.exists()]
    total = sum(f.stat().st_size for f in existing)
    print("\n" + "=" * 60)
    print(f"Generated {len(existing)} files, {total/(1024*1024):.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
