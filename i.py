import prompt_toolkit as pt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class MyCompleter(Completer):
    def get_completions(self, document: Document, complete_event):
        char = document.get_word_before_cursor()
        if char:
            yield Completion(char, start_position=-len(char))


s = pt.PromptSession(completer=MyCompleter())
text = pt.HTML("<b>Enter something:</b> ")
while True:
    try:
        text = s.prompt(text)
        print(f"You entered: {text}")
    except (KeyboardInterrupt, EOFError):
        break
