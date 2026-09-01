"""Read-only DepthWizard environment and offline-cache readiness check."""

from __future__ import annotations

import importlib
import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(REPO_ROOT / "outputs" / ".hf_cache"))
MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
REQUIRED_IMPORTS = (
    ("fastapi", "fastapi"),
    ("starlette", "starlette"),
    ("httpx", "httpx"),
    ("uvicorn", "uvicorn"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
    ("transformers", "transformers"),
    ("rasterio", "rasterio"),
    ("numpy", "numpy"),
    ("PIL", "pillow"),
)


def report(level: str, label: str, detail: str) -> None:
    print(f"{level:<4} {label}: {detail}")


def package_version(distribution: str) -> str:
    try:
        return version(distribution) or "installed (version metadata unavailable)"
    except PackageNotFoundError:
        return "installed (distribution metadata unavailable)"


def main() -> int:
    failures = 0
    expected = sys.version_info[:2] == (3, 12)
    report("PASS" if expected else "FAIL", "Python", platform.python_version())
    failures += not expected

    loaded: dict[str, object] = {}
    for module_name, distribution in REQUIRED_IMPORTS:
        try:
            loaded[module_name] = importlib.import_module(module_name)
            report("PASS", distribution, package_version(distribution))
        except Exception as exc:
            failures += 1
            report("FAIL", distribution, f"{type(exc).__name__}: {exc}")

    torch = loaded.get("torch")
    if torch is not None and hasattr(torch, "cuda"):
        cuda_available = bool(torch.cuda.is_available())  # type: ignore[attr-defined]
        report("PASS" if cuda_available else "WARN", "CUDA", "available" if cuda_available else "not available; CPU inference will be used")

    try:
        from huggingface_hub import try_to_load_from_cache

        required_files = ("config.json", "preprocessor_config.json", "model.safetensors")
        missing = [name for name in required_files if not isinstance(try_to_load_from_cache(MODEL_ID, name), str)]
        if missing:
            failures += 1
            report("FAIL", "Offline model cache", f"{MODEL_ID}; missing {', '.join(missing)}")
        else:
            report("PASS", "Offline model cache", f"{MODEL_ID}; required files present; no download attempted")
    except Exception as exc:
        failures += 1
        report("FAIL", "Offline model cache", f"{type(exc).__name__}: {exc}")

    report("PASS" if failures == 0 else "FAIL", "Overall", "offline environment ready" if failures == 0 else f"{failures} required check(s) failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
