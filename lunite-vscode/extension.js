const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

let terminal = null;
let hasWarnedLinter = false;

function activate(context) {
    vscode.languages.registerDocumentFormattingEditProvider('lunite', {
        provideDocumentFormattingEdits(document, options, token) {
            const edits = [];
            let indentLevel = 0;
            
            const tabSize = options.tabSize;
            const insertSpaces = options.insertSpaces;
            const indentChar = insertSpaces ? ' '.repeat(tabSize) : '\t';

            for (let i = 0; i < document.lineCount; i++) {
                const line = document.lineAt(i);
                const text = line.text.trim();

                if (!text) continue; 

                const cleanLine = stripStringsAndComments(line.text);
                
                const openCount = (cleanLine.match(/[\{\[\(]/g) || []).length;
                const closeCount = (cleanLine.match(/[\}\]\)]/g) || []).length;
                const netChange = openCount - closeCount;

                let lineIndentLevel = indentLevel;

                if (text.match(/^[\]\}\)]/)) {
                    lineIndentLevel = Math.max(0, indentLevel - 1);
                } else if (text.startsWith("else") || text.startsWith("rescue") || text.startsWith("other") || text.startsWith("finally")) {
                    lineIndentLevel = Math.max(0, indentLevel - 1);
                }

                const newText = indentChar.repeat(lineIndentLevel) + text;

                if (line.text !== newText) {
                    edits.push(vscode.TextEdit.replace(line.range, newText));
                }

                indentLevel += netChange;
                if (indentLevel < 0) indentLevel = 0;
            }
            return edits;
        }
    });

    vscode.languages.registerHoverProvider('lunite', {
        provideHover(document, position, token) {
            const range = document.getWordRangeAtPosition(position);
            if (!range) return;
            const word = document.getText(range);

            // to be updated later
            const docs = {
                "out": "Prints a value to the standard output.\n\n```lunite\nout(\"Hello, World!\")\n```",
                "in": "Reads a line of input from the user.\n\n```lunite\nlet name = in(\"What is your name? \", \"str\")\n```",
                "len": "Returns the length of a string, list, dictionary, etc.",
                "type": "Returns the type name of a value as a string.",
                "range": "Creates a list of integers from `a` to `b` (inclusive).\n\n```lunite\nfor i in range(1, 10) { out(i) }\n```",
                "list": "Creates an initialized list of `n` size with a default type hint.\n\n```lunite\nlet arr = list(5, \"int\")\n```",
                "Math": "Static library for mathematical operations.\n\nIncludes `sin`, `cos`, `tan`, `sqrt`, `pow`, `pi`, `e`, `min`, `max`, `clamp`, etc.",
                "File": "Static library for file I/O operations.\n\nIncludes `read`, `write`, `append`, `exists`, `cwd`, etc.",
                "Net": "Static library for network operations.\n\nIncludes `get`, `post`, `download`.",
                "Json": "Static library for JSON manipulation.\n\nIncludes `encode`, `decode`.",
                "Time": "Static library for time operations.\n\nIncludes `now`, `sleep`, `format`, `struct`.",
                "String": "Static library for string manipulation.\n\nIncludes `upper`, `lower`, `split`, `replace`, `includes`, etc.",
                "List": "Static library for list manipulation.\n\nIncludes `push`, `pop`, `sort`, `contains`, `index`, etc.",
                "Dict": "Static library for dictionary manipulation.\n\nIncludes `keys`, `values`, `items`, `merge`, `has`, `remove`.",
                "Sys": "Static library for system and environment tasks.\n\nIncludes `cmd`, `os`, `args`, `env`, `exit`.",
                "Random": "Static library for PRNG generation.\n\nIncludes `randint`, `choice`, `shuffle`, `random`.",
                "Console": "Static library for terminal manipulation.\n\nIncludes `clear`, `size`, `title`, `read_pass`."
            };

            if (docs[word]) {
                return new vscode.Hover(new vscode.MarkdownString(docs[word]));
            }
        }
    });

    const diagnosticCollection = vscode.languages.createDiagnosticCollection('lunite');
    context.subscriptions.push(diagnosticCollection);

    if (vscode.window.activeTextEditor) {
        lintDocument(vscode.window.activeTextEditor.document, diagnosticCollection);
    }

    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(doc => lintDocument(doc, diagnosticCollection)),
        vscode.workspace.onDidOpenTextDocument(doc => lintDocument(doc, diagnosticCollection)),
        vscode.workspace.onDidCloseTextDocument(doc => diagnosticCollection.delete(doc.uri))
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('lunite.run', (uri) => executeCommand('run', uri)),
        vscode.commands.registerCommand('lunite.compile', (uri) => executeCommand('compile', uri))
    );
}

