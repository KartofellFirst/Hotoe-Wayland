import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio

class HotkeyBindNotification:
    CSS = b"""
    .hk-toast {
        background-color: alpha(#1e1e1e, 0.94);
        border-radius: 10px;
        padding: 12px 14px;
        color: #eee;
    }
    .hk-toast .title {
        font-weight: 600;
        font-size: 0.95em;
    }
    .hk-toast .subtitle {
        font-size: 0.85em;
        color: alpha(#eee, 0.75);
    }
    .hk-toast .command {
        font-family: monospace;
        background-color: alpha(#000, 0.35);
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 0.9em;
    }
    .hk-toast button {
        min-height: 0;
        padding: 4px 10px;
        font-size: 0.85em;
    }
    .hk-toast .help-link {
        font-size: 0.75em;
        color: alpha(#eee, 0.55);
        
    }
    .flat {
        color: #fff;
    }
    .flat:hover { 
        background: none;
    }
    """

    def __init__(self, window, overlay):
        self.window = window
        self.overlay = overlay
        self._ensure_css_loaded()

    def _ensure_css_loaded(self):
        if getattr(HotkeyBindNotification, "_css_loaded", False):
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(self.CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        HotkeyBindNotification._css_loaded = True

    def show(self, command, help_url, on_copied=None, on_denied=None):
        revealer = Gtk.Revealer(
            transition_type=Gtk.RevealerTransitionType.SLIDE_LEFT,
            transition_duration=220,
            halign=Gtk.Align.END,
            valign=Gtk.Align.START,
            margin_top=16,
            margin_end=16,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("hk-toast")
        box.set_size_request(280, -1)

        box.append(Gtk.Label(label="This application added a hotkey listener",
                              xalign=0, css_classes=["title"], wrap=True))
        box.append(Gtk.Label(label="Please bind this to your compositor config\nif you havent done this already:",
                              xalign=0, css_classes=["subtitle"], wrap=True))

        cmd_label = Gtk.Label(label=command, xalign=0, selectable=True)
        cmd_label.add_css_class("command")
        box.append(cmd_label)

        btn_row = Gtk.Box(spacing=6, halign=Gtk.Align.START)
        copy_btn = Gtk.Button(label="Copy")
        deny_btn = Gtk.Button(label="Deny")
        deny_btn.add_css_class("flat")
        btn_row.append(copy_btn)
        btn_row.append(deny_btn)
        box.append(btn_row)

        help_label = Gtk.Label(xalign=0)
        help_label.set_halign(Gtk.Align.END)
        help_label.add_css_class("help-link")
        help_label.set_markup(f'<a href="{help_url}">How do I bind this?</a>')
        help_label.connect("activate-link", self._on_help_link)
        box.append(help_label)

        revealer.set_child(box)

        def close():
            revealer.set_reveal_child(False)
            GLib.timeout_add(revealer.get_transition_duration(),
                              lambda: (revealer.unparent(), False)[1])

        def _copy(_btn):
            self.window.get_display().get_clipboard().set(command)
            if on_copied:
                on_copied()
            close()

        def _deny(_btn):
            if on_denied:
                on_denied()
            close()

        copy_btn.connect("clicked", _copy)
        deny_btn.connect("clicked", _deny)

        self.overlay.add_overlay(revealer)
        revealer.set_reveal_child(True)
        return revealer

    def _on_help_link(self, label, uri):
        Gio.AppInfo.launch_default_for_uri(uri, None)
        return True  # stop default handling
