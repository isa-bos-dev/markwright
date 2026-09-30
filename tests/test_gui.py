import gc
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections.abc import Callable, Iterator
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter import font as tkfont

import conversion_fakes as fakes
import pytest

from markwright.core.converter import ConversionStage, ConversionWarning
from markwright.core.exceptions import InvalidPasswordError
from markwright.gui.assets import load_image
from markwright.gui.gui import App
from markwright.gui.main_screen import MainScreen, _open_in_file_manager
from markwright.gui.settings import Settings
from markwright.gui.settings_dialog import SettingsDialog
from markwright.gui.theme import apply_theme
from markwright.gui.tooltip import Tooltip
from markwright.i18n import t

_WAIT_TIMEOUT_SECONDS = 5


@pytest.fixture(scope="session")
def tk_root() -> Iterator[tk.Tk]:
    """One hidden Tk root shared by the whole session (each Tk start-up is costly).

    The GUI tests are skipped when the machine has no display.
    """
    try:
        root = tk.Tk()
    except tk.TclError as error:
        if "display" not in str(error):
            raise
        pytest.skip(f"no display available for Tk: {error}")
    root.withdraw()
    apply_theme(root)
    yield root
    root.destroy()


def _release_tk_garbage() -> None:
    """Finalize leftover Tk objects here, on the main thread.

    If the garbage collector ran inside a worker thread instead, finalizing a Tk
    object would need the main loop (which these tests do not run) and stall.
    """
    gc.collect()


@pytest.fixture
def main_screen(tk_root: tk.Tk) -> Iterator[MainScreen]:
    screen = MainScreen(tk_root, "en")
    yield screen
    screen.destroy()
    _release_tk_garbage()


def _pump(root: tk.Tk, condition: Callable[[], bool]) -> None:
    """Process Tk events until ``condition()`` holds (the GUI polls its worker via after())."""
    deadline = time.monotonic() + _WAIT_TIMEOUT_SECONDS
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail("timed out waiting for the GUI")
        root.update()
        time.sleep(0.01)


def _pump_for(root: tk.Tk, seconds: float) -> None:
    """Keep processing Tk events for a while (several polls of the worker queue)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)


def _is_shown(widget: tk.Widget) -> bool:
    return bool(widget.grid_info())


def _choose_pdf(screen: MainScreen, monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **_: str(path))
    screen.choose_button.invoke()


def test_packaged_images_load_at_their_declared_size(tk_root: tk.Tk) -> None:
    image = load_image("logo-56.png", tk_root)

    assert (image.width(), image.height()) == (56, 56)


# --- Theme ---


def test_font_size_small_and_large_scale_relative_to_normal(tk_root: tk.Tk) -> None:
    apply_theme(tk_root, font_size="normal")
    normal_size = tkfont.nametofont("SunValleyTitleFont", tk_root).actual("size")

    apply_theme(tk_root, font_size="large")
    large_size = tkfont.nametofont("SunValleyTitleFont", tk_root).actual("size")

    apply_theme(tk_root, font_size="small")
    small_size = tkfont.nametofont("SunValleyTitleFont", tk_root).actual("size")

    apply_theme(tk_root, font_size="normal")  # restore for the rest of the suite
    assert (small_size, large_size) == (normal_size - 2, normal_size + 2)


def test_reapplying_the_same_font_size_does_not_compound(tk_root: tk.Tk) -> None:
    apply_theme(tk_root, font_size="large")
    first = tkfont.nametofont("SunValleyTitleFont", tk_root).actual("size")

    apply_theme(tk_root, font_size="large")
    second = tkfont.nametofont("SunValleyTitleFont", tk_root).actual("size")

    apply_theme(tk_root, font_size="normal")  # restore for the rest of the suite
    assert first == second


def test_switching_theme_changes_the_status_label_colors(tk_root: tk.Tk) -> None:
    apply_theme(tk_root, theme="light")
    light_color = ttk.Style(tk_root).lookup("Error.TLabel", "foreground")

    apply_theme(tk_root, theme="dark")
    dark_color = ttk.Style(tk_root).lookup("Error.TLabel", "foreground")

    apply_theme(tk_root, theme="light")  # restore for the rest of the suite
    assert light_color != dark_color


# --- App startup ---


def test_app_starts_on_main_screen_and_the_gear_icon_changes_and_persists_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One App() for both facts: a second live Tk root in the same process is best avoided."""
    monkeypatch.setattr("markwright.gui.gui.load_settings", lambda: Settings())
    saved: list[Settings] = []
    monkeypatch.setattr("markwright.gui.gui.save_settings", saved.append)

    app = App()
    app.withdraw()
    try:
        assert len(app.winfo_children()) == 1
        assert isinstance(app.screen, MainScreen)
        assert app.screen.convert_button.cget("text") == t("main.convert", "en")

        app.screen.settings_button.invoke()
        dialog = next(child for child in app.winfo_children() if isinstance(child, SettingsDialog))
        dialog.language_buttons["es"].invoke()

        assert app.screen.convert_button.cget("text") == t("main.convert", "es")
        assert saved == [Settings(language="es")]
        dialog.destroy()
    finally:
        app.destroy()
    _release_tk_garbage()


