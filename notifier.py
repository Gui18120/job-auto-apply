"""
Notificações no Windows quando uma candidatura é enviada.
"""
import os

try:
    from win10toast import ToastNotifier
    _toaster = ToastNotifier()
    _available = True
except ImportError:
    _available = False


def notify(title: str, message: str):
    print(f"[Notificacao] {title}: {message}")
    if _available:
        try:
            _toaster.show_toast(title, message, duration=5, threaded=True)
        except Exception:
            pass
