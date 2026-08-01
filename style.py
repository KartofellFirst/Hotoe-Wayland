import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

def load_css():
    provider = Gtk.CssProvider()

    # In the future, swap this to load_from_path('style.css')
    css = b"""
    window, webview {
        background: transparent;
        margin-top: 0px;
        margin-right: 0px;
    }
    revealer {
        background: transparent;
    }
    #overlay {
        background-color: transparent;
        border-radius: 20px;
        color: white;
        padding: 3px 5px;
        transition: all 0.2s ease-in-out;
    }
    .overlay {
        background-color: transparent;
        border-radius: 20px;
        color: white;
        padding: 3px 5px;
        transition: all 0.2s ease-in-out;
    }
    """
    provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

