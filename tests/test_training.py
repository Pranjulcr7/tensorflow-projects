import json

import pytest

from overnight_agent.training import train, validate_dataset


def test_training_command_keeps_base_model_and_uses_adapter(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    row = {
        "messages": [{"role": "assistant", "content": "answer"}],
        "metadata": {"sources": ["fixture"]},
    }
    (data / "train.jsonl").write_text(json.dumps(row) + "\n")
    command = train({"model": "base-4bit", "data": str(data), "adapter_path": "adapter"})
    assert "--adapter-path" in command and "adapter" in command
    assert "--train" in command


def test_dataset_rejects_unsourced_targets(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"messages":[{"role":"assistant","content":"x"}]}\n')
    with pytest.raises(ValueError, match="sourced-answer"):
        validate_dataset(path)
