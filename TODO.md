# Lunite TODO:

- Change `import_py`'s syntax from only `import_py "<module_name>"` to both `import_py "<module_name>"` and `import_py "<module_name_or_member_or_method>" from "<package_name>"`, e.g., `import_py "load_dotenv" from "dotenv"`
- Make sure `import_py` works for `.py` files in a directory too, like: `import_py "app"` for app.py or `import_py "./pylib/csv"` for `./pylib/csv.py`
- Make a separate README for the VS Code extention, if possible
- Try to add multithreaded interpretation to make Lunite faster, with a command like `python lunite.py run <file.luna> <num_threads if specified else synchronous>`
- Add native `async` and threading to the language
- Add escape characters: `\b` for backspace, `\h` for horizontal tab, `\u0000` to `\uFFFF` or `\uffff` for a hexadecimal Unicode character, `\0` for the null character (`\u0000`)
- Make sure strings have both ASCII and Unicode support