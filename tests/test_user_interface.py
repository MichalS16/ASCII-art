"""
GUI smoke tests for user_interface.py.

These tests drive the real customtkinter widget tree (no display-less mocking of
the widgets themselves) but neutralize anything that would block or reach the
network: CTk.mainloop is a no-op, CTkInputDialog is mocked, requests calls are
mocked, and subprocess.Popen is mocked.

Nested callbacks (generate, menu, openfile, ...) are not exposed as module
attributes, so they are invoked the same way a real click would trigger them:
via the `_command` attribute customtkinter stores on each widget.
"""

import os
import re
import time
import tkinter
import unittest
from unittest.mock import patch

import customtkinter
import requests

from ascii_art import user_interface as ui
from ascii_art import ui_logic
from ascii_art.translations import ENGLISH, CZECH

from _paths import ASSETS_DIR
from _http import make_response
from _tempcwd import IsolatedTempCwdMixin

SAMPLE_IMAGE = os.path.join(ASSETS_DIR, "red-character.png")


def widgets_of_type(root, cls):
    """Recursively collect descendant widgets of `root` that are instances of `cls`."""
    found = []
    for child in root.winfo_children():
        if isinstance(child, cls):
            found.append(child)
        found.extend(widgets_of_type(child, cls))
    return found


def find_button(root, command_name):
    """Find the CTkButton whose bound callback function is named `command_name`."""
    for button in widgets_of_type(root, customtkinter.CTkButton):
        if button._command is not None and button._command.__name__ == command_name:
            return button
    raise AssertionError(f"no button found with command {command_name!r}")


def find_popup(root):
    """Find the CTkToplevel opened by show_popup_message, if any (it isn't
    nested in root's widget tree, so winfo_children() suffices)."""
    for child in root.winfo_children():
        if isinstance(child, customtkinter.CTkToplevel):
            return child
    return None


def find_selected_file_label(root):
    """Find the CTkLabel showing the currently-selected file's name: the one
    directly to the right of the 'openfile' button, in the same row of its
    parent (select_row) frame's grid (not exposed as a module attribute, so
    it's not directly importable)."""
    button_select = find_button(root, "openfile")
    for label in widgets_of_type(button_select.master, customtkinter.CTkLabel):
        if label.grid_info().get("column") == button_select.grid_info().get("column") + 1:
            return label
    raise AssertionError("no selected-file label found to the right of the openfile button")


def find_url_status_label(root):
    """Find the CTkLabel showing the live URL-check status: the one directly
    to the right of the URL entry widget, in the same row of its parent
    (url_row) frame's grid."""
    entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
    for label in widgets_of_type(entry_url.master, customtkinter.CTkLabel):
        if label.grid_info().get("column") == entry_url.grid_info().get("column") + 1:
            return label
    raise AssertionError("no URL status label found to the right of the URL entry")


def fire_key_release(entry):
    """Invoke a CTkEntry's <KeyRelease> binding directly via its registered Tcl
    command, since event_generate() isn't reliably delivered to an unmapped/
    unfocused window under this test harness's no-op mainloop."""
    bind_str = entry._entry.bind("<KeyRelease>")
    match = re.search(r"\[(\d+\w+) ([^\]]+)\]", bind_str)
    funcname, substitutions = match.group(1), match.group(2).split()
    entry._entry.tk.call(funcname, *(["0"] * len(substitutions)))


def click_new_image_when_result_window_opens(inner_self):
    """CTk.mainloop() replacement that immediately clicks "New image" on the
    result window, simulating a user closing it that way."""
    if inner_self.title() == ui.current_lang["result_title"]:
        find_button(inner_self, "newimage")._command()


