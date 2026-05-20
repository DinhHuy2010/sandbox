from werkzeug.wrappers import Response


def hello(context):
    return Response("Hello, World!")


def middleware_one(ctx, next):
    print("Middleware One")
    o = next(ctx)
    return o


hello.__endpoint__ = {"route": "/", "methods": ["GET"]}
__middlewares__ = [middleware_one]
