import re

class Preprocessor:
    def __init__(self):
        self.macros = {}

    def process(self, source: str) -> str:
        macro_regex = re.compile(r'macro\s+([a-zA-Z_]\w*)\s*(?:\((.*?)\))?\s*(?:\{([\s\S]*?)\}|=\s*(.*))')
        
        def make_macro(match):
            name = match.group(1)
            params = [p.strip() for p in match.group(2).split(',')] if match.group(2) else []
            body = match.group(3) if match.group(3) else match.group(4)
            self.macros[name] = (params, body.strip())
            return ""

        clean_source = macro_regex.sub(make_macro, source)

        for name in sorted(self.macros.keys(), key=len, reverse=True):
            params, body = self.macros[name]
            
            if not params:
                clean_source = re.sub(rf'\b{name}\b', body, clean_source)
            else:
                param_pattern = rf'\b{name}\s*\((.*?)\)'
                
                def replace_func_macro(m):
                    args = [a.strip() for a in m.group(1).split(',')]
                    temp_body = body
                    for i, p_name in enumerate(params):
                        if i < len(args):
                            temp_body = temp_body.replace(p_name, f"({args[i]})")
                    return temp_body

                clean_source = re.sub(param_pattern, replace_func_macro, clean_source)

        return clean_source