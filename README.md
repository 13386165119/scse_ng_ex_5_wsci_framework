# Exercise #5: WSCI Framework

This completes the three demonstrations in the teacher's PDF using local Qwen through Ollama.

## Run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3:0.6b
# Start `ollama serve` in another terminal if Ollama is not already running.
.\.venv\Scripts\python.exe bad_wsci.py
.\.venv\Scripts\python.exe manual_wsci.py
.\.venv\Scripts\python.exe smarter_wsci.py
.\.venv\Scripts\python.exe -m unittest -v
```

The default model is `qwen3:0.6b`. Set `$env:OLLAMA_MODEL` to another installed Qwen model if needed. CPU inference is used for compatibility with this computer. Paths are resolved relative to the source files, so launching from another directory is supported.

## What each version does

- `bad_wsci.py`: supplies all seven knowledge files to Qwen as a baseline.
- `manual_wsci.py`: manually selects Wi-Fi setup, password changes, and service status.
- `smarter_wsci.py`: selects by keywords, asks Qwen to compress the text, supplies only relevant saved diagnostic history, validates structured JSON, and saves it to `state.json`.
- `wsci_common.py`: shared model settings and knowledge-file reading.

## WSCI

- **WRITE:** save the problem, selected filenames, and structured response in `diagnostic_context`; save the run count separately in `report_context`. The file is read on the next run. Invalid model output does not overwrite saved state.
- **SELECT:** choose existing files using case-insensitive keyword rules. Unknown topics get no invented knowledge; the model is asked to request clarification when evidence is insufficient.
- **COMPRESS:** Qwen extracts relevant information before the final answer. If its result is empty or longer, retain the selected original text. Printed counts distinguish selected knowledge, compressed knowledge, and the final context including saved history.
- **ISOLATE:** `isolate_state` gives diagnostics only the same problem's previous advice, never reporting statistics. A reporting task gets only `report_context`. A different question does not inherit the previous case. Prior advice is explicitly unverified and does not mean a step was tried or a case was resolved.

`state.json` is generated locally and ignored by Git because future questions can contain personal information. The supplied service-status text describes the classroom exercise, not a live university outage check.

## Verification and observations

The teacher template has no automated tests. Six added offline tests cover topic selection, state isolation, compression fallback, JSON validation, persistence/reuse, and damaged-state handling. Actual Qwen runs are recorded under `validation/`.

The full knowledge context is 4,180 characters. Manual selection reduces it to 2,158 characters (about 48%). Compression and the final context sizes are recorded separately in the smarter run log; saved history can make the final prompt longer than the compressed knowledge alone.

These checks establish program behavior and valid output structure, not guaranteed factual correctness. The small 0.6B model sometimes gives incomplete steps or an imprecise explanation of the working phone. The source-backed explanation is that already signed-in services may keep working temporarily; the phone working does not establish that it saved the new password. Compression is also model-generated and can omit facts. Compare answers against the supplied knowledge before relying on them.

AI assistance was used to implement and validate this exercise. Review the code and outputs before submission.

Fresh-state smoke run: selected knowledge 2,158 characters, compressed knowledge 651, final context 714. The generated JSON passed structural validation, but included an invented Windows menu path. This is a model-quality failure, not a verified troubleshooting procedure. The source says Settings > Network & Internet > Wi-Fi, then forget the eduroam network and reconnect with current credentials. Saved-history runs and fresh-state runs are logged separately; neither is a factual-quality guarantee.
