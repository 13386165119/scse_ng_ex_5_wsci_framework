"""WRITE, SELECT, COMPRESS and ISOLATE for a small IT support assistant."""
import json
import re
from wsci_common import BASE_DIR, KNOWLEDGE_DIR, QUESTION, ask_qwen, read_context

STATE_PATH = BASE_DIR / "state.json"
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "likely_cause": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "explanation": {"type": "string"},
    },
    "required": ["likely_cause", "steps", "explanation"],
    "additionalProperties": False,
}


def select_context(question):
    """Keyword selection is transparent, but is not semantic retrieval."""
    keywords = {
        "wifi_setup.txt": r"\b(wi[ -]?fi|eduroam|wireless)\b",
        "password_changes.txt": r"\b(passwords?|credentials?|authentication)\b",
        "printing.txt": r"\b(print|printing|printers?)\b",
        "vpn.txt": r"\bvpn\b",
        "email_setup.txt": r"\b(e-?mail|webmail|outlook)\b",
        "classroom_projectors.txt": r"\b(projectors?|hdmi|displays?|screens?)\b",
    }
    files = [KNOWLEDGE_DIR / name for name, pattern in keywords.items()
             if re.search(pattern, question, re.IGNORECASE)]
    if files or re.search(r"\b(status|outage|operational)\b", question, re.IGNORECASE):
        files.append(KNOWLEDGE_DIR / "service_status.txt")
    return files


def compress_context(context, question):
    if not context:
        return ""
    response = ask_qwen(
        "Summarize relevant documentation in at most 120 words. Keep the exact "
        "network name and applicable Windows menu path and Forget/reconnect steps. "
        "Include cached passwords, temporarily working signed-in devices, service "
        "status, and the account-lockout warning when present. No invented facts.",
        question, context,
    )
    compressed = (response.message.content or "").strip()
    # Do not claim compression if the model returned an expansion or nothing.
    return compressed if 0 < len(compressed) < len(context) else context


def load_state(path=STATE_PATH):
    if not path.exists():
        return {"diagnostic_context": {}, "report_context": {"completed_runs": 0}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or any(
        not isinstance(state.get(key), dict)
        for key in ("diagnostic_context", "report_context")
    ):
        raise ValueError("state.json must contain diagnostic_context and report_context objects")
    count = state["report_context"].get("completed_runs", 0)
    if type(count) is not int or count < 0:
        raise ValueError("completed_runs must be a non-negative integer")
    return state


def isolate_state(state, question, task="diagnostic"):
    """A diagnostic never receives reporting data or another problem's history."""
    if task == "report":
        return dict(state["report_context"])
    if task != "diagnostic":
        raise ValueError("Unknown task")
    diagnostic = state["diagnostic_context"]
    if diagnostic.get("problem") != question:
        return {}
    # Earlier model advice is not evidence that the user tried it or fixed anything.
    return {key: diagnostic[key] for key in ("problem", "last_response") if key in diagnostic}


def validate_answer(answer):
    if not isinstance(answer, dict) or set(answer) != set(ANSWER_SCHEMA["required"]):
        raise ValueError("Unexpected answer fields")
    if not all(isinstance(answer[key], str) and answer[key].strip()
               for key in ("likely_cause", "explanation")):
        raise ValueError("Cause and explanation must be nonempty strings")
    if not isinstance(answer["steps"], list) or not answer["steps"] or not all(
        isinstance(step, str) and step.strip() for step in answer["steps"]
    ):
        raise ValueError("Steps must be a nonempty list of nonempty strings")
    return answer


def main(question=QUESTION, state_path=STATE_PATH):
    state = load_state(state_path)
    relevant_state = isolate_state(state, question)
    selected_files = select_context(question)
    context = read_context(selected_files)
    compressed_context = compress_context(context, question)
    model_context = json.dumps({
        "knowledge": compressed_context,
        "previous_advice_not_verified_outcome": relevant_state,
    }, ensure_ascii=False)
    response = ask_qwen(
        "Return JSON with likely_cause, steps (a list), and explanation. "
        "Treat earlier model advice as unverified history. Do not assume steps were tried. "
        "If evidence is insufficient, say so and ask for clarification in steps.",
        question, model_context, ANSWER_SCHEMA,
    )
    answer = validate_answer(json.loads(response.message.content or ""))
    state["diagnostic_context"] = {
        "problem": question,
        "selected_files": [file.name for file in selected_files],
        "last_response": answer,
    }
    state["report_context"]["completed_runs"] = state["report_context"].get("completed_runs", 0) + 1
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    print("Selected files:", ", ".join(file.name for file in selected_files))
    print("Context characters:", len(context))
    print("Compressed context characters:", len(compressed_context))
    print("Final context characters (including isolated state):", len(model_context))
    print(json.dumps(answer, ensure_ascii=False, indent=2))
    return answer


if __name__ == "__main__":
    main()
