"""
datasets/download_audio.py
Download a small sample of LibriSpeech clips for Phase 2 audio injection.

Uses HuggingFace datasets streaming — downloads only the clips we request,
no need to pull the full 1000h corpus.

Usage:
    python3 datasets/download_audio.py --n 20 --out datasets/audio/clean

No API key needed — LibriSpeech is fully public (CC BY 4.0).
Requires: pip install datasets soundfile
"""

import argparse
import io
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",   type=int, default=20, help="Number of clips to download")
    parser.add_argument("--out", default="datasets/audio/clean", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import soundfile as sf
        import numpy as np
        from datasets import load_dataset
    except ImportError:
        print("ERROR: pip install datasets soundfile numpy", file=sys.stderr)
        sys.exit(1)

    print(f"Streaming {args.n} clips from LibriSpeech test-clean → {out_dir}\n")

    ds = load_dataset(
        "openslr/librispeech_asr",
        "clean",
        split="test",
        streaming=True,
        trust_remote_code=True,
    )

    ok = 0
    for sample in ds.cast_column("audio", __import__("datasets").Audio(decode=False)):
        if ok >= args.n:
            break

        uid        = sample.get("id", f"clip_{ok:04d}")
        transcript = sample.get("text", "")

        # Audio is a dict with 'path' or 'bytes' — decode manually with soundfile
        audio = sample["audio"]
        try:
            if audio.get("bytes"):
                buf = io.BytesIO(audio["bytes"])
                arr, sr = sf.read(buf)
            elif audio.get("path"):
                arr, sr = sf.read(audio["path"])
            else:
                print(f"  [skip] {uid}: no audio data")
                continue
        except Exception as e:
            print(f"  [skip] {uid}: {e}")
            continue

        arr = np.array(arr, dtype=np.float32)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)  # stereo → mono

        fname = out_dir / f"{uid}.wav"
        sf.write(str(fname), arr, sr)
        (out_dir / f"{uid}.txt").write_text(transcript)

        print(f"  [ok] {fname.name}  ({sr} Hz, {len(arr)/sr:.1f}s)  \"{transcript[:60]}\"")
        ok += 1

    print(f"\nDone: {ok} clips saved to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
