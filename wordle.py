
import random

WORDS = [
    "apple", "grape", "chair", "table", "house",
    "water", "light", "bread", "plant", "stone",
    "cloud", "smile", "train", "brain", "flame",
    "world", "dream", "green", "mouse", "river",
    "beach", "music", "heart", "space", "tiger",
    "piano", "ocean", "clock", "night", "sweet",
    "fruit", "earth", "dance", "happy", "party",
]

GREEN = "\033[42;30m"
YELLOW = "\033[43;30m"
GRAY = "\033[100;37m"
RESET = "\033[0m"


def evaluate(guess, answer):
    result = ["gray"] * 5
    remaining = {}

    for i in range(5):
        if guess[i] == answer[i]:
            result[i] = "green"
        else:
            remaining[answer[i]] = remaining.get(answer[i], 0) + 1

    for i in range(5):
        if result[i] == "green":
            continue

        letter = guess[i]
        if remaining.get(letter, 0) > 0:
            result[i] = "yellow"
            remaining[letter] -= 1

    return result


def display(guess, result):
    colors = {
        "green": GREEN,
        "yellow": YELLOW,
        "gray": GRAY,
    }

    for letter, status in zip(guess, result):
        print(f"{colors[status]} {letter.upper()} {RESET}", end=" ")
    print()


def play():
    answer = random.choice(WORDS)

    print("\n========== WORDLE ==========")
    print("Guess the 5-letter word!")
    print("You have 6 attempts.\n")
    print("🟩 Correct position")
    print("🟨 Wrong position")
    print("⬛ Not in word\n")

    for attempt in range(1, 7):
        while True:
            guess = input(f"Attempt {attempt}/6: ").strip().lower()

            if len(guess) == 5 and guess.isascii() and guess.isalpha():
                break

            print("Please enter exactly 5 English letters.")

        result = evaluate(guess, answer)
        display(guess, result)

        if guess == answer:
            print(f"\n🎉 You won in {attempt}/6 attempts!")
            return

    print(f"\n💀 Game over! The word was {answer.upper()}.")


if __name__ == "__main__":
    try:
        while True:
            play()
            again = input("\nPlay again? (y/n): ").strip().lower()
            if again != "y":
                print("Goodbye!")
                break
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
