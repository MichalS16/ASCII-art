"""tkinter/customtkinter GUI: the main window, custom-size dialog, and result window."""

from ascii_art.ascii_generator import generator, SMS_SIZE
from ascii_art.ui_logic import check_url_is_image, fetch_and_save_image, truncate_filename_for_display, InvalidImageUrl
from ascii_art.paths import open_with_default_app, package_file_path
from ascii_art.display import monitor_work_area, geometry_fits_work_area, clamp_and_center_geometry
from ascii_art.translations import ENGLISH, CZECH

from tkinter import Text, filedialog
from concurrent.futures import ThreadPoolExecutor
import customtkinter
import os

LIGHT_LABEL = "Light"
DARK_LABEL = "Dark"
ENGLISH_LABEL = "EN"
CZECH_LABEL = "CZ"

URL_CHECK_DEBOUNCE_MS = 500

# reused across mainwindow() rebuilds (e.g. "New image") instead of spawning
# a new thread per debounced URL check
_url_check_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="url-check")

WINDOW_SIZE = "650x520"

# character-cell bounds for the result window's text area
RESULT_MIN_CHARS_WIDE = 60
RESULT_MAX_CHARS_WIDE = 200
RESULT_MIN_CHARS_TALL = 5
RESULT_MAX_CHARS_TALL = 50

# shared state read/written by mainwindow()/secondwindow() and their nested callbacks
pc_image_path = ""
theme = ""
downstate = ""
size = ""
current_lang = ENGLISH
other_lang = CZECH
rerun = False
window_position = ""


def show_popup_message(message, title):
    """Show a small always-on-top popup with the given message and title."""
    popwindow = customtkinter.CTkToplevel()
    popwindow.geometry("475x50")
    popwindow.title(title)
    popwindow.resizable(0, 0)
    label = customtkinter.CTkLabel(popwindow, text=message, text_color=("black", "snow3"), font=("Verdana", 11, "bold"))
    label.pack(pady=10)


class CustomSizeDialog(customtkinter.CTkToplevel):
    """Modal dialog with separate Width/Height number entries, replacing the
    single 'widthxheight' text field of CTkInputDialog for the custom size
    prompt. Mirrors CTkInputDialog's blocking get_input() pattern: construct,
    then call get_size() to run the dialog and get back (width, height) ints
    or None if cancelled."""

    def __init__(self, title, width_label, height_label, ok_text, cancel_text, invalid_input_message):
        """Build the modal dialog's widget tree (two entries, error label, Ok/Cancel)."""
        super().__init__()
        self._result = None
        self._invalid_input_message = invalid_input_message

        self.title(title)
        self.lift()
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.resizable(False, False)
        self.grab_set()

        self.grid_columnconfigure((0, 1), weight=1)

        # only allow digits
        digits_only = (self.register(self._is_digits_or_empty), "%P")

        label_width = customtkinter.CTkLabel(master=self, text=width_label, font=("Verdana", 12))
        label_width.grid(row=0, column=0, padx=(20, 10), pady=(20, 5), sticky="W")
        self._width_entry = customtkinter.CTkEntry(master=self, width=100, validate="key", validatecommand=digits_only)
        self._width_entry.grid(row=1, column=0, padx=(20, 10), pady=(0, 5))

        label_height = customtkinter.CTkLabel(master=self, text=height_label, font=("Verdana", 12))
        label_height.grid(row=0, column=1, padx=(10, 20), pady=(20, 5), sticky="W")
        self._height_entry = customtkinter.CTkEntry(master=self, width=100, validate="key", validatecommand=digits_only)
        self._height_entry.grid(row=1, column=1, padx=(10, 20), pady=(0, 5))

        self._error_label = customtkinter.CTkLabel(master=self, text="", text_color="firebrick2", font=("Verdana", 10))
        self._error_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 5))

        button_ok = customtkinter.CTkButton(master=self, text=ok_text, command=self._on_ok)
        button_ok.grid(row=3, column=0, padx=(20, 10), pady=(0, 20), sticky="EW")
        button_cancel = customtkinter.CTkButton(master=self, text=cancel_text, command=self._on_cancel)
        button_cancel.grid(row=3, column=1, padx=(10, 20), pady=(0, 20), sticky="EW")

        self._width_entry.bind("<Return>", self._on_ok)
        self._height_entry.bind("<Return>", self._on_ok)
        self.after(150, self._width_entry.focus)

    @staticmethod
    def _is_digits_or_empty(proposed_value):
        """Keystroke validator: only digits (or an empty field) may be typed."""
        return proposed_value == "" or proposed_value.isdigit()

    # validates and sets _result on success, or shows an error and keeps the dialog open
    def _on_ok(self, _event=None):
        # the digits_only keystroke validator already rules out non-numeric
        # characters, but an empty field (isdigit() == False) or "0" still
        # need to be rejected here
        width_text = self._width_entry.get()
        height_text = self._height_entry.get()
        if not width_text.isdigit() or not height_text.isdigit() or int(width_text) <= 0 or int(height_text) <= 0:
            self._error_label.configure(text=self._invalid_input_message)
            return

        self._result = (int(width_text), int(height_text))
        self.grab_release()
        self.destroy()

    # closes the dialog leaving _result as None
    def _on_cancel(self):
        self.grab_release()
        self.destroy()

    def get_size(self):
        """Block until the dialog closes, then return (width, height) or None if cancelled."""
        self.master.wait_window(self)
        return self._result


