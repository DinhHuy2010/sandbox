from python.lib.dhruntime3 import Runtime, JsonValue, MiddlewareState, NextMiddleware, AsyncRuntime
from tqdm import tqdm
from concurrent.futures import Future, wait

if __name__ == "__main__":
    runtime = Runtime()

    @runtime.on("success")
    def success_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        print(f"Success callback called with data: {data}")
        return {"status": "success", "received_data": data}

    @runtime.on("example_event")
    def example_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        print(f"Received event with data: {data}")
        return runtime.call("success", {"message": "Event processed successfully"})

    @runtime.use_middleware
    def example_auditer(state: MiddlewareState, next: NextMiddleware) -> JsonValue:
        # print(
        #     f"Auditing event '{state.event_name}' with callback '{state.callback_name}' and data: {state.data}"
        # )
        # result = state.callback(state.runtime, state.data)
        result = next()
        # print(f"Result of callback '{state.callback_name}': {result}")
        return result

    @runtime.use_middleware
    def example_logger(state: MiddlewareState, next: NextMiddleware) -> JsonValue:
        # print(
        #     f"Logging event '{state.event_name}' with callback '{state.callback_name}' and data: {state.data}"
        # )
        result = next()
        # print(f"Result of callback '{state.callback_name}': {result}")
        return result

    @runtime.on("long_time")
    def long_time_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        import random
        import time

        # print(f"Starting long time processing with data: {data}")
        time.sleep(random.uniform(0, 1))  # Simulate a long processing time
        # print(f"Finished long time processing with data: {data}")
        return {"status": "completed", "received_data": data}

    tasks: list[Future] = []
    aruntime = AsyncRuntime(runtime=runtime, max_workers=50)
    with aruntime:
        for i in range(500):
            task = aruntime.call("long_time", {"task_id": i})
            tasks.append(task)
        prog = tqdm(total=len(tasks), desc="Processing tasks", unit="task")
        with prog:
            try:
                while True:
                    done, not_done = wait(tasks, timeout=0.5)
                    prog.update(len(done) - prog.n)  # Update the progress bar
                    if len(not_done) == 0:
                        break
            except KeyboardInterrupt:
                print("Processing interrupted by user.")

    for task in tasks:
        if task.exception() is not None:
            print(f"Task {task} failed with error: {task.exception()}")
        else:
            print(f"Task {task} completed with result: {task.result()}")
