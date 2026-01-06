# Lunite TODO:

- Make a separate README for the VS Code extention, if possible
- Try to add multithreaded interpretation to make Lunite faster, with a command like `python lunite.py run <file.luna> <num_threads if specified else synchronous>`
- Add native `async` and threading to the language
- Add escape characters: `\b` for backspace, `\h` for horizontal tab, `\u0000` to `\uFFFF` or `\uffff` for a hexadecimal Unicode character, `\0` for the null character (`\u0000`)
- Make sure strings have both ASCII and Unicode support