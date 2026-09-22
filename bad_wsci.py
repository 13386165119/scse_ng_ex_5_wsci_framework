"""Baseline: give Qwen every knowledge file, including irrelevant material."""
from wsci_common import KNOWLEDGE_DIR, QUESTION, ask_qwen, read_context


def main():
    context = read_context(sorted(KNOWLEDGE_DIR.glob("*.txt")))
    response = ask_qwen("Give the likely cause, concrete steps from the documentation, "
                        "and explain why the phone can still work. Keep the answer concise.", QUESTION, context)
    print("Context characters:", len(context))
    print(response.message.content)


if __name__ == "__main__":
    main()
