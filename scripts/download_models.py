#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

MODEL_HOME = Path.home() / ".jarvis" / "models"
PIPER_DIR = MODEL_HOME / "tts"


def print_step(msg: str) -> None:
    print(f"[jarvis-models] {msg}")


def ensure_dirs() -> None:
    for directory in (PIPER_DIR,):
        directory.mkdir(parents=True, exist_ok=True)


def prepare_moonshine() -> None:
    print_step("Checking Moonshine Tiny STT")
    try:
        import moonshine

        _ = moonshine.load_model("moonshine/tiny")
        print_step("Moonshine tiny model ready")
    except Exception as exc:
        print_step(f"Moonshine check failed: {exc}")


def prepare_piper(model_name: str) -> None:
    print_step(f"Checking Piper model: {model_name}")
    try:
        from piper import PiperVoice

        model_path = PIPER_DIR / model_name
        if not model_path.exists():
            print_step(f"Piper model missing: {model_path}")
            print_step("Manual download recommended for now.")
            return

        _ = PiperVoice.load(str(model_path), use_cuda=False)
        print_step(f"Piper model ready: {model_path}")
    except Exception as exc:
        print_step(f"Piper check skipped/failed: {exc}")


def main() -> None:
    ensure_dirs()
    piper_model = os.getenv("JARVIS_TTS_PIPER_MODEL", "en_US-lessac-medium.onnx")

    print_step(f"Model home: {MODEL_HOME}")
    prepare_moonshine()
    prepare_piper(piper_model)
    print_step("Model preparation routine complete")


if __name__ == "__main__":
    main()
