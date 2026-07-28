# from typing import Any


# request: Any = ...


# def handler():
#     global request
#     print(f"Handling request: {request}")
#     # Simulate processing the request
#     response = "HTTP/1.1 200 OK\nContent-Type: text/plain\n\nHello, World!"
#     print(f"Sending response:\n{response}")


# def serve(handler, host, port):
#     global request
#     print(f"Serving on {host}:{port} with handler {handler.__name__}")
#     for _ in range(3):  # Simulate handling 3 requests
#         print("Waiting for a request...")
#         # Simulate receiving a request
#         request = "GET / HTTP/1.1"
#         print(f"Received request: {request}")
#         handler()
#     print("Server shutting down.")

# serve(handler, "localhost", 8080)

# template = """
# api("GET:/" -> response("Hello, World!"))
# api("GET:/home?required={required}[&name={name}]" -> response(html("<h1>Welcome to the Home Page (name: {name}, required: {required})</h1>")))
# api("GET:/about" -> response(html("<h1>About Us</h1><p>This is the about page.</p>")))
# api("GET:/api/v1/data?type={type}" -> response(json({"data": "Here is your data of type {type}"})))
# api("GET:/api/v1/items?category={category}&limit={limit}" -> response(json({"items": "Here are your items in category {category} with limit {limit}"})))
# api("POST:/api/v1/items", body={name, description} -> response(json({"message": "Item created with name {name} and description {description}"})))
# api("PUT:/api/v1/items/{id}", body={name, description} -> response(json({"message": "Item with id {id} updated with name {name} and description {description}"})))
# api("DELETE:/api/v1/items/{id}" -> response(json({"message": "Item with id {id} deleted"})))
# api("GET:/search?query={query}" -> response(
#     html("<h1>Search Results for '{query}'</h1>"),
#     sql("SELECT * FROM items WHERE name LIKE '%{query}%'") -> (
#         html("<ul>{{htmlize(results)}}</ul>")
#         if results else html("<p>No results found.</p>")
#     )
# ))
# api("GET:/users/{user_id}/profile" -> response(
#     html("<h1>User Profile for User ID {user_id}</h1>"),
#     sql("SELECT * FROM users WHERE id = {user_id}") -> (
#         html("<p>Name: {name}</p><p>Email: {email}</p>")
#         if name and email else html("<p>User not found.</p>")
#     )
# ))
# router("/admin", security: basic {username: admin, password: secret}) {
#     api("GET:/dashboard" -> response(html("<h1>Admin Dashboard</h1><p>Welcome to the admin dashboard.</p>")))
#     api("POST:/users", body={username, password} -> response(json({"message": "Admin created user with username {username}"})))
# }
# router("/rpc", security: token {token: abc123}) {
#     api("POST:/call", body={method, params} -> response(json({"result": "RPC call to method {method} with params {params}"})))
# }
# """
# xml = """
# <api appname="MyApp" version="1.0" host="localhost" port="8080">
#     <endpoint method="GET" path="/">
#         <response type="text/plain">Hello, World!</response>
#     </endpoint>
#     <endpoint method="GET" path="/home">
#         <query required="true" name="name" />
#         <response type="html">
#             <h1>Welcome to the Home Page (name: {name}, required: {required})</h1>
#         </response>
#     </endpoint>
#     <endpoint method="GET" path="/about">
#         <response type="html">
#             <h1>About Us</h1>
#             <p>This is the about page.</p>
#             <h2>Links:</h2>
#             <div>
#                 <a href="/home?required=true&name=Alice">Home (Alice)</a>
#                 <a href="/home?required=true&name=Bob">Home (Bob)</a>
#             </div>
#         </response>
#     </endpoint>
#     <endpoint method="GET" path="/api/v1/data">
#         <query name="type" />
#         <response type="json">
#             {"data": "Here is your data of type {type}"}
#         </response>
#     </endpoint>
#     <endpoint method="GET" path="/api/v1/items">
#         <query name="category" />
#         <query name="limit" />
#         <response dynamic="true" type="json">
#             // JavaScript
#             // use send() to send the response
#             const context = getContext();
#             const category = context.query.category;
#             const limit = context.query.limit;
#             const items = getItemsFromDatabase(category, limit);
#             send({status: 200, body: JSON.stringify({items})});
#         </response>
#     </endpoint>
# </api>
# """
# print(template)

"""
route("/", method: "GET") {
    response(200, "Hello, World!")
}
route("/home", method: "GET", schema: {
    query: {
        required: {type: "string"},
        name: {type: "string", optional: true}
    }
}) {
    response(200, html("<h1>Welcome to the Home Page (name: {name}, required: {required})</h1>"))
}
route("/about", method: "GET") {
    response(200, html("<h1>About Us</h1><p>This is the about page.</p>"))
}
router("/api/v1") {
    route("/data", method: "GET", schema: {
        query: {
            type: {type: "string", optional: true}
        }
    }) {
        response(200, json({"data": "Here is your data of type {type}"}))
    }
    route("/items", method: "GET", schema: {
        query: {
            category: {type: "string", optional: true},
            limit: {type: "number", optional: true}
        }
    }) {
        response(200, json({"items": "Here are your items in category {category} with limit {limit}"}))
    }
}
router("/admin") {
    security: basic {username: admin, password: secret}
    route("/dashboard", method: "GET") {
        response(200, html("<h1>Admin Dashboard</h1><p>Welcome to the admin dashboard.</p>"))
    }
    route("/users", method: "POST", schema: {
        body: {
            username: {type: "string"},
            password: {type: "string"}
        }
    }) {
        response(200, json({"message": "Admin created user with username {username}"}))
    }
}
route("/ws", protocol: "websocket") {
    when (ws.before_accept) {
        log("WebSocket connection is about to be accepted")
        ws.accept()
    }
    when (ws.message) {
        message = ws.receive()
        log("Received WebSocket message: {message}")
        ws.send("Echo: {message}")
    }
    when (ws.closed) {
        log("WebSocket connection closed")
    }
}
serve(host: "localhost", port: 8080) {
    when (server.stopped) {
        log("Server stopped")
    }
}
main() {
    log("Starting server...")
}
"""


class Router: ...


class Mount(Router):
    def index(self):
        self.status(200)
        self.header("Content-Type", "text/plain")
        self.body(b"Hello, World!")
        self.end()


class HelloWorld(Router, path="/"):
    def index(self):  # /
        self.status(200)
        self.header("Content-Type", "text/plain")
        self.body(b"Hello, World!")
        self.end()

    mount = Mount()  # /mount


def server(root_router: Router, host: str, port: int):
    print(f"Serving on {host}:{port} with root router {root_router.__class__.__name__}")
    # Simulate server loop
    for _ in range(3):  # Simulate handling 3 requests
        print("Waiting for a request...")
        # Simulate receiving a request
        request_path = "/"
        print(f"Received request for path: {request_path}")
        if request_path == "/":
            root_router.index()
        elif request_path == "/mount":
            root_router.mount.index()
        else:
            print("404 Not Found")
    print("Server shutting down.")

