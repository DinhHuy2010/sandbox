import random

from python.lib.okwhatever3 import LoopContinue as c
from python.lib.okwhatever3 import (
    complex_cond as cc,
    error as e,
    meanwhile as w,
    nil as n,
    on_error as oe,
    simple_cond as sc,
)
from types import new_class as nc

sc(__name__=="__main__",lambda MAX=100:(p:=print,number:=random.randint(1, MAX),wi:=nc("wi", (Exception,)),p("Welcome to the Guessing Game!"),p(f"I'm thinking of a number between 1 and {MAX}."),p("Try to guess it!"),oe(lambda:w(lambda: True,lambda:oe(lambda:(guess:=oe(lambda: int(input("Enter your guess: ")),(ValueError,lambda _:(p("Please enter a valid integer."),e(c())))),cc((guess<number,lambda:(p("Too low! Try again."),e(c()))),(guess>number,lambda:(p("Too high! Try again."),e(c()))),(guess==number,lambda:(p("Congratulations! You guessed it!"),e(wi()))))),(c, n))),(wi,lambda _: p("You won the game!"))))[-1],n)  # fmt: off
