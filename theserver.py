"""Prototype config schema for a dict-driven pure Python HTTP server.

The module-level ``config`` dict describes the server bind address, route table,
and global middleware:

``host``
    Host name or address to bind.
``port``
    TCP port to bind.
``routes``
    Mapping of URL path prefixes to route config dicts. Every route config has
    a ``type`` key that selects its remaining shape.
``middleware``
    Optional ordered list of callable references applied around requests.

Callable references use ``"module:object"`` for imported objects and
``":object"`` for objects in this config module.

Route types
-----------
``normal``
    Calls native server code.

    ``function``
        Callable reference for a handler. A native handler receives one request
        dict and returns a result dict.
    ``methods``
        Optional list of allowed HTTP methods.

``simple``
    Returns a fixed response dict from ``response``.

``static``
    Serves files below ``directory``.

    ``extra_response_headers``
        Optional headers added to static file responses.

``wsgi``
    Mounts the WSGI callable referenced by ``application``.

``asgi``
    Mounts the ASGI callable referenced by ``application``.

``advanced``
    Selects another route config from ``cases``. Case keys currently use the
    condition text shown by this prototype:

    ``method=METHOD``
        Match an HTTP method, for example ``method=GET``.
    ``header.NAME=VALUE``
        Match a request header value, for example
        ``header.x-custom=value``.
    ``default``
        Fallback case when no earlier condition matches.

Response dicts
--------------
A fixed ``simple`` response uses ``status``, ``headers``, and ``body``.
Native handler results add a ``type`` key so the server can distinguish result
kinds. The response result shape is:

.. code-block:: python

    {
        "type": "response",
        "status": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": b"Hello, World!",
    }

``body`` is bytes in this prototype. Route configs and response dicts are plain
Python dicts so values may stay Python-native instead of being limited to a
serialization format.
"""


def root(request):
    return {
        "type": "response",
        "status": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": b"Hello, World!",
    }


config = {
    "host": "localhost",
    "port": 8080,
    "routes": {
        "/": {"type": " normal", "function": ":root", "methods": ["GET"]},
        "/static": {
            "type": "static",
            "directory": "./static",
            "extra_response_headers": {
                "Cache-Control": "max-age=3600",
            },
        },
        # "/wsgi": {
        #     "type": "wsgi",
        #     "application": "my_wsgi_app:app",
        # },
        # "/asgi": {
        #     "type": "asgi",
        #     "application": "my_asgi_app:app",
        # },
        "/simple": {
            "type": "simple",
            "response": {
                "status": 200,
                "headers": {"Content-Type": "text/plain"},
                "body": b"Simple response",
            },
        },
        "/advanced": {
            "type": "advanced",
            "cases": {
                "method=GET": {
                    "type": "simple",
                    "response": {
                        "status": 200,
                        "headers": {"Content-Type": "text/plain"},
                        "body": b"GET response",
                    },
                },
                "method=POST": {
                    "type": "normal",
                    "function": ":my_post_handler",
                },
                "header.x-custom=value": {
                    "type": "simple",
                    "response": {
                        "status": 200,
                        "headers": {"Content-Type": "text/plain"},
                        "body": b"Custom header response",
                    },
                },
                "default": {
                    "type": "simple",
                    "response": {
                        "status": 400,
                        "headers": {"Content-Type": "text/plain"},
                        "body": b"Bad request",
                    },
                },
            },
        },
    },
    "middleware": [],
}

import theserver_implemation, __main__

theserver_implemation.serve(config, config_module=__main__)
