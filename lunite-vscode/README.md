# The Lunite Programming Language

This extension by (ing) Studios provides syntax highlighting and code formatting for **Lunite**, a programming language by ANW.

## Features

### 🎨 Syntax Highlighting
Full colorization for Lunite's unique syntax, including:
*   **Keywords:** `func`, `class`, `let`, `const`, `attempt`, `rescue`, `leap`, `advance`, `enum`, `match`, `other`, etc.
*   **Comments:** Support for single-line `~~` and multi-line `*~ ... ~*` comments.
*   **Literals:** Strings, f-strings, integers, floats, booleans, and null.

### 🧱 Bracket Matching
Automatic matching and closing for:
*   `{ }` (Blocks)
*   `( )` (Expressions/Arguments)
*   `[ ]` (Lists)

## Example Code

Enjoy beautiful highlighting for your Lunite code:

```lunite
~~ Lunite v1.8.5 Example
import "utils"
import_py sqrt from math

class Calculator {
    func add(a, b) {
        return a + b
    }
}

func main() {
    let calc = new Calculator()
    let result = calc.add(10, 5)
    
    out(f"Result: {result}")

    attempt {
        let x = 10 / 0
    } rescue (err) {
        out(f"Caught error: {err}")
    }
}

main()
```

## Requirements

To run the code, you must have **Lunite** or `lunite.py` script available on your system.

1.  Install Python 3.x.
2.  Download `lunite.py` source code from the repository from the commits, finding the version you want.
3.  Install all required Python modules.

---

**Copyright ANW, 2025-2026**
*Lunite is a project by ANW.*
*This extension is provided to you by (ing) Studios.*