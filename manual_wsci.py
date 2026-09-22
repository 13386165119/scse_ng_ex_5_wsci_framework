"""SELECT: manually choose files relevant to the example question."""
from wsci_common import KNOWLEDGE_DIR, QUESTION, ask_qwen, read_context


def main():
    selected_files = [KNOWLEDGE_DIR / name for name in (
        "wifi_setup.txt", "password_changes.txt", "service_status.txt"
    )]
    context = read_context(selected_files)
    response = ask_qwen("Give the likely cause, concrete steps from the documentation, "
                        "and explain why the phone can still work. Keep the answer concise.", QUESTION, context)
    print("Context characters:", len(context))
    print(response.message.content)


if __name__ == "__main__":
    main()