# --- Main screen ---


def test_choosing_a_pdf_and_converting_shows_where_the_result_was_saved(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "report.md"
    fakes.install(monkeypatch, fakes.returning(output))
    assert main_screen.convert_button.instate(["disabled"])

    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")
    assert main_screen.file_label.cget("text") == "report.pdf"
    assert main_screen.convert_button.instate(["!disabled"])

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert t("main.saved_to", "en", path=output) in main_screen.status_label.cget("text")


def test_a_protected_pdf_asks_for_the_password_and_retries_with_it(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str | None] = []

    def fake_convert(input_path, password=None, on_progress=None):
        calls.append(password)
        if password != "right":
            raise InvalidPasswordError(input_path)
        return tmp_path / "report.md"

    fakes.install(monkeypatch, fake_convert)
    assert not _is_shown(main_screen.password_entry)
    assert main_screen.password_entry.cget("show") == "•"

    pdf = tmp_path / "report.pdf"
    _choose_pdf(main_screen, monkeypatch, pdf)
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.password_entry))
    assert t("error.invalid_password", "en", path=pdf) in main_screen.status_label.cget("text")

    main_screen.password_entry.insert(0, "right")
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert calls == [None, "right"]


def test_a_partial_conversion_shows_the_warning_and_the_saved_file(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "report.md"
    warning = ConversionWarning(retryable=True, categories=("timeout",), affected_pages=(2,))

    def fake_convert(input_path, password=None, on_progress=None):
        on_progress(ConversionStage.PARTIAL_SUCCESS, warning)
        return output

    fakes.install(monkeypatch, fake_convert)
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    text = main_screen.status_label.cget("text")
    assert t("progress.partial_success.retryable", "en") in text
    assert t("main.saved_to", "en", path=output) in text


def test_cancelling_the_file_dialog_changes_nothing(
    main_screen: MainScreen, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **_: "")

    main_screen.choose_button.invoke()

    assert main_screen.file_label.cget("text") == t("main.no_file", "en")
    assert main_screen.convert_button.instate(["disabled"])


def test_choosing_another_file_clears_the_previous_message_and_password_request(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fakes.install(monkeypatch, fakes.raising(InvalidPasswordError))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "first.pdf")
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.password_entry))

    _choose_pdf(main_screen, monkeypatch, tmp_path / "second.pdf")

    assert main_screen.file_label.cget("text") == "second.pdf"
    assert main_screen.status_label.cget("text") == ""
    assert not _is_shown(main_screen.password_entry)


