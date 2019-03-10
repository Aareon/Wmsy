"""Wmsy
A small, shitty Xlib window manager written in Python
"""

import logging
import subprocess
from Xlib import X, XK
from Xlib.display import Display
from time import perf_counter_ns

logging.basicConfig(
    filename="wmsy.log",
    level=logging.DEBUG,
    format="[%(asctime)-15s][%(levelname)s]: %(message)s",
)

TERM = "urxvt"
timeout = 200  # milliseconds


def string_to_keycode(display: Display, key_string: str):
    """Convert a string identifier to usable keycode"""
    keysym = XK.string_to_keysym(key_string)
    return display.keysym_to_keycode(keysym)


def grab_key(screen, keycode, mod):
    screen.grab_key(keycode, mod, 1, X.GrabModeAsync, X.GrabModeAsync)


def grab_mouse_button(screen, button, mod):
    screen.grab_button(
        button,
        mod,
        1,
        X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
        X.GrabModeAsync,
        X.GrabModeAsync,
        X.NONE,
        X.NONE,
    )


def main():
    display = Display()
    root_screen = display.screen().root

    mod = X.Mod4Mask  # set the modifier to the Windows key

    key_F1 = string_to_keycode(display, "F1")
    key_Enter = string_to_keycode(display, "Return")

    grab_key(root_screen, key_F1, mod)  # stack above hotkey
    grab_key(root_screen, key_Enter, mod)  # hotkey for opening the terminal
    grab_mouse_button(root_screen, 1, mod)  # hotkey for moving windows
    grab_mouse_button(root_screen, 3, mod)  # hotkey for resizing windows

    start_event = None
    time_delta = perf_counter_ns()
    while True:
        event = display.next_event()

        # capture key press events
        if event.type == X.KeyPress:
            # Mod4 + F1
            if event.detail == 67 and event.child != X.NONE:
                event.child.configure(stack_mode=X.Above)
                logging.info("Focused window moved to top of stack")
            # Mod4 + Return
            elif event.detail == 36:
                err = subprocess.Popen(
                    TERM, start_new_session=True, stderr=subprocess.PIPE
                )
                logging.debug(err.stdout or err.stderr)

        # capture mouse button press events
        elif event.type == X.ButtonPress and event.child is not X.NONE:
            attr = event.child.get_geometry()
            start_event = event

        # handle moving/resizing windows
        elif event.type == X.MotionNotify and start_event is not None:
            x_diff = event.root_x - start_event.root_x
            y_diff = event.root_y - start_event.root_y
            time = perf_counter_ns()

            # move window with cursor
            if event.state == 320:
                # only accept this event if its been >= 200 ms
                if (time - time_delta) >= 200:
                    start_event.child.configure(
                        x=attr.x + (x_diff if start_event.detail == 1 else 0),
                        y=attr.y + (y_diff if start_event.detail == 1 else 0),
                    )
            # resize window with cursor
            elif event.state == 1088:
                # only accept this event if its been >= 200 ms
                if (time - time_delta) / 1000000 >= 200:
                    start_event.child.configure(
                        width=max(
                            1, attr.width + (x_diff if start_event.detail == 3 else 0)
                        ),
                        height=max(
                            1, attr.height + (y_diff if start_event.detail == 3 else 0)
                        ),
                    )

        # reset after mouse button press
        elif event.type == X.ButtonRelease:
            start_event = None


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(str(e))