class UserInterfaceTestCase(IsolatedTempCwdMixin, unittest.TestCase):
    """Base class: no-op mainloop, tracked root windows, clean module globals per test."""

    def setUp(self):
        super().setUp()
        self.created_roots = []
        original_init = customtkinter.CTk.__init__

        def tracking_init(inner_self, *args, **kwargs):
            last_error = None
            delay = 0.05
            for _attempt in range(3):
                try:
                    original_init(inner_self, *args, **kwargs)
                    last_error = None
                    break
                except tkinter.TclError as error:
                    last_error = error
                    time.sleep(delay)
                    delay *= 2
            if last_error is not None:
                raise last_error
            self.created_roots.append(inner_self)

        self._init_patcher = patch.object(customtkinter.CTk, "__init__", tracking_init)
        self._init_patcher.start()
        self.addCleanup(self._init_patcher.stop)

        self._mainloop_patcher = patch.object(customtkinter.CTk, "mainloop", lambda self: None)
        self._mainloop_patcher.start()
        self.addCleanup(self._mainloop_patcher.stop)

        self.addCleanup(self._destroy_roots)

        ui.pc_image_path = ""
        ui.theme = ""
        ui.downstate = ""
        ui.size = ""
        ui.current_lang = ENGLISH
        ui.other_lang = CZECH
        ui.window_position = ""

    def _destroy_roots(self):
        for root in self.created_roots:
            try:
                root.destroy()
            except Exception:
                pass

    def build_mainwindow(self):
        ui.mainwindow()
        return ui.ui1

    def segmented_buttons(self, root):
        return widgets_of_type(root, customtkinter.CTkSegmentedButton)


class MainWindowConstructionTests(UserInterfaceTestCase):
    def test_builds_with_dark_theme_by_default(self):
        # an unset theme defaults to building the window in dark mode
        ui.theme = ""
        root = self.build_mainwindow()
        self.assertIsNotNone(root)

    def test_builds_with_light_theme(self):
        # a "light" theme builds the window in light mode
        ui.theme = "light"
        root = self.build_mainwindow()
        self.assertIsNotNone(root)

    def test_run_delegates_to_mainwindow(self):
        # the module-level run() entry point builds the main window
        ui.run()
        self.assertIsNotNone(ui.ui1)


class DownloadStateTests(UserInterfaceTestCase):
    def test_checkbox_updates_downstate(self):
        # toggling the download checkbox updates the module-level downstate flag
        root = self.build_mainwindow()
        checkboxes = widgets_of_type(root, customtkinter.CTkCheckBox)
        checkboxes[0]._command()
        self.assertEqual(ui.downstate, checkboxes[0].get())


class ThemeSwitchTests(UserInterfaceTestCase):
    def test_switch_to_dark(self):
        # selecting "Dark" on the segmented button switches the theme to dark
        root = self.build_mainwindow()
        segmented_theme = self.segmented_buttons(root)[0]
        segmented_theme._command(ui.DARK_LABEL)
        self.assertEqual(ui.theme, "dark")

    def test_switch_to_light(self):
        # selecting "Light" on the segmented button switches the theme to light
        root = self.build_mainwindow()
        segmented_theme = self.segmented_buttons(root)[0]
        segmented_theme._command(ui.LIGHT_LABEL)
        self.assertEqual(ui.theme, "light")


