# The Lunite Programming Language

This extension provides syntax highlighting, code formatting, linting, and integrated tools for **Lunite**, a programming language by ANW.

## ✨ New in Version 1.4.0
*   **Live Linting & Diagnostics:** Catch syntax and structural errors instantly on save. Errors are highlighted with red squiggly lines directly in your code!
*   **Hover Documentation:** Hover your mouse over standard library components (like `Math`, `File`, `Random`, `out`, etc.) to see markdown documentation and code examples. Please note that this feature is incomplete.
*   **Editor Action Buttons:** Run or compile your Lunite code instantly using the new Play (`▶`-like play button) and Compile (binary file-like button) buttons located in the top-right corner of the editor.
*   **Bytecode Support:** Official file recognition and custom icons for compiled `.lunac` files.

## Features

### 🎨 Syntax Highlighting
Full colorization for Lunite's unique syntax, including:
*   **Keywords:** `func`, `class`, `let`, `const`, `attempt`, `rescue`, `leap`, `advance`, `enum`, `match`, `other`, `macro`, `async`, `await`, etc.
*   **Comments:** Support for single-line `~~` and multi-line `*~ ... ~*` comments.
*   **Literals:** Strings, f-strings, integers, floats, booleans, and null.

### 🧱 Bracket Matching & Formatting
*   Automatic matching and closing for `{ }` (Blocks), `( )` (Expressions/Arguments), and `[ ]` (Lists).
*   Automatic smart-indentation and document formatting.

## Configuration

To use the **Linting**, **Run**, and **Compile** features, the extension must know how to execute the Lunite interpreter. Open your VS Code Settings and configure the following if they differ from the defaults:
*   `lunite.pythonPath`: The path to your Python 3 interpreter (e.g., `python`, `python3`, or an absolute path to a virtual environment). Defaults to `python`.
*   `lunite.executablePath`: The path to the `lunite.py` engine file. If it is in your workspace root, you can leave it as `lunite.py`.

## Example Code

Enjoy beautiful highlighting for your Lunite code:

```lunite
~~ Lunite v1.9.9 Example
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

To run the code, you must have **Lunite** or the `lunite.py` script available on your system.

1.  Install Python 3.x.
2.  Download the `lunite.py` source code (and core modules) from the repository.
3.  Install all optionally required Python modules.
4.  Run directly via the Editor buttons or manually via CLI: `python lunite.py run source.luna`

Make sure to check the repository!  

---

**Copyright ANW, 2025-2026**
*Lunite is a project by ANW.*
*This extension is provided to you by (ing) Studios.*
