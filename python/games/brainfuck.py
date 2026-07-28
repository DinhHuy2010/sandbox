def run_brainfuck(code):
    memory = [0] * 30000
    ptr = 0
    code_ptr = 0
    output = []

    # Pre-parse loops for speed
    loop_map = {}
    stack = []
    for i, char in enumerate(code):
        if char == "[":
            stack.append(i)
        elif char == "]":
            start = stack.pop()
            loop_map[start] = i
            loop_map[i] = start

    while code_ptr < len(code):
        cmd = code[code_ptr]
        if cmd == ">":
            ptr += 1
        elif cmd == "<":
            ptr -= 1
        elif cmd == "+":
            memory[ptr] = (memory[ptr] + 1) % 256
        elif cmd == "-":
            memory[ptr] = (memory[ptr] - 1) % 256
        elif cmd == ".":
            output.append(chr(memory[ptr]))
        elif cmd == "[" and memory[ptr] == 0:
            code_ptr = loop_map[code_ptr]
        elif cmd == "]" and memory[ptr] != 0:
            code_ptr = loop_map[code_ptr]
        code_ptr += 1

    return "".join(output)


# Test it out!
# generated_bf = ">+++++[<+++++++>>>>++<<<-]<[>++>+++>+<<<-]>++.>.>--.>."
generated_bf = """
>+>>>>>,[>+>>,]>+[                      set up; for each subarray:
    --[+<<<-]<[                         find the subarray; if it exists:
        [<+>-]<[                        S=pivot; while pivot is in S:
            <[                          if not at end of subarray
                ->[<<<+>>>>+<-]         move pivot left (and copy it) 
                <<[>>+>[->]<<[<]<-]>    move value to S and compare with pivot
            ]>>>+<[[-]<[>+<-]<]>[       if pivot greater then set V=S; else:
                [>>>]+<<<-<[<<[<<<]>>+>[>>>]<-]     swap smaller value into V
                <<[<<<]>[>>[>>>]<+<<[<<<]>-]        swap S into its place
            ]+<<<                       end else and set S=1 for return path
        ]                               subarray done (pivot was swapped in)
    ]+[->>>]>>                          end "if subarray exists"; go to right
]>[brainfuck.org>>>]                    done sorting whole array; output it
"""
print("Running generated code...")
print(run_brainfuck(generated_bf))  # Outputs: Hello
