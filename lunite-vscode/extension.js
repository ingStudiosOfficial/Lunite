const vscode = require('vscode');

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

                if (!text) {
                    continue; 
                }

                const cleanLine = stripStringsAndComments(line.text);
                
                const openCount = (cleanLine.match(/[\{\[\(]/g) || []).length;
                const closeCount = (cleanLine.match(/[\}\]\)]/g) || []).length;
                const netChange = openCount - closeCount;

                let lineIndentLevel = indentLevel;

                // Handle outdent for lines starting with closing brackets
                if (text.match(/^[\]\}\)]/)) {
                    lineIndentLevel = Math.max(0, indentLevel - 1);
                } 
                // Handle non-indenting structural keywords
                else if (text.startsWith("else") || text.startsWith("rescue") || text.startsWith("other") || text.startsWith("finally")) {
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
}

function stripStringsAndComments(text) {
    let out = "";
    let i = 0;
    const len = text.length;
    let inString = false;
    let quoteChar = '';
    
    while (i < len) {
        const char = text[i];
        
        // Block comment removal
        if (!inString && char === '~' && text[i+1] === '*') {
            i += 2;
            while (i < len - 1 && !(text[i] === '*' && text[i+1] === '~')) {
                i++;
            }
            i += 2;
            continue;
        }
        
        // Line comment removal
        if (!inString && char === '~' && text[i+1] === '~') {
            break;
        }

        // String state management
        if (!inString && (char === '"' || char === "'")) {
            inString = true;
            quoteChar = char;
            i++;
            continue;
        }
        
        if (inString && char === quoteChar) {
            if (i > 0 && text[i-1] !== '\\') {
                inString = false;
            }
            i++;
            continue;
        }

        if (!inString) {
            out += char;
        }
        i++;
    }
    return out;
}

exports.activate = activate;