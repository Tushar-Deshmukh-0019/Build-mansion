def generate_python(ast):

    code = []

    for block in ast["blocks"]:

        # ---------------- ASSIGN ----------------
        if block["type"] == "assign":
            code.append(block["value"])

        # ---------------- WHILE ----------------
        elif block["type"] == "while":
            code.append(f"while {block['condition']}:")

            for line in block["body"]:
                line = line.strip()

                # CLEAN KEYWORDS
                line = line.replace("SET", "").strip()
                line = line.replace("THEN", "")
                line = line.replace("END IF", "")
                line = line.replace("END WHILE", "")
                line = line.replace("^", "**")

                # BREAK FIX
                if line.lower() == "break":
                    code.append("    break")
                    continue

                # IF inside WHILE
                if line.lower().startswith("if"):
                    cond = line.replace("if", "").strip()
                    code.append(f"    if {cond}:")
                    continue

                # PRINT FIX
                if line.lower().startswith("print"):
                    val = line.replace("PRINT", "").strip()
                    code.append(f"        print({val})")
                    continue

                # NORMAL LINE (assignment / dict / logic)
                if "=" in line:
                    code.append(f"    {line}")
                elif line:
                    code.append(f"    # {line}")

        # ---------------- IF ----------------
        elif block["type"] == "if":
            code.append(f"if {block['condition']}:")
            code.append(f"    print({block['true']})")

            if block["false"]:
                code.append("else:")
                code.append(f"    print({block['false']})")

        # ---------------- PRINT ----------------
        elif block["type"] == "print":
            val = block["value"].replace("PRINT", "").strip()
            code.append(f"print({val})")

        # ---------------- EXPRESSIONS ----------------
        elif block["type"] == "expr":
            code.append(f"# {block['value']}")

    return "\n".join(code)