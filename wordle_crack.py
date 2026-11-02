
from collections import Counter
from itertools import product
from secrets import choice

# Import from your previous Wordle program
from wordle import WORDS, evaluate


def pattern(guess, answer):
    return tuple(evaluate(guess, answer))


def best_guess(candidates, allowed_words):
    """
    Choose a guess that minimizes the expected
    number of remaining possible answers.
    """
    best_word = None
    best_score = float("inf")

    for guess in allowed_words:
        buckets = Counter(
            pattern(guess, answer)
            for answer in candidates
        )

        # Expected remaining candidates
        score = sum(n * n for n in buckets.values()) / len(candidates)

        if guess in candidates:
            score -= 0.001  # Tie-breaker

        if score < best_score:
            best_score = score
            best_word = guess

    return best_word


def crack(secret, words):
    candidates = list(words)

    for attempt in range(1, 7):
        guess = best_guess(candidates, words)
        feedback = pattern(guess, secret)

        print(f"{attempt}. {guess.upper()} -> {feedback}")

        if guess == secret:
            print(f"CRACKED in {attempt} attempts!")
            return attempt

        candidates = [
            word for word in candidates
            if pattern(guess, word) == feedback
        ]

        print(f"   Remaining: {len(candidates)}")

    print("Failed!")
    return None


if __name__ == "__main__":
    secret = choice(WORDS)
    crack(secret, WORDS)