class OpenFileTests(UserInterfaceTestCase):
    def test_selecting_a_file_sets_pc_image_path(self):
        # picking a file via the dialog stores its path in pc_image_path
        root = self.build_mainwindow()
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=SAMPLE_IMAGE):
            find_button(root, "openfile")._command()
        self.assertEqual(ui.pc_image_path, SAMPLE_IMAGE)

    def test_selecting_a_file_shows_its_name(self):
        # picking a file shows its name next to the button, empty beforehand
        root = self.build_mainwindow()
        label = find_selected_file_label(root)
        self.assertEqual(label.cget("text"), "")
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=SAMPLE_IMAGE):
            find_button(root, "openfile")._command()
        self.assertEqual(label.cget("text"), os.path.basename(SAMPLE_IMAGE))

    def test_selecting_a_file_with_a_long_name_shows_a_truncated_name(self):
        # a long filename is shown truncated, not overflowing the fixed-width label
        root = self.build_mainwindow()
        label = find_selected_file_label(root)
        long_path = os.path.join(os.path.dirname(SAMPLE_IMAGE), "a-very-long-filename-that-someone-picked-for-some-reason.png")
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=long_path):
            find_button(root, "openfile")._command()
        self.assertEqual(label.cget("text"), ui.truncate_filename_for_display(os.path.basename(long_path)))
        self.assertLessEqual(len(label.cget("text")), 24)

    def test_cancelling_file_dialog_leaves_path_empty(self):
        # dismissing the file dialog without picking anything leaves pc_image_path empty
        root = self.build_mainwindow()
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=""):
            find_button(root, "openfile")._command()
        self.assertEqual(ui.pc_image_path, "")

    def test_selecting_a_file_clears_a_previously_typed_url(self):
        # picking a file clears whatever URL was previously typed, keeping the two inputs mutually exclusive
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=SAMPLE_IMAGE):
            find_button(root, "openfile")._command()
        self.assertEqual(ui.pc_image_path, SAMPLE_IMAGE)
        self.assertEqual(entry_url.get(), "")


class UrlTypedClearsSelectedFileTests(UserInterfaceTestCase):
    def test_typing_a_url_clears_a_previously_selected_file(self):
        # typing a URL clears a previously selected file, keeping the two inputs mutually exclusive
        root = self.build_mainwindow()
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=SAMPLE_IMAGE):
            find_button(root, "openfile")._command()
        self.assertEqual(ui.pc_image_path, SAMPLE_IMAGE)

        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")
        fire_key_release(entry_url)

        self.assertEqual(ui.pc_image_path, "")
        self.assertEqual(find_selected_file_label(root).cget("text"), "")

    def test_typing_with_no_file_selected_is_a_no_op(self):
        # typing a URL when no file was selected doesn't touch pc_image_path
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")
        fire_key_release(entry_url)
        self.assertEqual(ui.pc_image_path, "")


class _SynchronousPool:
    """Stand-in for the module's ThreadPoolExecutor that runs a submitted
    task on the calling (main) thread instead of a pool thread, either
    immediately on submit() (the default) or deferred and queued in
    `pending` - used to simulate an earlier check's worker finishing after a
    later one's, without an actual race.

    Real background threads calling entry.after(0, ...) only work when a
    real Tk mainloop is actively pumping events, which this test suite's
    no-op mainloop patch deliberately isn't (see UserInterfaceTestCase). This
    keeps the after(0, ...) call on the main thread during tests, matching
    what Tk requires, while the production code still uses a real pool."""

    pending = []
    run_immediately = True

    def submit(self, target):
        if self.__class__.run_immediately:
            target()
        else:
            self.__class__.pending.append(target)


