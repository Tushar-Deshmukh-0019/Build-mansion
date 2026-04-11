def parse_logic(text):
    lines = text.strip().split("\n")

    ast = {
        "type": "program",
        "blocks": []
    }

    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        lower = line.lower()

        # ---------------- ASSIGN ----------------
        if lower.startswith("set") or ("=" in line and "if" not in lower):
            ast["blocks"].append({
                "type": "assign",
                "value": line.replace("SET", "").strip()
            })
            i += 1
            continue

        # ---------------- WHILE ----------------
        if lower.startswith("while"):
            condition = line.lower().replace("while", "").replace("do", "").strip()

            i += 1
            body = []

            while i < len(lines) and "end while" not in lines[i].lower():
                body.append(lines[i].strip())
                i += 1

            ast["blocks"].append({
                "type": "while",
                "condition": condition,
                "body": body
            })

            i += 1
            continue

        # ---------------- IF ----------------
        if "if" in lower and "then" in lower:
            try:
                condition = line.split("if")[1].split("then")[0].strip()
                after = line.split("then")[1]

                true_part = after.split("else")[0].strip() if "else" in after else after.strip()
                false_part = after.split("else")[1].strip() if "else" in after else None

                ast["blocks"].append({
                    "type": "if",
                    "condition": condition,
                    "true": true_part,
                    "false": false_part
                })
            except:
                pass

            i += 1
            continue

        # ---------------- PRINT ----------------
        if lower.startswith("print"):
            ast["blocks"].append({
                "type": "print",
                "value": line.replace("PRINT", "").strip()
            })
            i += 1
            continue

        # ---------------- DEFAULT ----------------
        ast["blocks"].append({
            "type": "expr",
            "value": line
        })

        i += 1

    return ast