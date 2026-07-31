from ctypes import CDLL
try:
    CDLL('libgtk4-layer-shell.so')
except:
    print("WTF?")

import gi
import sys
import os
import cairo
import zmq
import json
import threading
import time
import base64
import mimetypes
import subprocess
import uuid
import signal
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gio, Gdk, Gtk4LayerShell, WebKit, GLib

from style import load_css
from parser import parse_app, BUS_ADDR, APP_ID, APP_NAME
from hotkeysWaylandFix import HotkeyBindNotification


class HotoeEngine(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_NAME,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.input_regions = [[0, 0, 0, 0]]
        self.system_input_regions = [[0, 0, 0, 0]] # Wayland thing only
        self.system_popup = False # Wayland thing only
        self.hotkey_events = {}
        self.running = True
        self.setup_message_bus()
        self.setup_hotkey_bus()

    def setup_message_bus(self):
        """Setup ZeroMQ pub/sub message bus"""
        context = zmq.Context()
        
        self.pub_socket = context.socket(zmq.PUB)
        self.pub_socket.bind(BUS_ADDR)
        
        self.sub_socket = context.socket(zmq.SUB)
        self.sub_socket.connect(BUS_ADDR)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        threading.Thread(target=self.message_listener, daemon=True).start()
        
        print("Message bus running on " + BUS_ADDR)

    def setup_hotkey_bus(self):
        context = zmq.Context.instance()
        self.hotkey_rep = context.socket(zmq.REP)
        self.hotkey_rep.bind(f"ipc:///run/user/{os.getuid()}/hotoe-hotkeys.ipc")
        threading.Thread(target=self.hotkey_listener, daemon=True).start()

    def hotkey_listener(self):
        poller = zmq.Poller()
        poller.register(self.hotkey_rep, zmq.POLLIN)
        while self.running:
            events = dict(poller.poll(timeout=200)) 
            if self.hotkey_rep in events:
                combo = self.hotkey_rep.recv_string()
                match = self.hotkey_events.get(combo)
                if match:
                    GLib.idle_add(self.call_event_js, match, {})
                    self.hotkey_rep.send_string("ok")
                else:
                    self.hotkey_rep.send_string("unregistered")
        

    def do_startup(self):
        Gtk.Application.do_startup(self)
        load_css()
        
    def EnhansedWebview(self):
        w = WebKit.WebView()
        w.set_background_color(Gdk.RGBA(0.0, 0.0, 0.0, 0.01))
        w.connect("load-changed", self.webview_page_status)
        w.connect("decide-policy", self.on_decide_policy)
        self.initial_uri = f"file://{os.path.abspath('hotoe-execute.html')}"
        w.load_uri(self.initial_uri)
        
        
        # 2 lines to setup devtools
        settings = w.get_settings()
        settings.set_enable_developer_extras(True)
        
        content_manager = w.get_user_content_manager()
        content_manager.register_script_message_handler("busMessage")
        content_manager.connect("script-message-received::busMessage", self.on_webview_message)
        
        return w
    
    def on_decide_policy(self, webview, decision, decision_type):
        """forbid the dummy developer from redirecting the user from the app to an external website"""
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False 
        uri = decision.get_navigation_action().get_request().get_uri()

        if uri == self.initial_uri:
            decision.use() 
        else:
            decision.ignore()
            print(f"[blocked navigation] {uri}. Use iframe or fx.openExternal().\nAnd read the fucking docs, who have I been writing them for? it's like 10 minutes file'")

        return True

    def do_activate(self):
        
        self.window = Gtk.Window()
        self.window.set_application(self)

        Gtk4LayerShell.init_for_window(self.window)
        Gtk4LayerShell.set_namespace(self.window, "waydland-island")
        Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self.window, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        self.ewa_main = self.EnhansedWebview()
        self.ewa_main.set_focusable(True)
        self.ewa_main.set_can_focus(True)
        
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("enter", self.on_mouse_enter)
        motion_controller.connect("leave", self.on_mouse_leave)
        motion_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.ewa_main.add_controller(motion_controller)
        
        self.main = Gtk.Box()
        self.main.set_name("main-container")
        self.ewa_main.set_halign(Gtk.Align.START)
        self.ewa_main.set_valign(Gtk.Align.START)
        self.ewa_main.set_can_focus(True)
        self.ewa_main.connect("load-changed", self.on_webview_load_changed)
        self.main.append(self.ewa_main)

        self.ewa_main.add_tick_callback(self.on_animation_frame)

        # notification_overlay is only Wayland thing for now. you dont need this in other engines ithink
        self.notification_overlay = Gtk.Overlay()
        self.notification_overlay.set_child(self.main)
        self.notification_overlay.set_css_classes(["overlay"])
        self.window.set_child(self.notification_overlay)

        display = Gdk.Display.get_default()
        monitors = display.get_monitors()

        if monitors.get_n_items() > 0:
            primary_monitor = monitors.get_item(0)
            geometry = primary_monitor.get_geometry()
            self.monitor_w = geometry.width
            self.monitor_h = geometry.height
        else:
            self.monitor_w = 1920
            self.monitor_h = 1080

        self.window.set_default_size(self.monitor_w, self.monitor_h)
        self.window.set_resizable(False)
        self.ewa_main.set_size_request(self.monitor_w/2, self.monitor_h/3)

        self.window.present()
        self.window.connect("map", self.on_window_mapped)
        
        self.ewa_main.grab_focus()
        self.system_input_regions = [[self.monitor_w-296, 0, 296, 180]] 
        
    def webview_page_status(self, webview, load_event): # STARTED -> COMMITED -> FINISHED   
        if load_event == WebKit.LoadEvent.FINISHED:
            self.update_regions_using_html()
            
    def on_webview_load_changed(self, webview, event):
        if event == WebKit.LoadEvent.FINISHED:
            GLib.idle_add(self.update_regions_using_html)
                
    def on_animation_frame(self, widget, frame_clock):
        widget.queue_draw()
        return True
    
    def on_window_mapped(self, window):
        surface = window.get_surface()
        self.ewa_main.grab_focus()
    
    def on_mouse_enter(self, controller, x, y):
        self.ewa_main.grab_focus()
        self.call_event_js("focusEvent", "true")
        
    def on_mouse_leave(self, controller):
        self.call_event_js("focusEvent", "false")

    def update_input_region(self):
        surface = self.window.get_surface()
        if not surface:
            return

        all_regions = self.input_regions + self.system_input_regions
        if not all_regions:
            surface.set_input_region(cairo.Region())
            return

        first = all_regions[0]
        combined = cairo.Region(cairo.RectangleInt(first[0], first[1], first[2], first[3]))
        for region in all_regions[1:]:
            rect_region = cairo.Region(cairo.RectangleInt(region[0], region[1], region[2], region[3]))
            combined.union(rect_region)

        surface.set_input_region(combined)
            
    def message_listener(self):
        while self.running:
            try:
                message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                data = json.loads(message)
                
                print(f"[BUS RECEIVED] {data}")
                
                self.call_event_js("busMessage", data)
                    
            except zmq.Again:
                time.sleep(0.01)
            except Exception as e:
                print(f"Message listener error: {e}")

    def publish(self, data):
        """Publish a message to the bus"""
        try:
            self.pub_socket.send_string(json.dumps(data))
        except Exception as e:
            print(f"Bus publish error: {e}")
            
    def close_application(self):
        self.running = False  
        try:
            self.pub_socket.close(0)
            self.sub_socket.close(0)
        except Exception as e:
            print(f"Socket cleanup error: {e}")
        if self.window:
            self.window.close()
        self.quit() 
        
    def _handle_read_file(self, call_id, file_path):
        if not file_path or not os.path.exists(file_path):
            self.resolve_js_promise(call_id, error=f"File not found: {file_path}")
            return

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            is_text = mime_type and (mime_type.startswith("text/") or mime_type in ["application/json", "application/javascript"])

            if is_text:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.resolve_js_promise(call_id, result={
                    "type": "text",
                    "mime": mime_type or "text/plain",
                    "content": content
                })
            else:
                # images, pdfs, audio, etc -> Base64
                with open(file_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                
                mime = mime_type or "application/octet-stream"
                # form a data URI so images can easily be rendered via <img src="...">
                data_uri = f"data:{mime};base64,{encoded}"

                self.resolve_js_promise(call_id, result={
                    "type": "binary",
                    "mime": mime,
                    "base64": encoded,
                    "dataUri": data_uri
                })

        except Exception as e:
            self.resolve_js_promise(call_id, error=str(e))
    
    def _handle_write_file(self, call_id, file_path, content, is_base64):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            if is_base64:
                # saving images or binary data sent from JS
                binary_data = base64.b64decode(content)
                with open(file_path, "wb") as f:
                    f.write(binary_data)
            else:
                # plain text files
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
            self.resolve_js_promise(call_id, result={"success": True, "path": file_path})
        except Exception as e:
            self.resolve_js_promise(call_id, error=str(e))

    def _handle_remove_file(self, call_id, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.resolve_js_promise(call_id, result={"success": True})
            else:
                self.resolve_js_promise(call_id, error="File does not exist")
        except Exception as e:
            self.resolve_js_promise(call_id, error=str(e))

    def _handle_scan_directory(self, call_id, dir_path):
        try:
            if not os.path.isdir(dir_path):
                self.resolve_js_promise(call_id, error=f"Directory not found: {dir_path}")
                return

            items = []
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "isDir": entry.is_dir(),
                        "size": entry.stat().st_size if entry.is_file() else 0
                    })

            self.resolve_js_promise(call_id, result={"directory": dir_path, "items": items})
        except Exception as e:
            self.resolve_js_promise(call_id, error=str(e))
    
    def _exec_thread(self, call_id, payload):
        cmd = payload["cmd"]
        # timeout_ms = None
        if not payload.get("daemon", False): timeout_ms = payload.get("timeout", 30000)
        try:
            if timeout_ms:
                proc = subprocess.run(
                    cmd,
                    shell=isinstance(cmd, str),
                    capture_output=True,
                    text=True,
                    timeout=timeout_ms / 1000.0,
                )
                result = {"stdout": proc.stdout, "stderr": proc.stderr, "exitCode": proc.returncode}
                GLib.idle_add(self.resolve_js_promise, call_id, None, result)
            else:
                try: 
                    proc = subprocess.Popen(
                        cmd,
                        shell=isinstance(cmd, str),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    path = self.ensure_storage_exists()
                    with open(path, 'r') as f:
                        data = json.load(f)
                    data["daemons"].append(proc.pid)
                    with open(path, 'w') as f:
                        json.dump(data, f)
                    GLib.idle_add(self.resolve_js_promise, call_id, None, {"pid": proc.pid})
                except Exception as ew: 
                    GLib.idle_add(self.resolve_js_promise, call_id, str(ew), None)
        except subprocess.TimeoutExpired as e:
            GLib.idle_add(self.resolve_js_promise, call_id, f"Execution thread has timed out after {timeout_ms}ms", None)
        except Exception as e:
            GLib.idle_add(self.resolve_js_promise, call_id, str(e), None)
           
    def ensure_storage_exists(self):
        pth = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "hotoe")
        if not os.path.exists(pth): os.makedirs(pth)
        path = os.path.join(pth, "storage.json")
        if not os.path.exists(path):     
            with open(path, 'w') as f: json.dump({"daemons":[],"cache":{}}, f)
        return path
    
    def resolve_path_shortcuts(self, path_str):
        """Expands custom $Shortcuts and ~ into absolute system paths."""
        if not path_str:
            return path_str

        shortcuts = {
            "$DOWNLOADS": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD),
            "$DOCUMENTS": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS),
            "$DESKTOP": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP),
            "$MUSIC": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC),
            "$PICTURES": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES),
            "$VIDEOS": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS),
            # XDG
            "$CONFIG": GLib.get_user_config_dir(),
            "$DATA": GLib.get_user_data_dir(),
            "$CACHE": GLib.get_user_cache_dir(),
            "$HOME": GLib.get_home_dir(),
        }

        for key, val in shortcuts.items():
            if val and (path_str.startswith(key) or path_str.lower().startswith(key.lower())):
                path_str = path_str.replace(key, val, 1)
                break

        # standard ~
        return os.path.abspath(os.path.expanduser(path_str))


    def _handle_register_hotkey(self, call_id, accelerator, event_name):
        normalized = self._normalize_combo(accelerator)
        notif = HotkeyBindNotification(self.window, self.notification_overlay)
        self.system_popup = True

        def on_copied():
            self.hotkey_events[normalized] = event_name
            self.resolve_js_promise(call_id, result={"registered": True, "method": "manually"})
            self.system_popup = False
            
        def on_denied():
            self.system_popup = False
            self.resolve_js_promise(call_id, error="user denied hotkey registration")
            
        notif.show(
            command=f"hhotkey {normalized}",
            help_url=f"https://KartofellFirst.github.io/HotoeWH?accelerator={normalized}",
            on_copied=on_copied,
            on_denied=on_denied
        )

    def _normalize_combo(self, accelerator):
        parts = [p.strip().upper() for p in accelerator.replace(" ", "").split("+")]
        return "+".join(parts)

    
    # ===== fx API =====
    
    #> JS to ENGINE <#
    def on_webview_message(self, manager, result):
        try:
            message_str = result.to_string()
            data = json.loads(message_str)
            
            if isinstance(data, dict) and "fxAPICall" in data:
                self.API_handler(data["fxAPICall"])
                return
            
            self.publish(data)
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw message: {message_str if 'message_str' in locals() else 'N/A'}")
        except Exception as e:
            print(f"webview message error: {e}")
    
    def API_handler(self, data):  # idk if Switch case exists in python, but im too lazy to even AI this
        if "SIRs" in data.keys():
            regions = []
            for l in data["SIRs"]:
                for i, el in enumerate(l):
                    l[i] = max(0, int(el))
                regions.append(l)
            self.input_regions = regions
            GLib.idle_add(self.update_input_region)
            return
        if "RIR" in data.keys():
            self.update_regions_using_html()
            return
        if "CLOSE" in data.keys():
            self.close_application()
        if "BROWSE" in data.keys():
            Gio.AppInfo.launch_default_for_uri(data["BROWSE"], None)
            return
        if "STORE" in data.keys():
            path = self.ensure_storage_exists()
            with open(path, 'r') as f: 
                cont = json.load(f)
                cont["cache"][data["STORE"]["key"]] = data["STORE"]["data"]
                with open(path, 'w') as f: json.dump(cont, f)
            return
            
        # promised fxAPI calls
        if "action" in data and "callId" in data:
            action = data["action"]
            call_id = data["callId"]
            payload = data.get("payload", {})

            if action == "readFile":
                path = self.resolve_path_shortcuts(payload.get("filePath"))
                threading.Thread(target=self._handle_read_file, args=(call_id, path), daemon=True).start()
            elif action == "writeFile":
                path = self.resolve_path_shortcuts(payload.get("filePath"))
                content = payload.get("content", "")
                is_b64 = payload.get("isBase64", False)
                threading.Thread(target=self._handle_write_file, args=(call_id, path, content, is_b64), daemon=True).start()
            elif action == "removeFile":
                path = self.resolve_path_shortcuts(payload.get("filePath"))
                threading.Thread(target=self._handle_remove_file, args=(call_id, path), daemon=True).start()
            elif action == "scanDirectory":
                path = self.resolve_path_shortcuts(payload.get("dirPath"))
                threading.Thread(target=self._handle_scan_directory, args=(call_id, path), daemon=True).start()
            elif action == "execute":
                threading.Thread(
                    target=self._exec_thread,
                    args=(call_id, payload),
                    daemon=True
                ).start()
            elif action == "killDaemon":
                try: os.kill(payload["id"], signal.SIGTERM)
                except ProcessLookupError: pass  
                # to avoid spawning zombies
                try: os.waitpid(payload["id"], 0)
                except ChildProcessError: pass
                path = self.ensure_storage_exists()
                with open(path, 'r') as f: content = json.load(f)
                if payload["id"] in content["daemons"]: content["daemons"].remove(payload["id"])
                with open(path, 'w') as f: json.dump(content, f)
                self.resolve_js_promise(call_id, None, "Job done")
            elif action == "getDaemons":
                path = self.ensure_storage_exists()
                with open(path, 'r') as f: self.resolve_js_promise(call_id, None, json.load(f)["daemons"])
            elif action == "getKeyValues":
                path = self.ensure_storage_exists()
                with open(path, 'r') as f: self.resolve_js_promise(call_id, None, list(json.load(f)["cache"].keys()))
            elif action == "getValueFromCache":
                path = self.ensure_storage_exists()
                with open(path, 'r') as f: self.resolve_js_promise(call_id, None, json.load(f)["cache"].get(payload["key"]))
            elif action == "deleteFromCache":
                path = self.ensure_storage_exists()
                with open(path, 'r') as f: data = json.load(f)
                data["cache"].pop(payload["key"], None) 
                with open(path, 'w') as f: json.dump(data, f)
                self.resolve_js_promise(call_id, None, True)
            elif action == "registerHotkey":
                self._handle_register_hotkey(call_id, payload.get("accelerator"), payload.get("eventName"))
                        
            
    #> ENGINE to JS <#
    def call_event_js(self, event_name, detail):
        js = f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {json.dumps(detail)} }}));"
        self.ewa_main.evaluate_javascript(js, -1, None, None, None, None, None)
        
    def update_regions_using_html(self):
        """if you dont wrap js code into single-time-use function, you'll get conflicts while creating const data = [///]"""
        js = """(function() { const data = {fxAPICall: {SIRs: []}};
            document.querySelectorAll('.hotoe-input-region-regulator-box').forEach((el) => { 
                const rect = el.getBoundingClientRect();
                data.fxAPICall.SIRs.push([rect.left, rect.top, rect.width, rect.height]);
            });
            window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
        })();"""
        self.ewa_main.evaluate_javascript(js, -1, None, None, None, None, None)
        
    def resolve_js_promise(self, call_id, error=None, result=None):
        err_json = json.dumps(error) if error else "null"
        res_json = json.dumps(result) if result is not None else "null"
        js = f"fx._resolvePromise({json.dumps(call_id)}, {err_json}, {res_json});"
        
        # GLib.idle_add ensures GTK UI thread safety if called from background thread
        GLib.idle_add(lambda: self.ewa_main.evaluate_javascript(js, -1, None, None, None, None, None))
 
 
# hhotkey installation insurance universal
# user must have his ~/bin directory be added to PATH
def ensure_hhotkey_installed():
    import shutil
    from pathlib import Path
    
    source_file = Path("hhotkey")
    target_dir = Path.home() / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "hhotkey"
    
    if source_file.exists():
        shutil.copy2(source_file, target_file)
        target_file.chmod(0o755)
        print(f"[hotoe] installed to {target_file}")
        return True
    return False


if __name__ == '__main__':
    parse_app()
    ensure_hhotkey_installed() # Only Wayland thing
    app = HotoeEngine()
    sys.exit(app.run(sys.argv))