class LiveUrlCheckTests(UserInterfaceTestCase):
    """check_url_is_image runs on a background thread after a short debounce,
    then marshals its result back via entry_URL.after(0, ...). These tests
    shrink the debounce to ~0ms, run the "background" work synchronously via
    _SynchronousPool, and poll root.update() briefly so the after(0, ...)
    callback actually gets dispatched within the test."""

    def setUp(self):
        super().setUp()
        self._debounce_patcher = patch("ascii_art.user_interface.URL_CHECK_DEBOUNCE_MS", 1)
        self._debounce_patcher.start()
        self.addCleanup(self._debounce_patcher.stop)

        self._pool_patcher = patch("ascii_art.user_interface._url_check_pool", _SynchronousPool())
        self._pool_patcher.start()
        self.addCleanup(self._pool_patcher.stop)

    def _wait_for_status_text(self, root, label, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root.update()
            if label.cget("text") not in ("", ui.current_lang["url_checking"]):
                return
            time.sleep(0.01)
        raise AssertionError(f"status label never settled, stuck at {label.cget('text')!r}")

    def test_valid_looking_url_shows_success_status(self):
        # a URL that resolves to a real image shows the "valid" status label
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        label = find_url_status_label(root)

        with patch("ascii_art.user_interface.check_url_is_image", return_value=True):
            entry_url.insert(0, "https://example.com/cat.png")
            fire_key_release(entry_url)
            self._wait_for_status_text(root, label)

        self.assertEqual(label.cget("text"), ui.current_lang["url_looks_valid"])

    def test_unreachable_url_shows_failure_status(self):
        # a URL that doesn't resolve to an image shows the "not valid" status label
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        label = find_url_status_label(root)

        with patch("ascii_art.user_interface.check_url_is_image", return_value=False):
            entry_url.insert(0, "https://example.com/nope")
            fire_key_release(entry_url)
            self._wait_for_status_text(root, label)

        self.assertEqual(label.cget("text"), ui.current_lang["url_not_reachable"])

    def test_clearing_the_entry_clears_the_status(self):
        # deleting the typed URL clears the status label back to empty
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        label = find_url_status_label(root)

        with patch("ascii_art.user_interface.check_url_is_image", return_value=True):
            entry_url.insert(0, "https://example.com/cat.png")
            fire_key_release(entry_url)
            self._wait_for_status_text(root, label)

        entry_url.delete(0, "end")
        fire_key_release(entry_url)
        self.assertEqual(label.cget("text"), "")

    def test_stale_result_for_superseded_url_is_discarded(self):
        # an earlier URL's check finishing after a later URL's must not clobber the later result
        root = self.build_mainwindow()
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        label = find_url_status_label(root)

        _SynchronousPool.run_immediately = False
        try:
            with patch("ascii_art.user_interface.check_url_is_image", side_effect=[True, False]):
                entry_url.insert(0, "https://example.com/first")
                fire_key_release(entry_url)
                self._wait_for_debounce(root)
                # url A's worker is now queued but deliberately not run yet

                entry_url.delete(0, "end")
                entry_url.insert(0, "https://example.com/second")
                fire_key_release(entry_url)
                self._wait_for_debounce(root, expected_count=2)

                # run B's worker (consumes True) before A's stale one (consumes False)
                targets, _SynchronousPool.pending = list(reversed(_SynchronousPool.pending)), []
                targets[0]()
                self._wait_for_status_text(root, label)
                self.assertEqual(label.cget("text"), ui.current_lang["url_looks_valid"])

                targets[1]()
                root.update()
        finally:
            _SynchronousPool.run_immediately = True
            _SynchronousPool.pending = []

        # B's result must win; A's late/stale result must have been discarded
        self.assertEqual(label.cget("text"), ui.current_lang["url_looks_valid"])

    def _wait_for_debounce(self, root, expected_count=1, timeout=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root.update()
            if len(_SynchronousPool.pending) >= expected_count:
                return
            time.sleep(0.005)
        raise AssertionError(f"debounced check never queued {expected_count} worker(s), got {len(_SynchronousPool.pending)}")


class OpenTextTests(UserInterfaceTestCase):
    def test_about_button_opens_readme_with_default_app(self):
        # the About button opens ReadMe.txt with the OS's default handler
        root = self.build_mainwindow()
        with patch("ascii_art.user_interface.open_with_default_app") as mock_open:
            find_button(root, "opentext")._command()
        mock_open.assert_called_once()
        self.assertTrue(mock_open.call_args[0][0].endswith("ReadMe.txt"))


class CustomSizeDialogTests(UserInterfaceTestCase):
    """Constructs CustomSizeDialog directly (not via prompt_custom_size) so
    its widgets can be driven without going through the blocking get_size()
    call, which waits on the real Tk event loop via wait_window()."""

    def _build_dialog(self):
        self.build_mainwindow()
        return ui.CustomSizeDialog(
            title="Custom resolution",
            width_label="Width",
            height_label="Height",
            ok_text="Ok",
            cancel_text="Cancel",
            invalid_input_message="Please enter positive whole numbers.",
        )

    def test_valid_input_sets_result(self):
        # valid width/height input sets the dialog's result to the parsed (width, height) tuple
        dialog = self._build_dialog()
        width_entry, height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        width_entry.insert(0, "30")
        height_entry.insert(0, "20")
        dialog._on_ok()
        self.assertEqual(dialog._result, (30, 20))

    def test_non_numeric_characters_cannot_be_typed_into_either_entry(self):
        # non-digit keystrokes are rejected live and never appear in either entry
        dialog = self._build_dialog()
        width_entry, height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        width_entry.insert(0, "not-a-number")
        height_entry.insert(0, "20abc")
        self.assertEqual(width_entry.get(), "")
        self.assertEqual(height_entry.get(), "")

    def test_digits_can_still_be_typed_normally(self):
        # plain digit input is accepted by the entries as normal
        dialog = self._build_dialog()
        width_entry, _height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        width_entry.insert(0, "123")
        self.assertEqual(width_entry.get(), "123")

    def test_submitting_with_an_empty_field_shows_error_and_keeps_dialog_open(self):
        # submitting with one field left empty shows an error instead of a result
        dialog = self._build_dialog()
        _width_entry, height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        height_entry.insert(0, "20")
        dialog._on_ok()
        self.assertIsNone(dialog._result)
        self.assertEqual(dialog._error_label.cget("text"), "Please enter positive whole numbers.")

    def test_non_positive_input_shows_error(self):
        # a width of "0" is rejected as non-positive, showing an error instead of a result
        dialog = self._build_dialog()
        width_entry, height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        width_entry.insert(0, "0")
        height_entry.insert(0, "20")
        dialog._on_ok()
        self.assertIsNone(dialog._result)
        self.assertEqual(dialog._error_label.cget("text"), "Please enter positive whole numbers.")

    def test_cancel_leaves_result_none(self):
        # cancelling the dialog leaves its result as None
        dialog = self._build_dialog()
        dialog._on_cancel()
        self.assertIsNone(dialog._result)

    def test_get_size_blocks_until_dialog_closes_then_returns_result(self):
        # get_size() blocks (via wait_window) until the dialog closes, then returns the entered size
        dialog = self._build_dialog()
        width_entry, height_entry = widgets_of_type(dialog, customtkinter.CTkEntry)
        width_entry.insert(0, "30")
        height_entry.insert(0, "20")
        dialog.after(50, dialog._on_ok)

        result = dialog.get_size()

        self.assertEqual(result, (30, 20))


class MenuTests(UserInterfaceTestCase):
    def test_sms_size_selection(self):
        # selecting the SMS size option sets the fixed 12x12 size
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        optionmenu._command(ui.current_lang["sms_size"])
        self.assertEqual(ui.size, [12, 12])

    def test_original_size_selection(self):
        # selecting the original-size option sets size to "original"
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        optionmenu._command(ui.current_lang["original_size"])
        self.assertEqual(ui.size, "original")

    def test_custom_size_valid_input(self):
        # selecting custom size and entering a valid size sets it
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        with patch.object(ui.CustomSizeDialog, "get_size", return_value=(50, 40)):
            optionmenu._command(ui.current_lang["custom_size"])
        self.assertEqual(ui.size, [50, 40])

    def test_custom_size_cancelled_input(self):
        # cancelling the custom-size dialog leaves size unchanged
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        ui.size = ""
        with patch.object(ui.CustomSizeDialog, "get_size", return_value=None):
            optionmenu._command(ui.current_lang["custom_size"])
        self.assertEqual(ui.size, "")

    def test_custom_size_invalid_then_valid_input(self):
        # the custom-size flow still ends with the size set once a valid result comes back
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        with patch.object(ui.CustomSizeDialog, "get_size", return_value=(30, 20)):
            optionmenu._command(ui.current_lang["custom_size"])
        self.assertEqual(ui.size, [30, 20])


class ChangeLanguageTests(UserInterfaceTestCase):
    def test_toggle_to_same_language_is_a_no_op(self):
        # selecting the already-active language leaves current_lang unchanged
        root = self.build_mainwindow()
        segmented_language = self.segmented_buttons(root)[1]
        segmented_language._command(ui.ENGLISH_LABEL)
        self.assertIs(ui.current_lang, ENGLISH)

    def test_toggle_from_sms_size_label(self):
        # switching language relabels the dropdown's SMS-size option into the new language
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        segmented_language = self.segmented_buttons(root)[1]
        optionmenu.set(ui.current_lang["sms_size"])
        segmented_language._command(ui.CZECH_LABEL)
        self.assertEqual(optionmenu.get(), CZECH["sms_size"])

    def test_toggle_from_original_size_label(self):
        # switching language relabels the dropdown's original-size option into the new language
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        segmented_language = self.segmented_buttons(root)[1]
        optionmenu.set(ui.current_lang["original_size"])
        segmented_language._command(ui.CZECH_LABEL)
        self.assertEqual(optionmenu.get(), CZECH["original_size"])

    def test_toggle_from_custom_size_label(self):
        # switching language relabels the dropdown's custom-size option into the new language
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        segmented_language = self.segmented_buttons(root)[1]
        optionmenu.set(ui.current_lang["custom_size"])
        segmented_language._command(ui.CZECH_LABEL)
        self.assertEqual(optionmenu.get(), CZECH["custom_size"])

    def test_toggle_from_numeric_size_label(self):
        # switching language re-renders a numeric "WxH" label with the new language's symbols suffix
        root = self.build_mainwindow()
        optionmenu = widgets_of_type(root, customtkinter.CTkOptionMenu)[0]
        segmented_language = self.segmented_buttons(root)[1]
        ui.size = [50, 40]
        optionmenu.set("50x40" + ui.current_lang["symbols_suffix"])
        segmented_language._command(ui.CZECH_LABEL)
        self.assertEqual(optionmenu.get(), "50x40" + CZECH["symbols_suffix"])


class GenerateTests(UserInterfaceTestCase):
    def _sample_bytes(self):
        with open(SAMPLE_IMAGE, "rb") as f:
            return f.read()

    def _get_response(self, content=None, content_type="image/png", **kwargs):
        content = self._sample_bytes() if content is None else content
        return make_response(content=content, content_type=content_type, **kwargs)

    def test_missing_both_inputs_shows_popup(self):
        # clicking generate with neither a file nor a URL must show the "choose one image input" popup
        root = self.build_mainwindow()
        ui.size = [10, 10]
        find_button(root, "generate")._command()
        popup = find_popup(root)
        self.assertIsNotNone(popup)
        self.assertEqual(popup.title(), ui.current_lang["missing_image_title"])

    def test_missing_size_shows_popup(self):
        # clicking generate before picking a resolution must show the "select resolution first" popup
        root = self.build_mainwindow()
        ui.size = ""
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")
        find_button(root, "generate")._command()
        popup = find_popup(root)
        self.assertIsNotNone(popup)
        self.assertEqual(popup.title(), ui.current_lang["missing_resolution_title"])

    def test_url_flow_success(self):
        # a valid image URL is downloaded and saved into Results/
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")

        with patch("ascii_art.ui_logic.requests.get", return_value=self._get_response()):
            find_button(root, "generate")._command()

        self.assertTrue(os.path.isfile(os.path.join("Results", "cat.png")))

    def test_url_flow_oversized_download_is_rejected(self):
        # a download declaring a Content-Length over the limit is rejected and not saved
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/huge.png")

        oversized_response = self._get_response(content_length=ui_logic.MAX_DOWNLOAD_BYTES + 1)

        with patch("ascii_art.ui_logic.requests.get", return_value=oversized_response), \
             patch("customtkinter.CTkInputDialog") as MockDialog:
            MockDialog.return_value.get_input.return_value = None
            find_button(root, "generate")._command()

        self.assertFalse(os.path.isfile(os.path.join("Results", "huge.png")))

    def test_url_flow_with_rerun_rebuilds_mainwindow(self):
        # same "New image" rerun regression as the PC-image flow, via the URL branch's own code path
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.png")

        with patch("ascii_art.ui_logic.requests.get", return_value=self._get_response()), \
             patch.object(customtkinter.CTk, "mainloop", click_new_image_when_result_window_opens):
            find_button(root, "generate")._command()

        self.assertIsNot(ui.ui1, root)

    def test_url_flow_unsupported_content_type_then_retry_succeeds(self):
        # first URL is rejected (wrong content-type), corrected URL must still produce a result window
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/cat.html")

        with patch(
            "ascii_art.ui_logic.requests.get",
            side_effect=[self._get_response(content_type="text/html"), self._get_response(content_type="image/png")],
        ), patch("customtkinter.CTkInputDialog") as MockDialog:
            MockDialog.return_value.get_input.return_value = "https://example.com/cat.png"
            find_button(root, "generate")._command()

        result_window = self.created_roots[-1]
        self.assertEqual(result_window.title(), ui.current_lang["result_title"])

    def test_url_flow_non_http_scheme_is_rejected(self):
        # a non-http(s) URL is rejected without ever making a network request
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "file:///etc/passwd")

        with patch("ascii_art.ui_logic.requests.get") as mock_get, \
             patch("customtkinter.CTkInputDialog") as MockDialog:
            MockDialog.return_value.get_input.return_value = None
            find_button(root, "generate")._command()

        mock_get.assert_not_called()

    def test_url_flow_request_exception_then_cancelled_retry(self):
        # cancelling the correction dialog must leave mainwindow open with no result window created
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "not a valid url")

        with patch("customtkinter.CTkInputDialog") as MockDialog:
            MockDialog.return_value.get_input.return_value = None
            find_button(root, "generate")._command()

        self.assertIs(ui.ui1, root)
        self.assertIs(self.created_roots[-1], root)

    def test_url_flow_request_exception_then_retry_succeeds(self):
        # first URL fails to even connect, corrected URL must still produce a result window
        root = self.build_mainwindow()
        ui.size = [10, 8]
        entry_url = widgets_of_type(root, customtkinter.CTkEntry)[0]
        entry_url.insert(0, "https://example.com/broken.png")

        with patch(
            "ascii_art.ui_logic.requests.get",
            side_effect=[requests.RequestException("boom"), self._get_response()],
        ), patch("customtkinter.CTkInputDialog") as MockDialog:
            MockDialog.return_value.get_input.return_value = "https://example.com/fixed.png"
            find_button(root, "generate")._command()

        result_window = self.created_roots[-1]
        self.assertEqual(result_window.title(), ui.current_lang["result_title"])

    def test_pc_image_flow_success(self):
        # a selected PC file generates a result window with the expected title
        root = self.build_mainwindow()
        ui.size = [10, 8]
        ui.pc_image_path = SAMPLE_IMAGE
        find_button(root, "generate")._command()
        result_window = self.created_roots[-1]
        self.assertEqual(result_window.title(), ui.current_lang["result_title"])

    def test_pc_image_flow_with_rerun_rebuilds_mainwindow(self):
        # regression: generate() must not keep running past "New image" destroying its own widgets
        root = self.build_mainwindow()
        ui.size = [10, 8]
        with patch("ascii_art.user_interface.filedialog.askopenfilename", return_value=SAMPLE_IMAGE):
            find_button(root, "openfile")._command()
        self.assertEqual(find_selected_file_label(root).cget("text"), os.path.basename(SAMPLE_IMAGE))

        with patch.object(customtkinter.CTk, "mainloop", click_new_image_when_result_window_opens):
            find_button(root, "generate")._command()

        # a brand new mainwindow() must have been built, with no stale filename left over
        self.assertIsNot(ui.ui1, root)
        self.assertEqual(find_selected_file_label(ui.ui1).cget("text"), "")

    def test_rerun_remembers_the_window_position(self):
        # clicking "New image" preserves the window's on-screen position across the rebuild
        root = self.build_mainwindow()
        root.geometry("650x520+123+45")
        root.update()
        ui.size = [10, 8]
        ui.pc_image_path = SAMPLE_IMAGE

        with patch.object(customtkinter.CTk, "mainloop", click_new_image_when_result_window_opens):
            find_button(root, "generate")._command()

        self.assertEqual(ui.window_position, "+123+45")
        self.assertEqual(ui.ui1.geometry(), f"{ui.WINDOW_SIZE}+123+45")

    def test_remembered_position_off_screen_is_discarded(self):
        # a remembered position outside every monitor's usable area is discarded, not trusted
        ui.window_position = "+999999+999999"
        self.build_mainwindow()
        self.assertEqual(ui.window_position, "")


