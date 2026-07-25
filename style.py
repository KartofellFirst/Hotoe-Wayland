import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

def load_css():
    provider = Gtk.CssProvider()

    # In the future, swap this to load_from_path('style.css')
    css = b"""
    window {
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
    #arrow-left {
        border-left: 2px solid #fff;
        border-radius: 50px;
    }
    #arrow-right {
        border-right: 2px solid #fff;
        border-radius: 50px;
    }
    #pill {
        min-width: 0px;
        transition: all 250ms cubic-bezier(0.25, 1, 0.5, 1);
    }
    .mini-applet, .arrow-revealer {
        background: none;
        border-radius: 999px;
        transition: all .2s ease;
    }
    .mini-applet:hover {
        background: #222;
        transform: scale(1.1);
    }
    .arrow-revealer:hover {
        opacity: 0.3;
        transform: scale(1.5);
    }
    """
    provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

