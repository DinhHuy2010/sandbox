# from abc import ABC, abstractmethod

# class Collectable(ABC):
#     @abstractmethod
#     def collect(self):
#         pass


# class Agent:
#     def __init__(self, name):
#         self.name = name
#         self.collected_items = []

#     def collect(self, collectable: Collectable):
#         d = collectable.collect()
#         self.collected_items.append(d)
#         print(f"{self.name} collected: {d}")


# class Movie(Collectable):
#     def __init__(self, title):
#         self.title = title

#     def collect(self):
#         return {"title": self.title}


# class Cinema:
#     def __init__(self, name):
#         self.name = name
#         self.movies = []

#     def add_movie(self, movie: Movie):
#         self.movies.append(movie)

#     def collect(self):
#         return {
#             "cinema": self.name,
#             "movies": [movie.collect() for movie in self.movies],
#         }

# agent = Agent("Alice")
# cinema = Cinema("Cineplex")
# cinema.add_movie(Movie("Inception"))
# cinema.add_movie(Movie("The Matrix"))
# agent.collect(cinema)

# db = sqlite://:memory:
# sql://query/{db}/SELECT * FROM movies

from typing import Annotated, Any

import fastapi


app = fastapi.FastAPI()
