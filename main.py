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
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gio, Gdk, Gtk4LayerShell, WebKit, GLib

from style import load_css
from parser import parse_app, BUS_ADDR, APP_ID, APP_NAME


class HotoeEngine(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_NAME,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.input_regions = [[0, 0, 0, 0]]
        self.running = True
        
        # Setup ZeroMQ message bus
        self.setup_message_bus()

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


    def do_startup(self):
        Gtk.Application.do_startup(self)
        load_css()
        
    def EnhansedWebview(self):
        w = WebKit.WebView()
        w.set_background_color(Gdk.RGBA(0.0, 0.0, 0.0, 0.01))
        w.connect("load-changed", self.webview_page_status)
        w.load_uri(f"file://{os.path.abspath("hotoe-execute.html")}")
        
        
        # 2 lines to setup devtools
        settings = w.get_settings()
        settings.set_enable_developer_extras(True)
        
        content_manager = w.get_user_content_manager()
        content_manager.register_script_message_handler("busMessage")
        content_manager.connect("script-message-received::busMessage", self.on_webview_message)
        
        return w

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

        self.window.set_child(self.main)

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
        self.ewa_main.set_size_request(self.monitor_w, self.monitor_h)

        self.window.present()
        self.window.connect("map", self.on_window_mapped)
        
        self.ewa_main.grab_focus()
        
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
            
        if not self.input_regions:
            surface.set_input_region(cairo.Region())
            return
        
        first = self.input_regions[0]
        combined = cairo.Region(cairo.RectangleInt(first[0], first[1], first[2], first[3]))
        
        for region in self.input_regions[1:]:
            rect = cairo.RectangleInt(region[0], region[1], region[2], region[3])
            rect_region = cairo.Region(rect)
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
                # For saving images or binary data sent from JS
                binary_data = base64.b64decode(content)
                with open(file_path, "wb") as f:
                    f.write(binary_data)
            else:
                # For plain text files
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
                        "isFile": entry.is_file(),
                        "size": entry.stat().st_size if entry.is_file() else 0
                    })

            self.resolve_js_promise(call_id, result={"directory": dir_path, "items": items})
        except Exception as e:
            self.resolve_js_promise(call_id, error=str(e))
            
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

        # standard tilde (~) user paths
        return os.path.abspath(os.path.expanduser(path_str))

       
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
            print(f"❌ JSON decode error: {e}")
            print(f"   Raw message: {message_str if 'message_str' in locals() else 'N/A'}")
        except Exception as e:
            print(f"❌ Webview message error: {e}")
    
    def API_handler(self, data):
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
                
            
    #> ENGINE to JS <#
    def call_event_js(self, event_name, detail):
        js = f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {json.dumps(detail)} }}));"
        self.ewa_main.evaluate_javascript(js, -1, None, None, None, None, None)
        
    def update_regions_using_html(self):
        """if you dont wrap js code into single-time-use function, you'll get conflicts while creating const data = [///]"""
        js = """(function() { 
            const data = {fxAPICall: {SIRs: []}};
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
 


if __name__ == '__main__':
    parse_app()
    app = HotoeEngine()
    sys.exit(app.run(sys.argv))

