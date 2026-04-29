#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Extreme silence for TensorFlow/Keras
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Import these AFTER env vars
try:
    import httpx
    import tqdm
except ImportError:
    print("[jarvis-models] 📦 Installing downloader dependencies...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "httpx", "tqdm", "-q"]
    )
    import httpx
    from tqdm import tqdm

MODEL_HOME = Path.home() / ".jarvis" / "models"
PIPER_DIR = MODEL_HOME / "tts"
VOSK_DIR = MODEL_HOME / "stt" / "vosk"

PIPER_MODEL_URL = "https://huggingface.org/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
PIPER_CONFIG_URL = "https://huggingface.org/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def print_step(msg: str) -> None:
    print(f"\033[1;34m[jarvis-models]\033[0m {msg}")


def ensure_dirs() -> None:
    for directory in (PIPER_DIR, VOSK_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        return

    print_step(f"Downloading {dest.name}...")
    with httpx.stream("GET", url, follow_redirects=True) as response:
        total = int(response.headers.get("Content-Length", 0))
        with (
            open(dest, "wb") as f,
            tqdm(
                total=total, unit="B", unit_scale=True, desc=dest.name, leave=False
            ) as bar,
        ):
            for chunk in response.iter_bytes():
                f.write(chunk)
                bar.update(len(chunk))


def prepare_moonshine() -> None:
    print_step("Checking Moonshine Tiny STT...")
    try:
        import moonshine

        # Redirect stderr to devnull to hide TF initialization noise
        with open(os.devnull, "w") as fnull:
            old_stderr = sys.stderr
            sys.stderr = fnull
            try:
                _ = moonshine.load_model("moonshine/tiny")
            finally:
                sys.stderr = old_stderr
        print_step("✅ Moonshine tiny model ready")
    except Exception as exc:
        print_step(f"❌ Moonshine check failed: {exc}")


def prepare_vosk() -> None:
    print_step("Checking Vosk STT...")
    try:
        model_name = "vosk-model-small-en-us-0.15"
        model_path = VOSK_DIR / model_name

        if not model_path.exists():
            zip_path = VOSK_DIR / f"{model_name}.zip"
            download_file(VOSK_MODEL_URL, zip_path)
            print_step(f"Extracting {model_name}...")
            import zipfile

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(VOSK_DIR)
            zip_path.unlink()

        print_step(f"✅ Vosk model ready: {model_name}")
    except Exception as exc:
        print_step(f"⚠️ Vosk check failed: {exc}")


def prepare_piper(model_name: str) -> None:
    print_step(f"Checking Piper model: {model_name}...")
    try:
        model_path = PIPER_DIR / model_name
        config_path = PIPER_DIR / f"{model_name}.json"

        if not model_path.exists():
            download_file(PIPER_MODEL_URL, model_path)
        if not config_path.exists():
            download_file(PIPER_CONFIG_URL, config_path)

        print_step(f"✅ Piper model ready: {model_name}")
    except Exception as exc:
        print_step(f"⚠️ Piper check failed: {exc}")


def main() -> None:
    ensure_dirs()
    piper_model = os.getenv("JARVIS_TTS_PIPER_MODEL", "en_US-lessac-medium.onnx")

    print_step(f"Targeting model home: {MODEL_HOME}")
    prepare_moonshine()
    prepare_vosk()
    prepare_piper(piper_model)
    print_step("✨ Model preparation routine complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[jarvis-models] 🛑 Interrupted by user.")
        sys.exit(1)
