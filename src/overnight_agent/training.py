from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


def compatibility() -> dict:
    result = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
    }
    for package in ("mlx", "mlx-lm"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    result["training_ready"] = result["apple_silicon"] and bool(result["mlx-lm"])
    return result


def validate_dataset(path: str | Path) -> int:
    count = 0
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        messages = row.get("messages", [])
        if not messages or messages[-1].get("role") != "assistant":
            raise ValueError(f"line {line_number}: expected assistant target")
        if not row.get("metadata", {}).get("sources"):
            raise ValueError(f"line {line_number}: sourced-answer metadata is required")
        count += 1
    if count == 0:
        raise ValueError("dataset is empty")
    return count


def train(config: dict, execute: bool = False) -> list[str]:
    data = config["data"]
    validate_dataset(Path(data) / "train.jsonl")
    command = [
        "python",
        "-m",
        "mlx_lm.lora",
        "--model",
        config["model"],
        "--data",
        data,
        "--adapter-path",
        config["adapter_path"],
        "--train",
        "--iters",
        str(config.get("iters", 400)),
        "--batch-size",
        str(config.get("batch_size", 1)),
        "--num-layers",
        str(config.get("num_layers", 8)),
    ]
    if execute:
        status = compatibility()
        if not status["training_ready"]:
            raise RuntimeError(f"MLX training is not compatible with this host: {status}")
        subprocess.run(command, check=True)
    return command