def mainwindow():
    """Build and run the main window (image source, settings, Generate)."""
    global ui1
    global window_position

    # validates inputs, then downloads/reads the image and opens the result window
    def generate():
        global pc_image_path

        # asks the user to fix or cancel an invalid URL; returns the new URL or None
        def prompt_for_corrected_url():
            dialog = customtkinter.CTkInputDialog(text=current_lang["invalid_url"], title=current_lang["invalid_url_title"])
            return dialog.get_input()

        # clears the inputs after a successful generate, or rebuilds mainwindow() after "New image"
        def finish_and_reset():
            global pc_image_path
            if rerun:
                mainwindow()
                return
            entry_URL.delete(0, "end")
            pc_image_path = ""
            button_select.configure(fg_color="steelblue3")
            label_selected_file.configure(text="")

        url_value = entry_URL.get()

        if size == "":
            show_popup_message(current_lang["select_resolution_first"], current_lang["missing_resolution_title"])
            return

        if not url_value and not pc_image_path:
            show_popup_message(current_lang["choose_one_image_input"], current_lang["missing_image_title"])
            return

        if pc_image_path != "":
            secondwindow(generator(downstate, pc_image_path, size))
            finish_and_reset()
            return

        # url_value is set
        candidate_url = url_value
        while True:
            try:
                filename = fetch_and_save_image(candidate_url)
            except InvalidImageUrl:
                candidate_url = prompt_for_corrected_url()
                if candidate_url is None:
                    return
                continue

            secondwindow(generator(downstate, filename, size))
            finish_and_reset()
            return

    # syncs the module-level downstate flag with the download checkbox
    def downloadstate():
        global downstate

        downstate = checkbox_download.get()

    # opens CustomSizeDialog; the dialog itself handles re-prompting on invalid input
    def prompt_custom_size():
        global size

        dialog = CustomSizeDialog(
            title=current_lang["custom_size_title"],
            width_label=current_lang["width_label"],
            height_label=current_lang["height_label"],
            ok_text=current_lang["ok"],
            cancel_text=current_lang["cancel"],
            invalid_input_message=current_lang["resolution_format_error"],
        )
        result = dialog.get_size()

        if result is None:
            return

        size = list(result)
        optionmenu.set(str(size[0]) + "x" + str(size[1]) + current_lang["symbols_suffix"])

    # sets the module-level size based on the selected dropdown option
    def menu(condition):
        global size

        if condition == current_lang["sms_size"]:
            size = list(SMS_SIZE)
        elif condition == current_lang["original_size"]:
            size = "original"
        elif condition == current_lang["custom_size"]:  # pragma: no branch
            # condition is always one of the three dropdown values above;
            # the "no match" fallthrough is unreachable via the real UI
            prompt_custom_size()

    # opens ReadMe.txt with the OS's default text viewer
    def opentext():
        open_with_default_app(package_file_path(__file__, "ReadMe.txt"))

    # applies the selected Light/Dark theme
    def changetheme(selected_theme):
        global theme

        theme = selected_theme.lower()
        customtkinter.set_appearance_mode(theme)

    # switches all widget text to the selected language
    def changelanguage(selected_language_label):
        global current_lang
        global other_lang

        selected_lang = ENGLISH if selected_language_label == ENGLISH_LABEL else CZECH
        if selected_lang is current_lang:
            return
        current_lang, other_lang = selected_lang, current_lang

        current_size_label = optionmenu.get()
        if current_size_label == other_lang["sms_size"]:
            optionmenu.set(current_lang["sms_size"])
        elif current_size_label == other_lang["original_size"]:
            optionmenu.set(current_lang["original_size"])
        elif current_size_label == other_lang["custom_size"]:
            optionmenu.set(current_lang["custom_size"])
        else:
            optionmenu.set(str(size[0]) + "x" + str(size[1]) + current_lang["symbols_suffix"])

        ui1.title(current_lang["title"])
        label_name1.configure(text=current_lang["app_name"])
        button_select.configure(text=current_lang["select_picture"])
        label_name2.configure(text=current_lang["choose_one_option"])
        entry_URL.configure(placeholder_text=current_lang["insert_url"])
        label_name3.configure(text=current_lang["settings"])
        checkbox_download.configure(text=current_lang["download_txt"])
        label_resolution.configure(text=current_lang["resolution_label"])
        optionmenu.configure(values=[current_lang["sms_size"], current_lang["original_size"], current_lang["custom_size"]])
        button_generate.configure(text=current_lang["generate"])
        button_link.configure(text=current_lang["about"])

    # opens the file picker; selecting a file clears any typed URL (mutually exclusive inputs)
    def openfile():
        global pc_image_path

        chosen_path = filedialog.askopenfilename(title=current_lang["open_image_file"], filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp")])

        if chosen_path == "":
            return

        pc_image_path = chosen_path
        entry_URL.delete(0, "end")
        button_select.configure(fg_color="green")
        label_selected_file.configure(text=truncate_filename_for_display(os.path.basename(chosen_path)))

    # clears any selected file (mutually exclusive inputs) and (re)starts the debounced URL check
    def on_url_typed(_event):
        global pc_image_path

        url_value = entry_URL.get()
        if url_value != "" and pc_image_path != "":
            pc_image_path = ""
            button_select.configure(fg_color="steelblue3")
            label_selected_file.configure(text="")

        schedule_url_check(url_value)

    # bumped on every keystroke so a late-finishing check for a superseded URL is discarded
    url_check_token = 0
    url_check_after_id = None

    # debounces the URL check: cancels any pending check and schedules a new one after typing pauses
    def schedule_url_check(url_value):
        nonlocal url_check_token, url_check_after_id

        if url_check_after_id is not None:
            entry_URL.after_cancel(url_check_after_id)

        if url_value == "":
            label_url_status.configure(text="")
            url_check_after_id = None
            return

        url_check_token += 1
        label_url_status.configure(text=current_lang["url_checking"], text_color=("gray40", "gray70"))
        url_check_after_id = entry_URL.after(URL_CHECK_DEBOUNCE_MS, lambda: run_url_check(url_value, url_check_token))

    # runs check_url_is_image on the shared background pool so typing never blocks on network I/O
    def run_url_check(url_value, token):
        def worker():
            is_valid = check_url_is_image(url_value)
            entry_URL.after(0, lambda: apply_url_check_result(url_value, token, is_valid))

        _url_check_pool.submit(worker)

    # updates the status label with the check result, unless it's now stale
    def apply_url_check_result(url_value, token, is_valid):
        # discard a result for a stale token or a URL the entry no longer holds
        if token != url_check_token or entry_URL.get() != url_value:
            return

        if is_valid:
            label_url_status.configure(text=current_lang["url_looks_valid"], text_color=("green", "light green"))
        else:
            label_url_status.configure(text=current_lang["url_not_reachable"], text_color=("firebrick2", "firebrick1"))

    # reuse the last known window position so rebuilding (e.g. after "New image") doesn't reset it
    ui1 = customtkinter.CTk()

    # discard the remembered position if it's no longer on any monitor's usable area (e.g. DPI/monitor change)
    if window_position:
        win_width, win_height = (int(part) for part in WINDOW_SIZE.split("x"))
        pos_x, pos_y = (int(part) for part in window_position[1:].split("+"))
        work_area = monitor_work_area(ui1.winfo_id(), (ui1.winfo_screenwidth(), ui1.winfo_screenheight()))
        if not geometry_fits_work_area(pos_x, pos_y, win_width, win_height, work_area):
            window_position = ""

    ui1.geometry(WINDOW_SIZE + window_position)
    ui1.title(current_lang["title"])
    ui1.resizable(0, 0)

    frame = customtkinter.CTkFrame(master=ui1, corner_radius=15, fg_color=("white", "snow4"))
    frame.pack(padx=10, pady=10, ipadx=30, ipady=20, fill="both", expand=True)
    frame.grid_columnconfigure(0, weight=1)

    label_name1 = customtkinter.CTkLabel(master=frame, text=current_lang["app_name"], text_color=("snow3", "black"), font=("Verdana", 40))
    label_name1.grid(row=0, column=0, pady=(10, 20))

    # bordered panel grouping the two ways to pick an image (file or URL)
    image_source_section = customtkinter.CTkFrame(master=frame, corner_radius=10, fg_color=("gray90", "gray25"))
    image_source_section.grid(row=1, column=0, padx=20, pady=10, sticky="EW")
    image_source_section.grid_columnconfigure(0, weight=1)

    # select-picture button + filename label; equal spacer columns keep the button centered
    select_row = customtkinter.CTkFrame(master=image_source_section, fg_color="transparent")
    select_row.grid(row=0, column=0, pady=(15, 8))
    select_row.grid_columnconfigure(0, weight=1, uniform="select_row")
    select_row.grid_columnconfigure(2, weight=1, uniform="select_row")

    button_select = customtkinter.CTkButton(master=select_row, command=openfile, width=220, height=40, text=current_lang["select_picture"], font=("Verdana", 16, "bold"), text_color=("white", "black"), fg_color="steelblue3", hover_color=("snow3", "snow2"))
    button_select.grid(row=0, column=1)

    # shows which file (if any) is selected; fixed width + left anchor so it never shifts the layout
    label_selected_file = customtkinter.CTkLabel(master=select_row, text="", text_color=("green", "light green"), font=("Verdana", 10, "bold"), width=140, anchor="w")
    label_selected_file.grid(row=0, column=2, padx=(8, 0), sticky="W")

    label_name2 = customtkinter.CTkLabel(master=image_source_section, text=current_lang["choose_one_option"], text_color=("snow3", "black"), font=("Verdana", 11))
    label_name2.grid(row=1, column=0, pady=(0, 6))

    # URL entry + status label; same balancing-spacer approach as select_row above
    url_row = customtkinter.CTkFrame(master=image_source_section, fg_color="transparent")
    url_row.grid(row=2, column=0, pady=(0, 15))
    url_row.grid_columnconfigure(0, weight=1, uniform="url_row")
    url_row.grid_columnconfigure(2, weight=1, uniform="url_row")

    entry_URL = customtkinter.CTkEntry(master=url_row, height=32, width=280, placeholder_text=current_lang["insert_url"], placeholder_text_color=("steelblue3", "black"), text_color=("steelblue3", "black"), fg_color=("white", "snow4"), border_color="gray40")
    entry_URL.grid(row=0, column=1)
    entry_URL.bind("<KeyRelease>", on_url_typed)

    # live "is this a fetchable image" status; fixed width + left anchor so it never shifts the layout
    label_url_status = customtkinter.CTkLabel(master=url_row, text="", font=("Verdana", 10, "bold"), width=110, anchor="w")
    label_url_status.grid(row=0, column=2, padx=(8, 0), sticky="W")

    # bordered panel grouping output settings (download checkbox + resolution)
    settings_section = customtkinter.CTkFrame(master=frame, corner_radius=10, fg_color=("gray90", "gray25"))
    settings_section.grid(row=2, column=0, padx=20, pady=10, sticky="EW")
    settings_section.grid_columnconfigure((0, 1), weight=1)

    label_name3 = customtkinter.CTkLabel(master=settings_section, text=current_lang["settings"], font=("Verdana", 13, "bold"), text_color=("snow3", "black"))
    label_name3.grid(row=0, column=0, columnspan=2, pady=(12, 12))

    checkbox_download = customtkinter.CTkCheckBox(master=settings_section, command=downloadstate, text=current_lang["download_txt"], font=("Verdana", 11), text_color=("snow3", "black"), fg_color="steelblue3", border_color="gray40", hover_color="steelblue3")
    checkbox_download.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="E")

    # "Resolution:" heading + dropdown on one line, level with the download checkbox
    resolution_group = customtkinter.CTkFrame(master=settings_section, fg_color="transparent")
    resolution_group.grid(row=1, column=1, padx=15, pady=(0, 15), sticky="W")

    label_resolution = customtkinter.CTkLabel(master=resolution_group, text=current_lang["resolution_label"], font=("Verdana", 11, "bold"), text_color=("snow3", "black"))
    label_resolution.grid(row=0, column=0, padx=(0, 8), sticky="W")

    # preselects original size so Generate works without opening the dropdown first
    optionmenu = customtkinter.CTkOptionMenu(master=resolution_group, command=menu, height=32, width=200, font=("Verdana", 11), text_color=("white", "black"), fg_color="steelblue3", button_color=("steelblue2"), button_hover_color=("snow3", "snow2"), dropdown_fg_color="steelblue3", dropdown_text_color=("white", "black"), dropdown_hover_color=("snow3", "snow2"), values=[current_lang["sms_size"], current_lang["original_size"], current_lang["custom_size"]])
    optionmenu.grid(row=0, column=1, sticky="W")
    optionmenu.set(current_lang["original_size"])
    menu(current_lang["original_size"])

    button_generate = customtkinter.CTkButton(master=frame, command=generate, width=240, height=45, text=current_lang["generate"], font=("Verdana", 20, "bold"), text_color=("white", "black"), fg_color="steelblue3", hover_color=("snow3", "snow2"))
    button_generate.grid(row=3, column=0, pady=15)

    # theme switch / About / language switch in 3 equal columns, so About sits on frame's own center
    bottom_bar = customtkinter.CTkFrame(master=frame, fg_color="transparent")
    bottom_bar.grid(row=4, column=0, padx=20, pady=(15, 0), sticky="EW")
    bottom_bar.grid_columnconfigure(0, weight=1)
    bottom_bar.grid_columnconfigure(1, weight=1)
    bottom_bar.grid_columnconfigure(2, weight=1)

    # both theme options always visible/labeled, unlike a single on/off switch
    segmented_theme = customtkinter.CTkSegmentedButton(master=bottom_bar, command=changetheme, values=[LIGHT_LABEL, DARK_LABEL], height=32, font=("Verdana", 11, "bold"), selected_color="steelblue3", selected_hover_color="steelblue2", unselected_color=("gray70", "gray40"))
    segmented_theme.grid(row=0, column=0, sticky="W")

    button_link = customtkinter.CTkButton(master=bottom_bar, command=opentext, width=80, height=32, text=current_lang["about"], font=("Verdana", 11, "underline"), text_color=("snow3", "black"), fg_color="transparent", hover=False)
    button_link.grid(row=0, column=1, sticky="W", padx=(65, 0))

    segmented_language = customtkinter.CTkSegmentedButton(master=bottom_bar, command=changelanguage, values=[ENGLISH_LABEL, CZECH_LABEL], height=32, font=("Verdana", 11, "bold"), selected_color="steelblue3", selected_hover_color="steelblue2", unselected_color=("gray70", "gray40"))
    segmented_language.grid(row=0, column=2, sticky="E")

    if theme == "light":
        customtkinter.set_appearance_mode("light")
        segmented_theme.set(LIGHT_LABEL)
    else:
        customtkinter.set_appearance_mode("dark")
        segmented_theme.set(DARK_LABEL)

    segmented_language.set(ENGLISH_LABEL if current_lang is ENGLISH else CZECH_LABEL)

    ui1.mainloop()


