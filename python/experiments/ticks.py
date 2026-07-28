# def Person(name, age):
#     data = {"name": name, "age": age}

#     def get_name():
#         return data["name"]

#     def get_age():
#         return data["age"]

#     def set_name(new_name):
#         data["name"] = new_name

#     def set_age(new_age):
#         data["age"] = new_age

#     def Person__object(*args, **kwargs):
#         raise NotImplementedError(
#             "This is not a class, but a function that returns an object."
#         )

#     Person__object.get_name = get_name
#     Person__object.get_age = get_age
#     Person__object.set_name = set_name
#     Person__object.set_age = set_age
#     return Person__object


# from functools import partial


# def __create_AWS_factory(AWS, name, desc, module):
#     real_constructor = None

#     def factory(*args, **kwargs):
#         nonlocal real_constructor
#         if real_constructor is None:
#             real_module = AWS._load_module(module)
#             real_constructor = getattr(real_module, "AWS_factory_constructor")
#         return real_constructor(*args, **kwargs)

#     factory.name = name
#     factory.desc = desc
#     factory.module = module
#     return factory


# def __discover_AWS_factories():
#     # In a real implementation, this would discover factories dynamically.
#     # For this example, we'll just return a hardcoded list.
#     return [
#         ("S3", "AWS S3", "s3_module"),
#         ("EC2", "AWS EC2", "ec2_module"),
#     ]


# def AWS():
#     if not getattr(AWS, "_injected", False):
#         raise RuntimeError("AWS is already injected.")

#     @partial(AWS.__setattr__, "_load_module")
#     def _load_module(module):
#         from types import ModuleType

#         return ModuleType("__AWS_internal." + module, "")

#     for name, desc, module in __discover_AWS_factories():
#         factory = __create_AWS_factory(AWS, name, desc, module)
#         setattr(AWS, name, factory)

#     AWS._injected = True


# # AWS._injected = False
# AWS()

# p = AWS.S3("my-bucket")
# req = p.NewRequest("GetObject", {"Key": "my-object"})
# p.SendRequest(req)
# p = req.GetLastResponse()
# print(p.status_code)

# person = Person("Alice", 30)
# print(person.get_age())


# import atexit


# def print_delayed(*args, **kwargs):
#     called = False

#     def wrapper():
#         nonlocal called
#         if not called:
#             called = True
#             print(*args, **kwargs)

#     atexit.register(wrapper)
#     return wrapper


def delayed(func, /, *args, **kwargs):
    def wrapper():
        return func(*args, **kwargs)

    return wrapper


futures = []


def future(func, /, *args, **kwargs):
    called = False

    def daemon():
        nonlocal called
        if not called:
            called = True
            return func(*args, **kwargs)

    futures.append(daemon)
    return daemon


def a_function():
    def inner(a, b):
        print("This is a future function.")
        return a + b

    p = future(inner, 1, 2)
    print(p())


futures.extend(
    [
        future(print, "Hello, world!"),
        future(print, "Goodbye, world!"),
        future(a_function),
    ]
)


def event_loop():
    while futures:
        task = futures.pop(0)
        value = task()
        yield task, value


for _ in event_loop():
    print(_)

# hello = print_delayed("Hello, world!")
# hello()  # This will print "Hello, world!" when called
# print_delayed("Hello, world!")  # This will print "Hello, world!" when the program exits
# print_delayed(
#     "Goodbye, world!"
# )  # This will print "Goodbye, world!" when the program exits
