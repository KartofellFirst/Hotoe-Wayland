
# Hotoe-Wayland 

> *「ホ ト エ」.*  
> &nbsp; Built with GTk4 powered by GTK4_layer_Shell protocol  
> &nbsp; [Main repo](https://github.com/KartofellFirst/Hotoe)

**How it works**
---

Engine does not work with user files directly. They are getting soft or hard-parsed to provide expected file structure and behavior.  
Parser auto-injects JS methods from _fxAPI.js_. _fxAPI.js_ will not be shipped as an engine dependency.

The file structure it works with:
```rust
dir/
- manifest.json
- execute/hotoe-execute.html
- execute/<application assets>
- <your engine files and dependencies>
```

where  
`hotoe-execute.html`  
-> main file for the UI

`manifest.json`  
-> contains

```json
{
    "id": "com.application.my",
    "debug": true,
    "other_useless_values": "yeah, we're right here"
}
```

step-by-step engine logic:
1. Run full monitor sized webview with transparent background<br>
1.1. Forbid this webview to open external links. Only hotoe-execute.html can be displayed<br><br>
2. Load hotoe-execute.html into this webview<br>
2.1 If `debug: false` is in manifest.json -> restrict access to webview devtools<br><br>
3. Setup local IPC at `ipc://hotoe-bus.ipc`. Register yourself as a subscriber and publisher: <br>
3.1. Forward any IPC message to JS through <br>`evaluate_javascript("window.dispatchEvent(new CustomEvent('busMessage', data)")))`<br>
3.2. Forward any JS message to IPC if it's not "fxAPICall" marked<br><br>
4. Setup fxAPICalls handler in messages listener from JS. Handle them. <br>Some API calls wait for Promise –– some don't. <br>

(References of the correct API handling are in Wayland repo under "# ===== fx API =====" line)<br>
(You will have to rewrite _fxAPI.js_ for your engine specifically, but it mostly just changing webview method names)<br>
(On release you put _fxAPI.js_ and _EngineFiles.zip_ or _EngineExecutableStandalone_ separately)

## Wayland special
`hhotkeys` is a CLI integrated inside of Hotoe-Wayland engine. 

You can use it in your non-hotoe app:  
Setup a global IPC at <br>
`ipc:///run/user/<your_identifier>/hotoe-hotkeys.ipc`

Once user calls `hhotkey <combo>` from terminal or bind <br>hhotkeys registers as a publisher in your IPC and sends the combo. <br>

e.g. `SUPER+SHIFT+W`

## Learn more about EWAs and the Hotoe-Engine
- [Hotoe-MacOS](https://github.com/KartofellFirst/Hotoe-MacOS) 
- [Hotoe-Windows](https://github.com/FaultedSapiens/Hotoe-Windows) 
- [Main repo](https://github.com/KartofellFirst/Hotoe)

---

$${\color{gray}\sim\ With\ love\ from\ Hotoe\ Team\ \sim}$$