class SecondWindowTests(UserInterfaceTestCase):
    def _open_result_window(self, width=60, height=5, theme="dark"):
        ui.theme = theme
        data = ["abc\ndef", width, height]
        ui.secondwindow(data)
        return self.created_roots[-1]

    def test_clamps_width_and_height_low(self):
        data = ["abc\ndef", 10, 1]
        ui.theme = "dark"
        ui.secondwindow(data)
        # clamped to the minimums (60 wide, 5 tall), not the requested 10/1
        self.assertEqual(data[1], 60)
        self.assertEqual(data[2], 5)

    def test_clamps_width_and_height_high(self):
        data = ["abc\ndef", 500, 500]
        ui.theme = "dark"
        ui.secondwindow(data)
        # clamped to the maximums (200 wide, 50 tall), not the requested 500/500
        self.assertEqual(data[1], 200)
        self.assertEqual(data[2], 50)

    def test_window_never_exceeds_screen_bounds(self):
        # even the maximum clamped character size stays within the real screen's pixel bounds
        data = ["abc\ndef", 500, 500]
        ui.theme = "dark"
        ui.secondwindow(data)
        root = self.created_roots[-1]
        root.update()
        self.assertLessEqual(root.winfo_width(), root.winfo_screenwidth())
        self.assertLessEqual(root.winfo_height(), root.winfo_screenheight())

    def test_window_position_stays_within_screen_bounds(self):
        # the window's on-screen position (not just its size) is explicitly kept within screen bounds
        data = ["abc\ndef", 500, 500]
        ui.theme = "dark"
        ui.secondwindow(data)
        root = self.created_roots[-1]
        root.update()
        self.assertGreaterEqual(root.winfo_x(), 0)
        self.assertGreaterEqual(root.winfo_y(), 0)
        self.assertLessEqual(root.winfo_x() + root.winfo_width(), root.winfo_screenwidth())
        self.assertLessEqual(root.winfo_y() + root.winfo_height(), root.winfo_screenheight())

    def test_light_theme_background(self):
        # the result window still builds correctly under the light theme
        root = self._open_result_window(theme="light")
        self.assertEqual(root.title(), ui.current_lang["result_title"])

    def test_copy_button_copies_to_clipboard(self):
        # the Copy button copies the generated text-image to the clipboard
        root = self._open_result_window()
        find_button(root, "copy")._command()
        self.assertEqual(root.clipboard_get(), "abc\ndef")

    def test_exit_button_destroys_windows(self):
        # exit must destroy both the main window and the result window
        main_root = self.build_mainwindow()
        result_root = self._open_result_window()
        find_button(result_root, "exit_program")._command()
        # once the whole app is destroyed, even winfo_exists() raises rather
        # than returning False - that TclError is itself proof of destruction
        with self.assertRaises(tkinter.TclError):
            main_root.winfo_exists()
        with self.assertRaises(tkinter.TclError):
            result_root.winfo_exists()

    def test_new_image_button_sets_rerun(self):
        # clicking "New image" sets the rerun flag so a fresh mainwindow() gets built
        self.build_mainwindow()
        root = self._open_result_window()
        find_button(root, "newimage")._command()
        self.assertTrue(ui.rerun)


if __name__ == "__main__":
    unittest.main()