function getTerminal() {
    if (!terminal || terminal.exitStatus !== undefined) {
        terminal = vscode.window.createTerminal("Lunite");
    }
    return terminal;
}

function executeCommand(action, uri) {
    let filePath = uri ? uri.fsPath : vscode.window.activeTextEditor?.document.fileName;
    if (!filePath) return;
    
    const config = vscode.workspace.getConfiguration('lunite');
    const pythonPath = config.get('pythonPath') || 'python';
    let lunitePath = config.get('executablePath') || 'lunite.py';

    if (!path.isAbsolute(lunitePath) && vscode.workspace.workspaceFolders) {
        lunitePath = path.join(vscode.workspace.workspaceFolders[0].uri.fsPath, lunitePath);
    }

    const term = getTerminal();
    term.show();
    term.sendText(`${pythonPath} "${lunitePath}" ${action} "${filePath}"`);
}

function stripAnsi(text) {
    return text.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '');
}

function lintDocument(document, diagnosticCollection) {
    if (document.languageId !== 'lunite') return;

    const config = vscode.workspace.getConfiguration('lunite');
    const pythonPath = config.get('pythonPath') || 'python';
    let lunitePath = config.get('executablePath') || 'lunite.py';

    if (!path.isAbsolute(lunitePath) && vscode.workspace.workspaceFolders) {
        const absolutePath = path.join(vscode.workspace.workspaceFolders[0].uri.fsPath, lunitePath);
        if (fs.existsSync(absolutePath)) {
            lunitePath = absolutePath;
        }
    }

    const tempFile = path.join(os.tmpdir(), `lunite_lint_${Date.now()}.luna`);
    const tempCompiled = tempFile.replace('.luna', '.lunac');
    
    fs.writeFileSync(tempFile, document.getText());

    cp.exec(`"${pythonPath}" "${lunitePath}" compile "${tempFile}"`, (err, stdout, stderr) => {
        try {
            if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
            if (fs.existsSync(tempCompiled)) fs.unlinkSync(tempCompiled);
        } catch (e) { }

        const output = stripAnsi(stdout + '\n' + stderr);

        if (err && output.includes("can't open file") && !hasWarnedLinter) {
            vscode.window.showWarningMessage(`Lunite Linter: Cannot find ${lunitePath}. Please ensure the Lunite interpreter is available or set 'lunite.executablePath' in VS Code settings.`);
            hasWarnedLinter = true;
            return;
        }

        const diagnostics = [];
        const errorRegex = /(.*?Error):\s*(.*?)\r?\n\s*File:\s*(.*?):(\d+):(\d+)/g;
        let match;
        
        while ((match = errorRegex.exec(output)) !== null) {
            const errType = match[1].trim();
            const errMsg = match[2].trim();
            const line = Math.max(0, parseInt(match[4], 10) - 1);
            const col = Math.max(0, parseInt(match[5], 10) - 1);

            let endCol = col + 1;
            if (line < document.lineCount) {
                const lineText = document.lineAt(line).text;
                const wordMatch = lineText.substring(col).match(/^\w+/);
                if (wordMatch) {
                    endCol = col + wordMatch[0].length;
                }
            }

            const range = new vscode.Range(line, col, line, endCol);
            const diagnostic = new vscode.Diagnostic(
                range,
                `${errType}: ${errMsg}`,
                vscode.DiagnosticSeverity.Error
            );
            
            diagnostics.push(diagnostic);
        }

        diagnosticCollection.set(document.uri, diagnostics);
    });
}

function stripStringsAndComments(text) {
    let out = "";
    let i = 0;
    const len = text.length;
    let inString = false;
    let quoteChar = '';
    
    while (i < len) {
        const char = text[i];
        
        if (!inString && char === '~' && text[i+1] === '*') {
            i += 2;
            while (i < len - 1 && !(text[i] === '*' && text[i+1] === '~')) i++;
            i += 2;
            continue;
        }
        
        if (!inString && char === '~' && text[i+1] === '~') break;

        if (!inString && (char === '"' || char === "'")) {
            inString = true;
            quoteChar = char;
            i++;
            continue;
        }
        
        if (inString && char === quoteChar) {
            if (i > 0 && text[i-1] !== '\\') inString = false;
            i++;
            continue;
        }

        if (!inString) out += char;
        i++;
    }
    return out;
}

exports.activate = activate;
