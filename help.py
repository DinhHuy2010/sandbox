from typing import Annotated, TypeAlias


class Nothing:
    def __init__(self, **kwds):
        pass

    def __call__(self, *args, **kwds):
        return self

    def __getattr__(self, name):
        return self

    def __getitem__(self, key):
        return self

    def __str__(self):
        return "Nothing"

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    def __setitem__(self, key, value):
        pass

    def __setattr__(self, name, value):
        pass

    def __delitem__(self, key):
        pass

    def __delattr__(self, name):
        pass


NotAnnotationForm: TypeAlias = Nothing

nothing = Nothing()
p = nothing.library
books = p.catalog("Python").books(
    filter=nothing.query.where(
        nothing.query.fields.author == nothing.datatypes.string("Guido van Rossum")
    )
)
resp = books.execute(outfile="python://self/books_iterator?format=iterator")
if resp.get_field("ok"):
    for book in nothing.self.books_iterator:
        toc = book.toc().execute(outfile="python://return?format=rich-objects")
        for i in toc.chapters().execute(outfile="python://return?format=rich-objects"):
            print(i.title().execute(outfile="python://return?format=string"))
            page_obj = i.page().execute(
                outfile="python://return?format=rich-objects&resolve-ref=1"
            )
            resp = page_obj.content().execute(
                outfile=f"python://open/page{i.index().execute(outfile='python://return?format=string')}.txt?format=string"
            )
            if resp.get_field("ok"):
                print(resp.get_field("file"))

ai = nothing.ai
gemma = ai.model("google.gemma4")


@gemma.tool(
    "python.execute",
    description="Execute Python code and return the result.",
    schema={
        "code": {"type": "string", "description": "The Python code to execute."},
        "python_version": {
            "type": "string",
            "description": "The Python version to use for execution (e.g., '3.8', '3.9', '3.10').",
            "default": "3.10",
        },
    },
    media_type="application/json",
)
def python_execute(params):
    python_version = params.python_version.unwrap_or("3.10")
    env = nothing.pyenv.new(
        python_version,
        policy={
            "no": {
                "import": True,
                "open": True,
                "eval": True,
                "exec": True,
                "pickle": True,
            },
            "allow": {"builtins": True, "math": True, "datetime": True},
        },
    )
    # path = env.execute(outfile="python://return?format=pathlib-path")
    out = nothing.pyenv.run(env=env, code=params.code)
    return out.execute(outfile="python://return?format=json&channel=all")


o = gemma.chat("Hello, Gemma! Can you execute some Python code for me?").execute(
    outfile="python://return?format=string(mime:text/plain)"
)
print(o)

server = nothing.server

server.route().accept(
    methods=["GET", "POST"],
    media_type={
        "application/json": server.modeling.schema("json").define(
            {"message": {"type": "string", "description": "The message to echo back."}}
        ),
        "text/plain": server.modeling.schema("text").match(
            r"^(?P<message>.+)$", flags=nothing.re.MULTILINE
        ),
        "multipart/form-data": server.modeling.schema("form").define(
            {"message": {"type": "string", "description": "The message to echo back."}}
        ),
        "application/x-www-form-urlencoded": server.modeling.schema("form").define(
            {"message": {"type": "string", "description": "The message to echo back."}}
        ),
    },
    user_agent_match=r"^EchoClient/1\.0$",
).where(
    method="POST",
    then=lambda req: nothing.server.response(
        content=req.get_field("message"), media_type="text/plain"
    ),
).where(
    method="GET",
    then=lambda req: nothing.server.response(
        content="Send a POST request with a message to echo back!",
        media_type="text/plain",
    ),
).save("/echo")


payment = nothing.payment
out = (
    payment.build(
        nothing.datatypes.string(
            "stripe:token={{secrets.stripe_token}}",
            evaluation_options={"secrets": "python://self/secrets?format=dict"},
        )
    )
    .charge(
        amount=1000,
        currency="usd",
        source="tok_visa",
        description="Test charge",
    )
    .execute(outfile="python://return?format=json")
)