def test_an_unexpected_error_shows_a_generic_message_and_unlocks_the_controls(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fakes.install(monkeypatch, fakes.raising(lambda _: RuntimeError("bug")))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump(
        tk_root,
        lambda: (
            main_screen.convert_button.instate(["!disabled"])
            and main_screen.status_label.cget("text") != ""
        ),
    )

    assert main_screen.status_label.cget("text") == t("error.unexpected_gui", "en")
    assert not _is_shown(main_screen.open_folder_button)


def test_an_unexpected_error_never_leaks_its_technical_detail_however_sensitive(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SEC-TH-003: whatever the underlying exception says, only the generic message shows."""
    sensitive = RuntimeError(r"failed at C:\Users\dev\.venv\Lib\site-packages\torch\_ops.py:42")
    fakes.install(monkeypatch, fakes.raising(lambda _: sensitive))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: main_screen.status_label.cget("text") != "")

    shown = main_screen.status_label.cget("text")
    assert shown == t("error.unexpected_gui", "en")
    assert "site-packages" not in shown
    assert "dev" not in shown


def test_controls_stay_locked_across_several_polls_and_unlock_afterwards(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    release = threading.Event()
    fakes.install(monkeypatch, fakes.blocked_until(release, tmp_path / "report.md"))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump_for(tk_root, 0.35)  # several 100 ms polls find the queue empty and reschedule

    assert main_screen.convert_button.instate(["disabled"])
    assert main_screen.choose_button.instate(["disabled"])
    assert _is_shown(main_screen.progress)

    release.set()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert main_screen.convert_button.instate(["!disabled"])
    assert not _is_shown(main_screen.progress)


def test_the_current_stage_is_shown_while_converting(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    release = threading.Event()

    def staged_convert(input_path, password=None, on_progress=None):
        on_progress(ConversionStage.STARTED)
        release.wait(timeout=_WAIT_TIMEOUT_SECONDS)
        return tmp_path / "report.md"

    fakes.install(monkeypatch, staged_convert)
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: main_screen.status_label.cget("text") == t("progress.started", "en"))

    release.set()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))


def test_a_second_conversion_cannot_start_while_one_is_running(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    release = threading.Event()
    started: list[int] = []
    fakes.install(monkeypatch, fakes.blocked_until(release, tmp_path / "report.md", started))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")
    main_screen.convert_button.invoke()

    main_screen._start_conversion()  # what pressing Enter in the password field triggers
    release.set()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert started == [1]


def test_closing_the_screen_during_a_conversion_leaves_no_pending_updates(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    release = threading.Event()
    fakes.install(monkeypatch, fakes.blocked_until(release, tmp_path / "report.md"))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")
    main_screen.convert_button.invoke()

    main_screen.destroy()
    release.set()

    _pump_for(tk_root, 0.4)  # a poll left behind on the destroyed screen would raise here


def test_the_open_folder_button_opens_the_folder_of_the_result(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    opened: list[Path] = []
    monkeypatch.setattr("markwright.gui.main_screen._open_in_file_manager", opened.append)
    fakes.install(monkeypatch, fakes.returning(tmp_path / "report.md"))
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    main_screen.open_folder_button.invoke()

    assert opened == [tmp_path]


def test_on_windows_the_folder_is_opened_with_startfile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", opened.append, raising=False)

    _open_in_file_manager(tmp_path)

    assert opened == [tmp_path]


@pytest.mark.parametrize(("platform", "command"), [("darwin", "open"), ("linux", "xdg-open")])
def test_on_other_platforms_the_folder_is_opened_with_the_system_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, platform: str, command: str
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append(args))
    _open_in_file_manager(tmp_path)

    assert calls == [[command, str(tmp_path)]]


# --- Tooltip ---


def test_hovering_shows_a_popup_with_the_text(tk_root: tk.Tk) -> None:
    button = ttk.Button(tk_root, text="?")
    button.pack()
    tooltip = Tooltip(button, "Hello")

    tooltip._show()

    assert tooltip._popup is not None
    assert tooltip._popup.winfo_children()[0].cget("text") == "Hello"

    tooltip._hide()
    button.destroy()
    _release_tk_garbage()


def test_leaving_hides_the_popup(tk_root: tk.Tk) -> None:
    button = ttk.Button(tk_root, text="?")
    button.pack()
    tooltip = Tooltip(button, "Hello")
    tooltip._show()

    tooltip._hide()

    assert tooltip._popup is None
    button.destroy()
    _release_tk_garbage()


def test_showing_twice_does_not_create_a_second_popup(tk_root: tk.Tk) -> None:
    button = ttk.Button(tk_root, text="?")
    button.pack()
    tooltip = Tooltip(button, "Hello")

    tooltip._show()
    first_popup = tooltip._popup
    tooltip._show()

    assert tooltip._popup is first_popup

    tooltip._hide()
    button.destroy()
    _release_tk_garbage()


def test_hiding_without_having_shown_is_a_no_op(tk_root: tk.Tk) -> None:
    button = ttk.Button(tk_root, text="?")
    button.pack()
    tooltip = Tooltip(button, "Hello")

    tooltip._hide()  # must not raise

    button.destroy()
    _release_tk_garbage()


# --- Settings ---


def test_the_gear_button_opens_settings(tk_root: tk.Tk) -> None:
    opened = []
    screen = MainScreen(tk_root, "en", on_open_settings=lambda: opened.append(1))

    screen.settings_button.invoke()

    screen.destroy()
    _release_tk_garbage()
    assert opened == [1]


def test_the_gear_button_does_nothing_without_a_settings_callback(main_screen: MainScreen) -> None:
    main_screen.settings_button.invoke()  # must not raise


def test_refresh_language_relocalizes_the_static_labels(main_screen: MainScreen) -> None:
    main_screen.refresh_language("es")

    assert main_screen.convert_button.cget("text") == t("main.convert", "es")
    assert main_screen.file_label.cget("text") == t("main.no_file", "es")
    assert main_screen._settings_tooltip.text == t("settings.gear_tooltip", "es")


def test_refresh_language_keeps_an_already_chosen_file_name(
    main_screen: MainScreen, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.refresh_language("es")

    assert main_screen.file_label.cget("text") == "report.pdf"


@pytest.fixture
def settings_dialog(tk_root: tk.Tk) -> Iterator[tuple[SettingsDialog, list[Settings]]]:
    changes: list[Settings] = []
    dialog = SettingsDialog(tk_root, Settings(), on_change=changes.append)
    yield dialog, changes
    dialog.destroy()
    _release_tk_garbage()


def test_picking_a_language_reports_the_updated_settings(
    settings_dialog: tuple[SettingsDialog, list[Settings]],
) -> None:
    dialog, changes = settings_dialog

    dialog.language_buttons["es"].invoke()

    assert changes == [Settings(language="es")]


def test_picking_a_theme_reports_the_updated_settings(
    settings_dialog: tuple[SettingsDialog, list[Settings]],
) -> None:
    dialog, changes = settings_dialog

    dialog.theme_buttons["dark"].invoke()

    assert changes == [Settings(theme="dark")]


def test_picking_a_font_size_reports_the_updated_settings(
    settings_dialog: tuple[SettingsDialog, list[Settings]],
) -> None:
    dialog, changes = settings_dialog

    dialog.font_size_buttons["large"].invoke()

    assert changes == [Settings(font_size="large")]


def test_choices_accumulate_onto_the_same_settings_object(
    settings_dialog: tuple[SettingsDialog, list[Settings]],
) -> None:
    dialog, changes = settings_dialog

    dialog.theme_buttons["dark"].invoke()
    dialog.font_size_buttons["small"].invoke()

    assert changes[-1] == Settings(theme="dark", font_size="small")


def test_the_dialog_title_and_labels_use_the_initial_settings_language(tk_root: tk.Tk) -> None:
    dialog = SettingsDialog(tk_root, Settings(language="es"), on_change=lambda _s: None)

    assert dialog.title() == t("settings.title", "es")
    assert dialog.theme_buttons["dark"].cget("text") == t("settings.theme.dark", "es")

    dialog.destroy()
    _release_tk_garbage()
