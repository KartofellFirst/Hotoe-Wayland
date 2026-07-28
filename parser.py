shortcuts = { # for key()
    "push": "fx.pushString",
    "SIRs": "fx.recalculateInputRegions",
    "CLOSE": "fx.closeApplication",
    "write": "fx.writeFile",
    "remove": "fx.removeFile",
    "scan": "fx.scanDirectory",
    "read": "fx.requestFileContent",
    "openExternal": "fx.openExternal",
    "exec": "fx.execute",
    "hotkey": "fx.registerHotkey"
}

listeners = { # for key{}
    "receive": "window.addEventListener('busMessage', function(event) { const message = event.detail;",
    "focus": "window.addEventListener('focusEvent', function(event) { const focus = event.detail;"
}


import re
import os
input_file = 'index.html'
content = ""
fxAPI = ""
try:
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    with open("fxAPI.js", 'r', encoding='utf-8') as fx:
        fxAPI = fx.read()
except FileNotFoundError:
    content = ""
    
from random import randint
APP_ID = ""
for _ in range(10):
    APP_ID += str(randint(0, 99))
BUS_ADDR = f"ipc://hotoe-bus.ipc"
APP_NAME = "com.application" + APP_ID

def parse_app():
    inline_external_assets() # must first collect all the files
    global content
    
    if not "<script>" in content:
        content = content.replace("</body>", "<script></script></body>")
    
    content = content.replace("<script>", f"\n<script>\n{fxAPI}\n</script>\n<script>")
    
    content = content.replace("{% LOCAL_BUS_ADDRESS %}", BUS_ADDR)
    
    # IRR -> input region regulator. SIR -> set input region
    # looking for SIRs
    content = re.sub(rf"<\s*(\w+)([^>]*?)\s+{re.escape('SIR')}([^>]*)>", r'<\1\2 class="hotoe-input-region-regulator-box"\3>', content)
    
    for key, val in shortcuts.items():
        smart_method_replace(key, val)
    
    for key, val in listeners.items():
        smart_listener_replace(key, val)
    
    with open("hotoe-execute.html", 'w', encoding='utf-8') as f:
        f.write(content)
        
        
def smart_method_replace(replace, replaced):
    global content
    pattern = rf"(?<!\.)\b{re.escape(replace)}\s*\("
    content = re.sub(pattern, f"{replaced}(", content)


def smart_listener_replace(key, js_prefix):
    global content
    pattern = re.compile(rf"(?<![:\w])\b{re.escape(key)}\s*\{{")
    result = []
    pos = 0

    while True:
        m = pattern.search(content, pos)
        if not m:
            result.append(content[pos:])
            break
        result.append(content[pos:m.start()])

        # find matching closing brace, skipping braces inside strings/comments
        depth = 1
        i = m.end()
        state = None  # None | 'sq' | 'dq' | 'tpl' | 'line_comment' | 'block_comment'
        tpl_depth = 0  # tracks nested ${ ... } inside template literals

        while i < len(content) and depth > 0:
            c = content[i]
            nxt = content[i + 1] if i + 1 < len(content) else ''

            if state == 'line_comment':
                if c == '\n':
                    state = None
            elif state == 'block_comment':
                if c == '*' and nxt == '/':
                    state = None
                    i += 1
            elif state == 'sq':
                if c == '\\':
                    i += 1
                elif c == "'":
                    state = None
            elif state == 'dq':
                if c == '\\':
                    i += 1
                elif c == '"':
                    state = None
            elif state == 'tpl':
                if c == '\\':
                    i += 1
                elif c == '`':
                    state = None
                elif c == '$' and nxt == '{':
                    # entering an interpolation — braces here DO count
                    state = None
                    tpl_depth += 1
                    depth += 1
                    i += 1
            else:
                if c == '/' and nxt == '/':
                    state = 'line_comment'
                    i += 1
                elif c == '/' and nxt == '*':
                    state = 'block_comment'
                    i += 1
                elif c == "'":
                    state = 'sq'
                elif c == '"':
                    state = 'dq'
                elif c == '`':
                    state = 'tpl'
                elif c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if tpl_depth > 0 and depth >= 1:
                        # closed a ${...} interpolation, back into template text
                        tpl_depth -= 1
                        state = 'tpl'
            i += 1

        body = content[m.end():i - 1]
        result.append(f"{js_prefix}\n{body}\n}});")
        pos = i

    content = "".join(result)

def inline_external_assets():
    global content

    # <script src="..."></script>  →  <script>...</script>
    def inline_script(match):
        src = match.group(1)
        path = os.path.join(os.path.dirname(os.path.abspath(input_file)), src)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                js = f.read()
        except FileNotFoundError:
            print(f"Script not found: {path}")
            return match.group(0)  # leave untouched
        return f"<script>\n{js}\n</script>"

    content = re.sub(
        r'<script\s+src=["\']([^"\']+)["\']\s*(?:type=["\']text/javascript["\'])?\s*></script>',
        inline_script,
        content
    )

    # <link rel="stylesheet" href="...">  →  <style>...</style>
    def inline_style(match):
        href = match.group(1)
        path = os.path.join(os.path.dirname(os.path.abspath(input_file)), href)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                css = f.read()
        except FileNotFoundError:
            print(f"Stylesheet not found: {path}")
            return match.group(0)
        return f"<style>\n{css}\n</style>"

    content = re.sub(
        r'<link\s+rel=["\']stylesheet["\']\s+href=["\']([^"\']+)["\']\s*/?>',
        inline_style,
        content
    )


if __name__ == '__main__':
    parse_app()