ui = nothing.ui
window = ui.window()


@window.button("Click me!")
def on_click():
    print("Button was clicked!")


@window.form("Enter your name:")
def on_input(name):
    print(f"Hello, {name}!")


@window.scroll("Scrollable content here...")
def on_scroll():
    print("Scrolled!")


window.show()

plot = nothing.plot
fig = plot.figure().plot(
    x=[1, 2, 3, 4, 5],
    y=[10, 20, 15, 25, 30],
    kind="line",
    title="Sample Plot",
    xlabel="X-axis",
    ylabel="Y-axis",
)
fig.execute(outfile="python://open/sample_plot.png?format=png")

# same as: map, car = nothing.map, nothing.car
map, car = nothing.meta.autogateway()
acar = car.connect("tesla:model_s")
acar.with_config(speed=100, ac=27)
route = map.route(
    map.point(37.7749, -122.4194),  # San Francisco
    map.point(34.0522, -118.2437),  # Los Angeles
).with_config(avoid="highways", backend=map.backends["osmf"])
acar.drive(route, mode="autonomous+oversight").ft(ai=gemma)


air = nothing.air
flights = air.flights(origin="JFK", destination="SIN", date="1999-12-31").execute(
    outfile="python://return?format=json"
)
for flight in flights:
    print(
        f"Flight {flight.get_field('flight_number')} from {flight.get_field('origin')} to {flight.get_field('destination')} at {flight.get_field('departure_time')}"
    )
flight = nothing.random.choice(flights)
booking = flight.book(
    passenger=nothing.datatypes.object(
        name="John Doe",
        email="john.doe@example.com",
        passport_number="X12345678",
    ),
    payment_method=nothing.datatypes.object(
        type="credit_card",
        card_number="4111111111111111",
        expiry_date="12/25",
        cvv="123",
    ),
).execute(outfile="python://return?format=json")
nothing.teleport.goto(point=booking.get_field("seat").to_map_point()).ft(ai=gemma)

golang = nothing.golang


@golang.package("main")
def package(ctx: Annotated[NotAnnotationForm, golang.dtypes.Context]):
    ctx.go_import("fmt")
    ctx.go_import("net/http")

    @golang.function("Hello")
    def hello():
        return "Hello from Go!"

    @golang.function("Add")
    def add(
        a: Annotated[NotAnnotationForm, golang.dtypes.int64],
        b: Annotated[NotAnnotationForm, golang.dtypes.int64],
    ) -> Annotated[NotAnnotationForm, golang.dtypes.int64]:
        return a + b

    @golang.function("Main")
    def main(
        __go_fmt: Annotated[NotAnnotationForm, golang.dtypes.Package("fmt")],
        __go_http: Annotated[NotAnnotationForm, golang.dtypes.Package("net/http")],
    ):
        __go_fmt.Println("Starting server on :8080")

        def handler(
            w: Annotated[NotAnnotationForm, golang.dtypes.Interface],
            r: Annotated[NotAnnotationForm, golang.dtypes.Interface],
        ):
            w.Write(golang.dtypes.byte("Hello, World!"))

        __go_http.HandleFunc("/", handler)
        __go_http.ListenAndServe(":8080", None)

    return golang.package.export([hello, add, main])


bin_file = golang.build(package).execute(
    outfile="python://return?format=binary(mime:application/octet-stream)"
)
server.route().accept(methods=["GET"], media_type="application/octet-stream").where(
    method="GET",
    media_type="application/octet-stream",
    then=lambda req: nothing.server.staticfile(
        content=bin_file,
        filename="golang_bin",
        media_type="application/octet-stream",
    ),
).save("/download-golang-bin")

