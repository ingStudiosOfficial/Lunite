# Lunite Changelog

This changelog is from version 1.8.0 onwards. v1.0.0 to v1.8.0 were during the local development phase only.  

*   **1.8.0** - First version of the source code on GitHub
*   **1.8.1** - Added `else if` logic and fixed copyright message
*   **1.8.2** - Modulo operator `%` and modulo equals to compound operator `%=`
*   **1.8.3** - Use `colorama` for coloured output, track column numbers and current open file
*   **1.8.4** - Much better error reporting
*   **1.8.5** - Better imports
*   **1.8.6** - More escape characters and bug fixes
*   **1.8.7** - Major `import` and `import_py` bug fixing and other fixes
*   **1.8.8** - Python venv detection for building Lunite programs
*   **1.8.9** - Added `finally` block to attempt-rescue, fixes fstrings and error handling
*   **1.9.0** - Added less than or equal to operator `<=`, greater than or equal to operator `>=` and major bug fixes
*   **1.9.1** - Bug fixing, `range(1, n)` now returns a list upto `n` rather than `n - 1`. Semicolons. Re-wrote STD LIB. New docs page.
*   **1.9.2** - Fixed TypeCheck operator code, fixed 4 edge cases, added func call stack tracing, added `list(num, "typehint")`, fixed `visit_FunctionDef()` to prevent making functions with datatype constructor names, refactored `lunite_error()` calls
*   **1.9.3** - Small speed optimizations for Lunite, a `speedtest.py` helper script and a `demos/stresstest.luna` script (used by speedtest.py)