def secondwindow(textimagedata):
    """Build and run the result window showing the generated ASCII text-image."""
    global rerun
    rerun = False

    # destroys both windows and sets rerun so generate() rebuilds a fresh mainwindow()
    def newimage():
        global rerun
        global window_position
        rerun = True
        window_position = f"+{ui1.winfo_x()}+{ui1.winfo_y()}"
        ui2.destroy()
        ui1.destroy()

    # copies the generated text-image to the clipboard
    def copy():
        ui2.clipboard_clear()
        ui2.clipboard_append(text.get("1.0", "end-1c"))

    # closes both windows, ending the app
    def exit_program():
        ui2.destroy()
        ui1.destroy()

    # clamp the requested character size to the min/max bounds
    width = max(RESULT_MIN_CHARS_WIDE, min(textimagedata[1], RESULT_MAX_CHARS_WIDE))
    height = max(RESULT_MIN_CHARS_TALL, min(textimagedata[2], RESULT_MAX_CHARS_TALL))
    textimagedata[1], textimagedata[2] = width, height

    themecolor = "snow3" if theme == "dark" else "snow2"

    # geometry is set later, once the real widget tree has been measured (see measure_window_size_for)
    ui2 = customtkinter.CTk()
    ui2.title(current_lang["result_title"])
    ui2.resizable(1, 1)

    frame = customtkinter.CTkFrame(master=ui2, corner_radius=15, fg_color=("white", "snow4"))
    frame.pack(padx=10, pady=10, fill="both", expand=True)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(1, weight=1)

    label_name4 = customtkinter.CTkLabel(master=frame, text=current_lang["result_hint"], text_color=("snow3", "black"), font=("Verdana", 11, "bold"))
    label_name4.grid(row=0, column=0, pady=(15, 10), padx=20)

    # scrollbars keep all the text reachable even if the window ends up smaller than the art's natural size
    text_container = customtkinter.CTkFrame(master=frame, corner_radius=10, fg_color=("gray90", "gray25"))
    text_container.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="NSEW")
    text_container.grid_columnconfigure(0, weight=1)
    text_container.grid_rowconfigure(0, weight=1)

    text = Text(text_container, width=textimagedata[1], height=textimagedata[2], bg=themecolor, bd=0, wrap="none")
    text.tag_configure("center", justify='center')
    text.insert("1.0", textimagedata[0])
    text.tag_add("center", "1.0", "end")
    text.grid(row=0, column=0, padx=(10, 0), pady=(10, 0), sticky="NSEW")

    text_vscroll = customtkinter.CTkScrollbar(master=text_container, orientation="vertical", command=text.yview)
    text_vscroll.grid(row=0, column=1, padx=(0, 10), pady=(10, 0), sticky="NS")
    text_hscroll = customtkinter.CTkScrollbar(master=text_container, orientation="horizontal", command=text.xview)
    text_hscroll.grid(row=1, column=0, padx=(10, 0), pady=(0, 10), sticky="EW")
    text.configure(yscrollcommand=text_vscroll.set, xscrollcommand=text_hscroll.set)

    button_bar = customtkinter.CTkFrame(master=frame, fg_color="transparent")
    button_bar.grid(row=2, column=0, pady=(0, 15))

    button_new = customtkinter.CTkButton(master=button_bar, command=newimage, width=140, height=36, text=current_lang["new_image"], font=("Verdana", 14), text_color=("white", "black"), fg_color="steelblue3", hover_color=("snow3", "snow2"))
    button_new.grid(row=0, column=0, padx=8)

    button_copy = customtkinter.CTkButton(master=button_bar, command=copy, width=140, height=36, text=current_lang["copy"], font=("Verdana", 14), text_color=("white", "black"), fg_color="steelblue3", hover_color=("snow3", "snow2"))
    button_copy.grid(row=0, column=1, padx=8)

    button_exit = customtkinter.CTkButton(master=button_bar, command=exit_program, width=140, height=36, text=current_lang["exit"], font=("Verdana", 14), text_color=("white", "black"), fg_color="steelblue3", hover_color=("snow3", "snow2"))
    button_exit.grid(row=0, column=2, padx=8)

    # measures the Text widget's real required size at given character dimensions, instead of guessing pixels-per-character
    def measure_window_size_for(chars_wide, chars_tall):
        text.configure(width=chars_wide, height=chars_tall)
        ui2.update_idletasks()
        return ui2.winfo_reqwidth(), ui2.winfo_reqheight()

    winwidth, winheight = measure_window_size_for(width, height)
    max_pixel_width, max_pixel_height = measure_window_size_for(RESULT_MAX_CHARS_WIDE, RESULT_MAX_CHARS_TALL)
    min_pixel_width, min_pixel_height = measure_window_size_for(RESULT_MIN_CHARS_WIDE, RESULT_MIN_CHARS_TALL)
    text.configure(width=width, height=height)  # restore the actual content size

    # clamp size to the target monitor's usable work area (screen minus taskbar) so it never opens off-screen
    screen_margin = 80
    work_area = monitor_work_area(ui2.winfo_id(), (ui2.winfo_screenwidth(), ui2.winfo_screenheight()))

    max_pixel_width, max_pixel_height, _, _ = clamp_and_center_geometry(max_pixel_width, max_pixel_height, work_area, margin=screen_margin)
    # the minimum must also fit, or Tk's minsize could keep the window bigger than an unusually small screen
    min_pixel_width = min(min_pixel_width, max_pixel_width)
    min_pixel_height = min(min_pixel_height, max_pixel_height)
    # centers within the work area explicitly, since Tk's default placement ignores the just-measured size
    winwidth, winheight, pos_x, pos_y = clamp_and_center_geometry(min(winwidth, max_pixel_width), min(winheight, max_pixel_height), work_area)

    ui2.geometry(f"{winwidth}x{winheight}+{pos_x}+{pos_y}")
    ui2.minsize(min_pixel_width, min_pixel_height)
    ui2.maxsize(max_pixel_width, max_pixel_height)

    ui2.mainloop()


def run():
    """Module entry point: build and run the main window."""
    try:
        mainwindow()
    finally:
        # don't let a check still in flight (e.g. a slow/hanging host) delay
        # process exit; ThreadPoolExecutor's worker threads aren't daemons,
        # so without this the interpreter would wait on them at shutdown
        _url_check_pool.shutdown(wait=False, cancel_futures=True)