s = server.build()
loop = s.serve(port=8080)
while loop.running():
    event = loop.events.get()
    loop.tick()
    print(f"Received event: {event.type} at {event.timestamp}")

loop.stop()

cache = nothing.cache
sandbox = nothing.sandbox

store = cache.memoize(ttl=3600)


@sandbox.enviroment("""
python = Python(3.10)
policy = Policy(isolated | strict)
os = Ubuntu(22.04)
env = (os+python)@policy
output(env)
""")
@sandbox.when("timeout>time(5s)", sandbox.actions.stop())
@store.memoize_this("fibonacci")
def fibonacci(
    n: Annotated[NotAnnotationForm, nothing.datatypes.int(kind="64bit")],
) -> Annotated[NotAnnotationForm, nothing.datatypes.int(kind="64bit")]:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


db = nothing.database


@db.table("users")
def User(
    id: Annotated[NotAnnotationForm, db.dtypes.int64(primary_key=True)],
    name: Annotated[NotAnnotationForm, db.dtypes.string],
    email: Annotated[NotAnnotationForm, db.dtypes.string(unique=True)],
):
    return db.table.export(
        [id, name, email],
        views=db.views("id", "name", "email"),
        indexes=db.index("email"),
    )


contract = db.new_connection_contract(
    "python://self", "postgres://user:password@localhost:5432/mydb"
)
contract.register(User)
contract.enforce()
connection = contract.connect()

u = User(id=1, name="Alice", email="alice@example.com")
connection.insert(u)
connection.commit()
result = connection.query(User).where(User.name == "Alice")
for user in result.execute(outfile="python://return?format=rich-objects"):
    print(
        f"User {user.get_field('id')}: {user.get_field('name')} <{user.get_field('email')}>"
    )
contract.terminate(close_connection=True)
connection.close()

md = nothing.markdown

md_text = """
# Sample Markdown Document

...with python

```python[3.12,isolated|strict]
print("Hello, Markdown!")
x = 5
```

Above will evaluate as "Hello, markdown!"
x value: [!python.x]

also

```go[1.20,isolated|strict]
package main

import "fmt"

const PI = 3.14;

func main() {
    fmt.Println("Hello, Markdown with Go!");
}

```

PI: [!go.PI]

"""

html = md.render(md_text).execute(outfile="python://return?format=html")

# Training LLM

ai = nothing.ai
model = ai.model("openai.gpt4")
# load every datasets from Kaggle and train on them (just for demonstration, not recommended in practice)
dataset = ai.dataset("kaggle/*")
training_job = (
    model.train(dataset)
    .with_config(
        epochs=3,
        batch_size=32,
        learning_rate=1e-5,
        evaluation_strategy="epoch",
        save_strategy="epoch",
    )
    .execute(outfile="python://return?format=json")
)
training_job_id = training_job.get_field("job_id")
print(f"Started training job with ID: {training_job_id}")
while True:
    status = ai.training_job_status(training_job_id).execute(
        outfile="python://return?format=json"
    )
    print(f"Training job status: {status.get_field('status')}")
    if status.get_field("status") in ["completed", "failed"]:
        break
    nothing.time.sleep(60)  # Wait for 1 minute before checking again

p = model.chat("Hello, can you tell me about the training process?").execute(
    outfile="python://return?format=string(mime:text/plain)"
)
print(p)
p = model.chat("Can you summarize the training results?").execute(
    outfile="python://return?format=string(mime:text/plain)"
)
print(p)
p = model.chat("What dataset did you train on?").execute(
    outfile="python://return?format=string(mime:text/plain)"
)
print(p)

# archive

archive, fs = nothing.meta.autogateway()

a = archive.open("zip://path/to/archive.zip").execute(
    outfile="python://return?format=rich-objects"
)
files = fs.glob.recursive("*").execute(outfile="python://return?format=rich-objects")
a.add_all(files)
a.commit()

# and finally, ...
nothing.self_destruct()
