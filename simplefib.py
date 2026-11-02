import sys


class simplefib:
    def __init__(self):
        self.level = 0
        self.cache = {}

    def _p(self, n, message):
        print(f"[l={self.level},n={n}] {message}")

    def calculate(self, n):
        if n < 0:
            raise ValueError("Input must be a non-negative integer.")
        if n <= 1:
            self._p(n, f"returning {n}")
            return n
        elif n in self.cache:
            self._p(n, f"returning cached value {self.cache[n]}")
            return self.cache[n]
        else:
            self._p(n, "calculating fibonacci")
            self.level += 1
            try:
                result = self.calculate(n - 1) + self.calculate(n - 2)
            finally:
                self.level -= 1

            self.cache[n] = result
            self._p(n, f"returning {result}")
            return result


def fib(n):
    fib_calculator = simplefib()
    return fib_calculator.calculate(n)

sys.setrecursionlimit(20000)
print(fib(10))
