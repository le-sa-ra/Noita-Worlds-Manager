"""
Dear Tinkerer,

Before you peek into the guts of the program, know this:
This (originally tiny) idea was initially meant to only create symlinks for any Noita save I felt like playing.
Primarily, for me to swap between my legitimate save and a "multiplayer" save with my friends without any hassle of copying and moving folders.
Every other feature beyond that I felt like adding to this program for fun, was hacked together -
very poorly, with no thought behind it, with no structure in mind...

If you were curious how something worked and wanted to check it out for your own ideas, I'm sorry.
"""
import src.Utils as Util
from ttkbootstrap.style import ThemeDefinition
from tkinter import filedialog, Canvas
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import src.ExtendedFrame as Ef
import ttkbootstrap as tb
import tkinter as tk
import shutil
import json
import sys
import os

try:
    Util.ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass
WINDOW_SCALING = 64

show_advanced_settings_options = False
mouse_btn_1_clicked_once = False
first_key_frame_selected = None
next_input_is_selector = None
frame_move_manager = None
set_swap_select = None


def run_selection(frame, command=None):
    global config
    if not command and len(config["world_paths"]) <= 1:
        Util.notification(0, {"type": "info", "title": "No need to swap",
                              "message": "Not enough saves available to swap with..."})
        return
    if command and len(config["world_paths"]) == 0:
        Util.notification(0, {"type": "info", "title": "Nothing to select", "message": "No saves can be selected..."})
        return
    global set_swap_select

    if isinstance(set_swap_select, Ef.Swapper):
        set_swap_select.re_toggle()
        set_swap_select = None
    else:
        set_swap_select = Ef.Swapper(frame, config, cancel_select_swapper, command)


def cancel_select_swapper():
    global set_swap_select
    if isinstance(set_swap_select, Ef.Swapper):
        set_swap_select.re_toggle()
        set_swap_select = None
        return True
    set_swap_select = None
    return False


def run_keypress(event):
    global mouse_btn_1_clicked_once
    global next_input_is_selector
    global config

    key = f"key-{event.keysym}"
    if key == "key-??":
        key = f"mbt-{event.num}"

    if not next_input_is_selector:
        mouse_btn_1_clicked_once = False
        if key.startswith("mbt-") and not key == "mbt-1":
            execute_keypress_action(key)
            return

    if key == "mbt-1":
        if isinstance(window.winfo_containing(window.winfo_pointerx(), window.winfo_pointery()),
                      (Ef.ScrollSelectionText, tb.Text, tb.Entry)):
            if next_input_is_selector and mouse_btn_1_clicked_once:
                next_input_is_selector = None
                frame_move_manager.reload_frame()
            mouse_btn_1_clicked_once = False
            return

    if key == "mbt-1" and not next_input_is_selector:
        root.focus_set()

    w = root.focus_get()
    if w and w.winfo_class() in ("TEntry", "Text", "Spinbox", "TCombobox"):
        return

    if key == "mbt-1":
        if mouse_btn_1_clicked_once:
            mouse_btn_1_clicked_once = False
            for dict_key, action in config["keybind"].items():
                if action == next_input_is_selector:
                    key = dict_key
        elif next_input_is_selector:
            mouse_btn_1_clicked_once = True
            return
    if next_input_is_selector:

        if not key in config["keybind"].keys():
            for dict_key, action in config["keybind"].items():
                if action == next_input_is_selector:
                    config["keybind"].pop(dict_key)
                    config["keybind"][key] = next_input_is_selector
                    mouse_btn_1_clicked_once = False
                    break
        next_input_is_selector = None
        frame_move_manager.reload_frame()
        return
    execute_keypress_action(key)


def execute_keypress_action(key):
    if key in config["keybind"].keys():
        if config["keybind"][key] == "Home":
            Ef.update_search_term("")
        action_to_funk_map[config["keybind"][key]]()


def reset_pressed_play():
    global _pressed_play
    if _pressed_play:
        if not Util.process_running():
            _pressed_play = False
            Util.pause(1)
            window.tk.call('tk', 'scaling', WINDOW_SCALING)
            frame_move_manager.reload_frame()
            window.update_idletasks()
            window.deiconify()
            window.iconbitmap(ICON)
            resize_window()
            return
    window.after(500, reset_pressed_play)


def wait_for_running_noita():
    if Util.process_running():
        window.after(500, reset_pressed_play)
        return
    window.after(500, wait_for_running_noita)


def try_open_mod(mod_args_idx):
    global config

    if config["modded_starter_agrs"][mod_args_idx]["application_path"]:
        if os.path.exists(config["modded_starter_agrs"][mod_args_idx]["application_path"]):
            return config["modded_starter_agrs"][mod_args_idx]["application_path"]
        elif isinstance(config["modded_starter_agrs"][mod_args_idx]["application_path"], str):
            return ""
        else:
            path_set = Util.get_mod_app_path(mod_args_idx, config)
            if path_set:
                return try_open_mod(mod_args_idx)
    else:
        path_set = Util.get_mod_app_path(mod_args_idx, config)
        if path_set:
            return try_open_mod(mod_args_idx)
    if Util.notification(5, {"type": "ask",
                             "title": f"Warning: Running Noita without \"{config["modded_starter_agrs"][mod_args_idx]["mod_name"]}\"",
                             "message": "Running noita without the enabled mods application could cause unwanted behaviour in-game...\n\nDo you still want to start Noita?"}):
        return ""
    return None


def start_noita(noita_start_args=[]):

    global _pressed_play
    if Util.process_running() or _pressed_play:
        Util.notification(0, {"type": "warn", "title": "Already running", "message": "Noita is already running!"})
        return False
    run_fail = False
    start_noita_too = False
    start_mod_path = []
    for arg in noita_start_args:
        start_noita_mod = try_open_mod(arg[0])
        start_noita_too = start_noita_too or arg[1]["start_noita_too"]
        if isinstance(start_noita_mod, str):
            if start_noita_mod:
                start_mod_path.append([start_noita_mod, arg[1]["looking_for"].split("/")[-1].lower()])
        else:
            return False
    _pressed_play = True
    window.withdraw()
    wait_for_running_noita()
    for mod_starters in start_mod_path:
        if not Util.process_running(mod_starters[1]):
            if not Util.open_path_process(mod_starters[0]):
                run_fail = True
                break
    if not run_fail:
        if start_noita_too or len(start_mod_path) == 0:
            if not Util.open_path_process(config["game"].get("noita_runner_arg", None)):
                run_fail = True

    if run_fail:
        _pressed_play = False
        Util.pause(1)
        window.tk.call('tk', 'scaling', WINDOW_SCALING)
        frame_move_manager.reload_frame()
        window.update_idletasks()
        window.deiconify()
        window.iconbitmap(ICON)
        resize_window()

    return not run_fail


def add_save_path(path):
    real_path = path.replace("\\", "/")
    if Util.path_is_symlink(real_path):
        real_path = os.path.realpath(path)
    if os.path.exists(real_path):
        if Util.NOITA_SAVE_PATH.replace(r"\Nolla_Games_Noita", "") in real_path:
            Util.notification(3, {"type": "warn", "title": "Original Noita path", "message":
                f"Path \"{real_path}\" leads to the main Noita save path.\nPlease move your save away from the main Noita path."})
            return False
        if Util.NOITA_SAVE_PATH in real_path:
            Util.notification(3, {"type": "warn", "title": "Original Noita path", "message":
                f"Path \"{real_path}\" leads to the main Noita save path.\nPlease move your save away from the main Noita path."})
            return False
        if real_path in config["world_paths"]:
            Util.notification(3, {"type": "warn", "title": "Already a save entry", "message":
                f"Path \"{real_path}\" is already a save entry in the worlds manager."})
            return False
        if config["save_management"]["new_save_entries_to_start"]:
            config["world_paths"].append(real_path)
        else:
            config["world_paths"].insert(0, real_path)
        return real_path
    Util.notification(2, {"type": "warn", "title": "",
                          "message": f"We cannot proceed because:\n{real_path}\ndoes not exist..."})
    return False


def move_playing_path():
    if os.path.exists(Util.NOITA_SAVE_PATH):
        global config
        if Util.path_is_symlink(Util.NOITA_SAVE_PATH):
            current_link = os.path.realpath(Util.NOITA_SAVE_PATH).replace("\\", "/").replace("/Nolla_Games_Noita", "")
            if current_link not in config["world_paths"]:
                if os.path.exists(current_link + f"/data.json"):
                    with open(current_link + f"/data.json") as f:
                        if "is_backup_of" in json.load(f).keys():
                            return current_link
                    add_save_path(current_link)
            return current_link
        else:
            move_path = ""
            if Util.notification(99, {"type": "ask", "title": "More original folder", "message":
                "The folder \"Nolla_Games_Noita\" already exists.\nTo proceed we will need to move it elsewhere..."}):
                move_path = tk.filedialog.askdirectory(initialdir=os.getcwd())
                if not move_path:
                    Util.notification(5, {"type": "warn", "title": "", "message":
                        f"{move_path} is an invalid path!"})
                    return False
                if len(os.listdir(move_path)) >= 1:
                    Util.notification(5, {"type": "info", "title": "Non empty folder given", "message":
                        f"We cannot proceed because:\n{move_path}\nis not emtpy...\n(please try again with an empty folder!)"})
                    return False
            if not move_path:
                Util.notification(5, {"type": "warn", "title": "Cannot proceed", "message":
                    f"We cannot proceed until:\n{Util.NOITA_SAVE_PATH}\nis moved...\n(You can also make a backup manually)"})
                return False
            shutil.move(Util.NOITA_SAVE_PATH, move_path)
            Util.create_symlink(move_path + "/Nolla_Games_Noita", Util.NOITA_SAVE_PATH)
            add_save_path(move_path)
            return move_path
    else:
        return True


def play_selected_world(world_path):
    global set_swap_select
    global config
    if not os.path.exists(world_path + "/Nolla_Games_Noita"):
        os.mkdir(world_path + "/Nolla_Games_Noita")

    config["appearance"]["geometry"] = window.geometry()
    config["appearance"]["state"] = window.state()

    if isinstance(set_swap_select, Ef.Swapper):
        Util.notification(2, {"type": "warn", "title": "Cannot select",
                              "message": f"Cannot select worlds while they are loading in..."})
        return False

    if not move_playing_path():
        Util.notification(4, {"type": "info", "title": "Could not move world",
                              "message": f"Failed to run selected world...\n{world_path}"})
    else:
        success = False
        if not Util.path_is_symlink(Util.NOITA_SAVE_PATH):
            if Util.create_symlink(world_path + "/Nolla_Games_Noita", Util.NOITA_SAVE_PATH):
                success = True
        if not success:
            success = Util.update_symlink(world_path) == f"Created world link to:{world_path}"
        if success:
            worlds_enabled_mods, mod_ids = Util.get_enabled_mod_list(world_path)
            modded_start_args = []
            for idx, mod_name in enumerate(config["modded_starter_agrs"]):
                if mod_name["mod_name"] in worlds_enabled_mods and mod_name["mod_id"] in mod_ids and mod_name["argument_enabled"]:
                    modded_start_args.append([idx, mod_name])
            if start_noita(modded_start_args):
                if config["appearance"].get("place_played_save_to_start", False):
                    config["world_paths"].remove(world_path)
                    config["world_paths"].append(world_path)
                return True

    Util.notification(3, {"type": "info", "title": "Could not open world",
                          "message": f"Failed to run selected world...\n{world_path}"})
    return False


def get_valid_noita_path(path=None, silent=False):
    if path:
        location = path
    else:
        location = tk.filedialog.askdirectory(initialdir=config["save_management"].get("default_saves_path", "."),
                                              title="Open Desired Noita Save")

    if Util.is_valid_noita_path(location):
        return location

    if location == "":
        return

    if not silent:
        Util.notification(3, {"type": "warn", "title": "Invalid path",
                              "message": f"The path:\n\"{location}\"\ndoes not lead to a \"Nolla_Games_Noita\" folder..."})


def copy_config_xml_to_save(location):
    config_file_path = config["save_management"].get("favourite_config_file", "")
    if not os.path.exists(config_file_path):
        Util.notification(3, {"type": "warn", "title": "No config found",
                              "message": "Failed to locate a config.xml in selected Noita save folder..."})
        return False
    os.mkdir(location + "/Nolla_Games_Noita")
    os.mkdir(location + "/Nolla_Games_Noita/save_shared")
    shutil.copy(config_file_path, location + "/Nolla_Games_Noita/save_shared")
    return True


def create_new_save(from_backup_path=None, initialdir=None):
    if initialdir is None:
        initialdir = config["save_management"].get("default_saves_path", ".")
    location = tk.filedialog.askdirectory(initialdir=initialdir, title="Save Location")

    if os.path.exists(location + "/Nolla_Games_Noita") or "Nolla_Games_Noita" in location:
        Util.notification(1, {"type": "warn", "title": "Already a noita save",
                              "message": "Save path cannot lead to a folder that is already used\nto save noita instance!"})
        return False
    if from_backup_path and location:
        with open(from_backup_path + "/data.json") as origin:
            name = json.load(origin)["name"]
        with open(location + "/data.json", "w") as backup_file:
            json.dump({"name": "BACKUP", "description": f"This is a backup of:\n\n - {name}\n\n - {from_backup_path}",
                       "is_backup_of": from_backup_path}, backup_file, indent=4)
        return location
    if location:
        if config["save_management"].get("copy_config_to_new_saves", False):
            copy_config_xml_to_save(location)
        add_save_path(location)
        return location
    return False


def start_new_save():
    new_save_path = create_new_save()
    if new_save_path:
        save_config()
        play_selected_world(new_save_path)


def relace_saves(source, destination):
    if Util.notification(4, {"type": "ask", "title": "REPLACE SAVE?",
                             "message": f"Are you sure you want to replace:\n{destination}\nwith:\n{source}\nPress yes to continue..."}):

        if os.path.exists(destination + "/Nolla_Games_Noita"):
            shutil.rmtree(destination + "/Nolla_Games_Noita")

        shutil.copytree(source + "/Nolla_Games_Noita", destination + "/Nolla_Games_Noita")
        frame_move_manager.reload_frame()


def rebind_backup(world_path):
    try:
        with open(world_path + "/data.json") as f:
            location_backup = json.load(f)
    except Exception as l_e:
        Util.notification(4, {"type": "warn", "title": "Faulty json",
                              "message": f"The path selected appears\nto have a faulty save file\n\n{l_e}"})
        return

    target_path = tk.filedialog.askdirectory(initialdir=config["save_management"].get("default_saves_path", "."),
                                             title="Open Desired Noita Save")
    if target_path:
        if not Util.is_valid_noita_path(target_path):
            Util.notification(4, {"type": "warn", "title": "Invalid Noita save selected",
                                  "message": f"The path selected is not a\nvalid Noita save folder...\n({target_path})"})
            return
    else:
        return
    try:
        with open(target_path + "/data.json") as f:
            target_backup = json.load(f)
    except Exception as t_e:
        Util.notification(4, {"type": "warn", "title": "Faulty json",
                              "message": f"The path selected appears\nto have a faulty save file\n\n{t_e}"})
        return

    wants_to_proceed = False
    if world_path == target_backup.get("is_backup_of", ""):
        wants_to_proceed = True
    if not wants_to_proceed:
        if Util.notification(4, {"type": "ask", "title": "Incompatible saves",
                                 "message": f"The selected save is a backup of \n{f"\"{target_backup.get("is_backup_of", "")}\"" if target_backup.get("is_backup_of", False) else "nothing"}\nand not:\n{world_path}"},
                             True):
            wants_to_proceed = True
    if wants_to_proceed:
        location_backup["backup_path"] = target_path
        target_backup["is_backup_of"] = world_path

        with open(target_path + "/data.json", "w") as f:
            json.dump(target_backup, f, indent=4)

        with open(world_path + "/data.json", "w") as f:
            json.dump(location_backup, f, indent=4)

        frame_move_manager.reload_frame()
    return


def create_backup_save(entry, paint_backup=None, start_folder=None):
    if start_folder is None:
        start_folder = config["save_management"].get("default_saves_path", "")
    if isinstance(entry, Ef.WorldBannerFrame):
        copy_from_location = entry.world_path
    else:
        copy_from_location = entry
    if copy_from_location is None:
        return
    if os.path.exists(copy_from_location + "/data.json"):
        with open(copy_from_location + "/data.json") as f:
            selected_world_data = json.load(f)
        if os.path.exists(selected_world_data.get("backup_path", "")):
            cancel_select_swapper()
            play_selected_world(selected_world_data["backup_path"])
            return
    new_save_path = create_new_save(copy_from_location, start_folder)
    if new_save_path:

        if isinstance(entry, Ef.WorldBannerFrame):
            entry.select.config(text="COPYING")
            entry.select.config(bootstyle="warning-outline")
        if paint_backup:
            paint_backup.config(text="COPYING...")
            paint_backup.config(bootstyle="warning-outline")

        Util.notification(0, {"type": "info", "title": "Copying...",
                              "message": f"Now copying save:\n{copy_from_location}\nto a new save..."})
        window.update()
        window.update_idletasks()

        if config["save_management"].get("one_to_one_backup", True):
            shutil.copytree(copy_from_location + "/Nolla_Games_Noita", new_save_path + "/Nolla_Games_Noita")
        else:
            if not os.path.exists(new_save_path + "/Nolla_Games_Noita"):
                os.mkdir(new_save_path + "/Nolla_Games_Noita")
            shutil.copytree(copy_from_location + "/Nolla_Games_Noita/save00",
                            new_save_path + "/Nolla_Games_Noita/save00")
            shutil.copytree(copy_from_location + "/Nolla_Games_Noita/save_shared",
                            new_save_path + "/Nolla_Games_Noita/save_shared")

        with open(copy_from_location + "/data.json") as f:
            selected_world_data = json.load(f)
        selected_world_data["backup_path"] = new_save_path
        with open(copy_from_location + "/data.json", "w") as f:
            json.dump(selected_world_data, f, indent=4)

        if not paint_backup:
            play_selected_world(new_save_path)
        else:
            frame_move_manager.reload_frame()
        return new_save_path
    return None


def load_in_noita_save(path=None, auto_open_new_entry=True):
    location = get_valid_noita_path(path)

    if location == f"{Util.ROAMING.replace("Roaming", "")}LocalLow".replace("\\", "/"):
        Util.notification(3, {"type": "warn", "title": "Cannot add original path", "message":
            "Cannot add the noita path directly!\nPlease move your save from the noita save location."})
        return False
    if location:
        if location not in config["world_paths"]:
            add_save_path(location)
            global scroll_depth
            scroll_depth.set(0.0 if config["save_management"]["new_save_entries_to_start"] else 1.0)
        else:
            Util.notification(1, {"type": "info", "title": "Already saved",
                                  "message": "Path provided is already registered as a save!"})
        if auto_open_new_entry:
            set_world_frame(location)
    return True


def unlist_noita_save(location, update=None):
    if location:
        config["world_paths"].remove(location)
    if update:
        update.config(text="Add Backup to homepage")
        update.config(command=lambda: list_backup_path(location, update))
        update.config(bootstyle="light-outline")
    else:
        frame_move_manager.reload_frame()
    return


def update_xml_config(world_banner):
    location = world_banner.world_path + "/Nolla_Games_Noita/save_shared/config.xml"
    if not location:
        Util.notification(3, {"type": "warn", "title": "Failed to update config path",
                              "message": "No valid noita save selected for a config file"})
        location = ""
    if os.path.exists(location):
        config["save_management"]["favourite_config_file"] = location
    else:
        Util.notification(4, {"type": "warn", "title": "Failed to update config path",
                              "message": "The provided save does not\ncontain a config.xml"})
    frame_move_manager.previous_frame()


def list_backup_path(backup_path, update=None):
    add_save_path(backup_path)
    if update:
        update.config(text="Unlist Backup")
        update.config(command=lambda: unlist_noita_save(backup_path, update))
        update.config(bootstyle="danger-outline")
    else:
        frame_move_manager.reload_frame()


def search_worlds(event, search_grid_frame, results_frame):
    search_string_raw = event.widget.get()
    count = 0
    prev_key_term = Ef.WORLD_BANNER_SEARCH_TERM
    if Util.reduced_string(search_string_raw) in ["-list", "-entries"]:
        event.widget.delete(0, "end")
        for i in search_grid_frame.items:
            if isinstance(i, Ef.WorldBannerFrame):
                count += 1 if i.is_visible else 0
        results_frame.config(
            text=f"Currently showing:\n{Util.get_formatted_int(count)} {"entry" if count == 1 else "entries"}...")
        return
    if Util.reduced_string(search_string_raw) == Ef.WORLD_BANNER_SEARCH_TERM:
        results_frame.config(text="")
        return
    Ef.update_search_term(search_string_raw)
    event.widget.delete(0, "end")
    event.widget.config(bootstyle="warning")
    window.update_idletasks()
    for i in search_grid_frame.items:
        if isinstance(i, Ef.WorldBannerFrame):
            count += i.display_banner(i.contains_keyword())
    if count == 0:
        for i in search_grid_frame.items:
            if isinstance(i, Ef.WorldBannerFrame):
                i.display_banner(True)
        results_frame.config(
            text=f"No entries found\nfor \"{search_string_raw[:7]}{"..." if len(search_string_raw) >= 8 else ""}\"")
        event.widget.config(bootstyle="secondary")
        Ef.update_search_term(prev_key_term)
        return
    event.widget.config(bootstyle="secondary")
    if Util.reduced_string(search_string_raw) == "":
        results_frame.config(text="")
    else:
        results_frame.config(
            text=f"Search for \"{search_string_raw[:7]}{"..." if len(search_string_raw) >= 8 else ""}\"\nFound {Util.get_formatted_int(count)} {"entry" if count == 1 else "entries"}:")


def look_for_unlisted_noita_saves():
    new_saves = 0
    if config["save_management"]["auto_list_unknown_saves"]:
        if os.path.exists(config["save_management"]["default_saves_path"]):
            for noita_save_name in os.listdir(config["save_management"]["default_saves_path"]):
                noita_save_path = get_valid_noita_path(
                    config["save_management"]["default_saves_path"] + "/" + noita_save_name, True)
                present = noita_save_path not in config.get("unlisted_paths", [])
                present &= noita_save_path not in config["world_paths"]
                if present:
                    if noita_save_path:
                        if os.path.exists(noita_save_path + "/data.json"):
                            with open(noita_save_path + "/data.json") as f:
                                world_data = json.load(f)
                                f.close()
                            if "backup_path" in world_data.keys() or "is_backup_of" in world_data.keys():
                                pass
                            elif load_in_noita_save(noita_save_path, False):
                                new_saves += 1
                        else:
                            if load_in_noita_save(noita_save_path, False):
                                new_saves += 1
    return new_saves


def select_noita_save_entry(command):
    global action_to_funk_map
    global set_swap_select
    global config
    global root

    if len(config["world_paths"]) == 0:
        Util.notification(2, {"type": "info", "title": "Nothing to select...", "message": "You seem to not have any\nNoita saves to select. :(\n\n(You can manually add any of your\nsaves under the \"Save management\" panel)"})
        return

    if isinstance(set_swap_select, Ef.Swapper):
        set_swap_select.re_toggle()
        set_swap_select = None

    action_to_funk_map["Play"] = lambda: None
    action_to_funk_map["Next"] = lambda: None
    action_to_funk_map["Open"] = lambda: None
    frame_move_manager.add_frame("selector frame", lambda: select_noita_save_entry(command))

    root.destroy()
    root = tb.Frame(window)

    container = tb.Frame(root)
    canvas = tk.Canvas(container)

    scroll_frame = Ef.ExtendedTkFrame(canvas, select_scroll_depth)

    Ef.ThreadedWorldsLoader(scroll_frame.scrollable_frame, config["world_paths"].copy(), scroll_frame, config,
                            play_selected_world, set_world_frame)

    footer = tb.Frame(root)
    Ef.FooterFrame(footer, [
        {"name": "RETURN", "style": "warning-outline", "command": frame_move_manager.previous_frame}
    ], pad_x=25, relief=RAISED).pack(padx=15, pady=15)
    scroll_frame.pack(fill="both", expand=True)
    canvas.pack(fill="both", expand=True)
    container.pack(fill="both", expand=True)
    footer.pack()
    root.pack(fill="both", expand=True)

    scroll_frame.update_idletasks()
    scroll_frame.canvas.yview_moveto(select_scroll_depth.get())
    run_selection(scroll_frame, command)


def reset_config(redraw=True):
    if not Util.notification(999, {"type": "ask", "title": "WARNING!",
                                   "message": "WARNING!\nYou are about to reset all settings\nback to their default values!\n\n(This does NOT include current Noita saves listed)"},
                             False):
        return False
    global config
    preserve_world_paths = config.get("world_paths", []).copy()
    config = {}
    for default_config_key, default_config_stats in Util.DEFAULT_CONFIG.items():
        config = Util.setup_config_key(config, default_config_key, default_config_stats,
                                       default_config_key == "keybind")

    config["spoiler_links"] = Util.DEFAULT_SPOILER_LINKS
    config["modded_starter_agrs"] = Util.DEFAULT_MOD_ARGS
    config["game"] = {"noita_path": Util.NOITA_PATH, "noita_runner_arg": Util.RUNNER_ARG}
    config["world_paths"] = preserve_world_paths
    config["unlisted_paths"] = []

    if redraw:
        frame_move_manager.reload_frame()
    return True


def credit_frame():
    global root
    frame_move_manager.add_frame("CREDITS", credit_frame)
    action_to_funk_map["Next"] = frame_move_manager.next_frame
    action_to_funk_map["Play"] = lambda: None
    setting_frame_padding = 45
    root.destroy()
    root = tb.Frame(window)
    panel = tb.Frame(root)
    header = tb.Frame(root)
    tb.Label(header, text="CREDITS", font=Util.tk_font("Hl")).grid(row=0, column=0, padx=20, pady=5)
    main_panel = Ef.ExtendedTkFrame(root, settings_scroll_depth, relief=GROOVE, padding=5)

    lib_panel = Ef.TitledFrame(main_panel.scrollable_frame, "Notable libraries:", padding=setting_frame_padding)
    content_libs = tb.Frame(lib_panel.content)

    tb.Label(content_libs, text="GUI library:", font=Util.tk_font("Tl")).pack(anchor="w", pady=13, padx=10)
    tb.Button(content_libs, text="https://pypi.org/project/ttkbootstrap/", style="primary-outline",
              command=lambda: Util.opening_page("https://pypi.org/project/ttkbootstrap/")).pack(pady=12, padx=10)
    tb.Separator(content_libs, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=20, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_libs, text="Image generation:", font=Util.tk_font("Tl")).pack(anchor="w", pady=13, padx=10)
    tb.Button(content_libs, text="    https://pypi.org/project/pillow/    ", style="primary-outline",
              command=lambda: Util.opening_page("https://pypi.org/project/pillow/")).pack(pady=12, padx=10)
    tb.Separator(content_libs, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=20, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_libs, text="XML file parsing:", font=Util.tk_font("Tl")).pack(anchor="w", pady=13, padx=10)
    tb.Button(content_libs, text="  https://pypi.org/project/xmltodict/  ", style="primary-outline",
              command=lambda: Util.opening_page("https://pypi.org/project/xmltodict/")).pack(pady=12, padx=10)

    content_libs.pack()
    main_panel.add_item(lib_panel)

    link_panel = Ef.TitledFrame(main_panel.scrollable_frame, "External links:", padding=setting_frame_padding)
    content_link = tb.Frame(link_panel.content)
    tb.Label(content_link, text="Maps:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    map_buttons = tb.Frame(content_link)
    tb.Button(map_buttons, text="noita-telescope", style="primary-outline", command=lambda: Util.opening_page("https://lymm37.github.io/noita-telescope/")).grid(row=0, column=0, padx=5)
    tb.Button(map_buttons, text="noitamap", style="primary-outline", command=lambda: Util.opening_page("https://noitamap.com/")).grid(row=0, column=1, padx=5)
    map_buttons.pack(pady=5, padx=10)
    tb.Separator(content_link, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=0, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_link, text="Noitool:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Button(content_link, text="          https://www.noitool.com/info          ", style="primary-outline",
              command=lambda: Util.opening_page("https://www.noitool.com/info")).pack(pady=5, padx=10)
    tb.Separator(content_link, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=0, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_link, text="Progress:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Button(content_link, text=" https://ipeterov.github.io/noita-progress/ ", style="primary-outline",
              command=lambda: Util.opening_page("https://ipeterov.github.io/noita-progress/")).pack(pady=5, padx=10)
    tb.Separator(content_link, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=0, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_link, text="Wand Simulator:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Button(content_link, text="https://tinker-with-wands-online.vercel.app/", style="primary-outline",
              command=lambda: Util.opening_page("https://tinker-with-wands-online.vercel.app/")).pack(pady=5, padx=10)
    tb.Separator(content_link, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=0, expand=True,
                                                                                             fill="x", padx=20)
    tb.Label(content_link, text="Wiki:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Label(content_link, text="   - Community documentation", font=Util.tk_font("Tm")).pack(anchor="w", pady=0,
                                                                                              padx=10)
    tb.Button(content_link, text="                https://noita.wiki.gg/                ", style="primary-outline",
              command=lambda: Util.opening_page("https://noita.wiki.gg/")).pack(pady=5, padx=10)

    content_link.pack()
    main_panel.add_item(link_panel)

    credit_panel = Ef.TitledFrame(main_panel.scrollable_frame, "Assets & more:", padding=setting_frame_padding)
    content = tb.Frame(credit_panel.content)

    tb.Label(content, text="Application logo:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Label(content, text="   - Its the Noita logo...\n     5 times over", font=Util.tk_font("Tm")).pack(anchor="w",
                                                                                                          pady=0,
                                                                                                          padx=10)
    tb.Separator(content, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=5, expand=True, fill="x",
                                                                                        padx=20)
    tb.Label(content, text="Death marker map:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Label(content, text="   - Inspired by \"Noited\"", font=Util.tk_font("Tm")).pack(anchor="w", pady=0, padx=10)
    tb.Button(content, text="      https://kamiheku.github.io/noited/      ", style="primary-outline",
              command=lambda: Util.opening_page("https://kamiheku.github.io/noited/")).pack(pady=5, padx=10)
    tb.Separator(content, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=5, expand=True, fill="x",
                                                                                        padx=20)
    tb.Label(content, text="Noita font:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Label(content, text="   - Found in noita wiki", font=Util.tk_font("Tm")).pack(anchor="w", pady=0, padx=10)
    tb.Separator(content, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=5, expand=True, fill="x",
                                                                                        padx=20)
    tb.Label(content, text="Noita \"mapcap\":", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Button(content, text="https://github.com/Dadido3/noita-mapcap", style="primary-outline",
              command=lambda: Util.opening_page("https://github.com/Dadido3/noita-mapcap")).pack(pady=5, padx=10)
    tb.Separator(content, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=5, expand=True, fill="x",
                                                                                        padx=20)
    tb.Label(content, text="OpenSeadragon:", font=Util.tk_font("Tl")).pack(anchor="w", pady=5, padx=10)
    tb.Button(content, text="      https://openseadragon.github.io/      ", style="primary-outline",
              command=lambda: Util.opening_page("https://openseadragon.github.io/")).pack(pady=5, padx=10)
    content.pack()
    main_panel.add_item(credit_panel)

    friends_panel = Ef.TitledFrame(main_panel.scrollable_frame, "Playtesters:", padding=setting_frame_padding)
    friends = tb.Frame(friends_panel.content)
    tb.Label(friends, text=" - FerociousFly", font=Util.tk_font("Tl")).pack(anchor="w", pady=35, padx=10)
    tb.Separator(friends, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=20, expand=True, fill="x", padx=20)
    tb.Label(friends, text=" - Night", font=Util.tk_font("Tl")).pack(anchor="w", pady=35, padx=10)
    tb.Separator(friends, orient='horizontal', style='info.horizontal.TSeparator').pack(pady=20, expand=True, fill="x", padx=20)
    tb.Label(friends, text=" - retr0catz:", font=Util.tk_font("Tl")).pack(anchor="w", pady=20, padx=10)
    tb.Button(friends, text="https://www.tiktok.com/@retr0_catz", style="primary-outline",
              command=lambda: Util.opening_page("https://www.tiktok.com/@retr0_catz")).pack(pady=5, padx=10)

    friends.pack()
    main_panel.add_item(friends_panel)

    Ef.FooterFrame(panel, [
        {"name": "Disclaimer: This project is not affiliated with, endorsed by, or associated with\n                 the creators of Noita or the projects, links etc. shown above."},
        {"name": "RETURN", "style": "warning-outline", "command": frame_move_manager.previous_frame}
    ], 25, relief=RAISED).pack(padx=15, pady=14)
    header.pack(anchor="n", fill="x", padx=10, pady=10)
    main_panel.pack(fill="both", expand=True, padx=5)
    panel.pack()
    root.pack(fill="both", expand=True)
    main_panel.refresh()


def create_settings_window():
    global show_advanced_settings_options
    global first_key_frame_selected
    global next_input_is_selector
    global config
    global root

    if frame_move_manager.frame_list[-1]["key"] == "selector frame":
        frame_move_manager.frame_list.pop()

    next_input_is_selector = None
    first_key_frame_selected = None

    action_to_funk_map["Open"] = lambda: Util.opening_folder(Util.CONFIG_PATH)
    action_to_funk_map["Next"] = frame_move_manager.next_frame
    action_to_funk_map["Play"] = credit_frame
    frame_move_manager.add_frame("SETTINGS", create_settings_window)

    root.destroy()
    setting_frame_padding = 45
    root = tb.Frame(window)

    panel = tb.Frame(root)

    header = tb.Frame(root)
    tb.Label(header, text="SETTINGS", font=Util.tk_font("Hl")).grid(row=0, column=0, padx=20, pady=5)
    main_panel = Ef.ExtendedTkFrame(root, settings_scroll_depth, relief=GROOVE, padding=5)

    """
    Save management
    """
    save_title = Ef.TitledFrame(main_panel.scrollable_frame, "Save management:", padding=setting_frame_padding)
    save_frame = tb.Frame(save_title.content)

    backup_specifications_frame = tb.Frame(save_frame)

    save_specifications_frame = tb.Frame(save_frame)

    def update_default_save_path():
        path = tk.filedialog.askdirectory(initialdir=config["save_management"].get("default_saves_path", "."),
                                          title="Update default save path")
        if path:
            invalid = False
            if path == f"{Util.ROAMING.replace("Roaming", "")}LocalLow".replace("\\", "/"):
                invalid = True
            if "Nolla_Games_Noita" in os.listdir(path):
                invalid = True
            if "Nolla_Games_Noita" in path:
                invalid = True

            if invalid:
                Util.notification(3, {"type": "warn", "title": "Invalid path",
                                      "message": f"The path provided cannot be used as a default save path!\n({path})"})
                return
            else:
                config["save_management"]["default_saves_path"] = path
                frame_move_manager.reload_frame()

    default_save_path = config["save_management"]["default_saves_path"]
    tb.Button(save_specifications_frame,
              text=f"{"Update" if os.path.exists(default_save_path) else "Setup"} default\n save path",
              style=f"primary{"-outline" if os.path.exists(default_save_path) else ""}",
              command=update_default_save_path).grid(row=0, column=0, padx=5, pady=5)

    tb.Label(save_specifications_frame,
             text="Load new entries\nin automatically:",
             font=Util.tk_font("Tl")).grid(padx=10, row=0, column=1)

    def update_auto_load_toggle():
        config["save_management"]["auto_list_unknown_saves"] = auto_load_new_entries.get()

    auto_load_new_entries = tb.BooleanVar(value=config["save_management"]["auto_list_unknown_saves"])
    tb.Checkbutton(save_specifications_frame,
                   variable=auto_load_new_entries,
                   command=update_auto_load_toggle).grid(row=0, column=2)

    save_specifications_frame.pack()

    def backup_one_to_one_toggle():
        config["save_management"]["one_to_one_backup"] = one_to_one_backup_toggle.get()
        backup_mode_text.config(
            text=f"Backups will copy\n{"all of the" if one_to_one_backup_toggle.get() else " important"} files:")

    one_to_one_backup_toggle = tb.BooleanVar(value=config["save_management"]["one_to_one_backup"])
    backup_mode_text = tb.Label(backup_specifications_frame,
                                text=f"Backups will copy\n{"all of the" if one_to_one_backup_toggle.get() else "important"} files:",
                                font=Util.tk_font("Tl"))
    backup_mode_text.grid(row=0, column=0)
    tb.Label(backup_specifications_frame).grid(row=0, column=1, padx=15)
    tb.Checkbutton(backup_specifications_frame,
                   style="info-round-toggle",
                   variable=one_to_one_backup_toggle,
                   command=backup_one_to_one_toggle).grid(row=0, column=2, padx=15)
    backup_specifications_frame.pack()

    def update_new_save_placement():
        config["save_management"]["new_save_entries_to_start"] = add_new_saves_to_start.get()

    def unlist_a_world_save(world):
        if Util.notification(4, {"type": "ask", "title": "Unlist a save",
                                 "message": f"You are about to unlist a noita save\nAre you shure you want to proceed?\n(Removing {world.world_path})"},
                             True):
            global config
            config["world_paths"].remove(world.world_path)
            if not config["save_management"].get("permanent_delisting", False):
                if "unlisted_paths" not in config.keys():
                    config["unlisted_paths"] = []
                config["unlisted_paths"].append(world.world_path)
        frame_move_manager.previous_frame()

    new_saves_frame = tb.Frame(save_frame)
    tb.Button(new_saves_frame,
              text="Add a new\nNoita save",
              style="success-outline",
              command=load_in_noita_save).grid(row=0, column=0, padx=5)
    tb.Button(new_saves_frame,
              text="Remove a\nNoita save",
              style="danger-outline",
              command=lambda: select_noita_save_entry(unlist_a_world_save)).grid(row=1, column=0, padx=5)

    add_new_saves_to_start = tb.BooleanVar(value=config["save_management"]["new_save_entries_to_start"])
    tb.Label(new_saves_frame,
             text="Add New Entries\nup to the top:",
             font=Util.tk_font("Tl")).grid(row=0, column=1, padx=10, pady=15)
    new_save_to_entry_start = tb.Checkbutton(new_saves_frame,
                                             style="primary-round-toggle",
                                             variable=add_new_saves_to_start,
                                             command=update_new_save_placement)
    new_save_to_entry_start.grid(row=0, column=2, padx=10)

    def update_perma_delist():
        global config
        config["save_management"]["permanent_delisting"] = perma_delist.get()
        if isinstance(main_panel.items[-1], Ef.TitledFrame):
            main_panel.items[-1].title_label.config(text="Unlisted paths:" + ("(unused)" if perma_delist.get() else ""))

    perma_delist = tb.BooleanVar(value=config["save_management"]["permanent_delisting"])
    tb.Label(new_saves_frame,
             text="PERMANENTLY\nunlist saves:",
             font=Util.tk_font("Tl")).grid(row=1, column=1, padx=10)

    perma_delist_check = tb.Checkbutton(new_saves_frame,
                                        style="danger-round-toggle",
                                        variable=perma_delist,
                                        command=lambda: update_perma_delist())
    perma_delist_check.grid(row=1, column=2, padx=10)

    new_saves_frame.pack()

    use_config_xml_for_new_saves_val = tb.BooleanVar(value=config["save_management"]["copy_config_to_new_saves"])
    config_management_frame = tb.Frame(save_frame)

    setup_xml_path = tb.Button(config_management_frame,
                               text=f"{"Update" if os.path.exists(config["save_management"]["favourite_config_file"]) else "Setup"} path to a config.xml\nto be used for new games",
                               style="info-outline",
                               command=lambda: select_noita_save_entry(update_xml_config),
                               state=("enabled" if use_config_xml_for_new_saves_val.get() else "disabled"))
    setup_xml_path.grid(row=0, column=1)

    config_management_sub_frame = tb.Frame(config_management_frame)
    tb.Label(config_management_sub_frame,
             text="Enable:",
             font=Util.tk_font("Tl")).grid(row=0, column=0, pady=5)

    def update_config_use_toggle():
        config["save_management"]["copy_config_to_new_saves"] = use_config_xml_for_new_saves_val.get()
        setup_xml_path.config(state=("enabled" if use_config_xml_for_new_saves_val.get() else "disabled"))

    use_config_xml_for_new_saves = tb.Checkbutton(config_management_sub_frame,
                                                  variable=use_config_xml_for_new_saves_val,
                                                  style="info-rounded-toggle",
                                                  command=update_config_use_toggle)
    use_config_xml_for_new_saves.grid(row=1, column=0)

    config_management_sub_frame.grid(row=0, column=0, padx=30, pady=5)
    config_management_frame.pack()

    save_frame.pack()
    main_panel.add_item(save_title)

    """
    Appearance
    """

    main_appearance_title = Ef.TitledFrame(main_panel.scrollable_frame, "Appearance:", padding=setting_frame_padding)
    main_appearance_frame = tb.Frame(main_appearance_title.content)

    theme_map = Util.get_themes()

    def update_theme(theme):
        try:
            selected_theme = theme_map[theme]
            if theme == "custom":
                if not Util.notification(5, {"type": "ask", "title": "Your style!",
                                             "message": "This font is for you to modify!\n\n- go to the config folder\n- go to the styles folder\n  and make a copy of any of the .json styles\n- rename the new .json to your styles name\n  and modify the color values."}):
                    return
            _custom_theme = ThemeDefinition(selected_theme["name"], selected_theme["colors"])
            global style
            style = tb.Style()
            if _custom_theme.name not in style.theme_names():
                style.register_theme(_custom_theme)
            style.theme_use(_custom_theme.name)
            config["appearance"]["theme"] = theme

        except Exception as e:
            Util.notification(3, {"type": "warn", "title": "", "message": f"Failed to load {theme}...\n{e}"})

    theme_selection_frame = tb.Frame(main_appearance_frame)
    tb.Label(theme_selection_frame, text="Change window \ncolors:", font=Util.tk_font("Tl")).grid(row=0, column=0)
    menu_button = tb.Menubutton(theme_selection_frame, text="Select Window Theme", style="success-outline")

    menu = tk.Menu(menu_button, tearoff=0)
    menu.add_command(label="                 ", state="disabled", font=Util.tk_font("Tm"))
    for item in theme_map.keys():
        menu.add_command(label="- " + item, font=Util.tk_font("Tl"), command=lambda value=item: update_theme(value))
    menu.add_command(label="                 ", state="disabled", font=Util.tk_font("Tm"))

    menu_button["menu"] = menu
    menu_button.grid(row=0, column=1, pady=5)

    theme_selection_frame.pack(pady=10)

    wand_export_mode = tb.Frame(main_appearance_frame)

    boolean_one_to_one_wand_export = tb.BooleanVar(value=config["appearance"].get("accurate_wand_export", True))

    def toggle_one_to_one_wand():
        config["appearance"]["accurate_wand_export"] = boolean_one_to_one_wand_export.get()
        Ef.PERFECT_WAND_PRINT = boolean_one_to_one_wand_export.get()
        one_to_one_wand_label.config(
            text=f"Export wand pictures\n({"DETAILED" if boolean_one_to_one_wand_export.get() else "BASIC"})")

    one_to_one_wand_label = tb.Label(wand_export_mode,
                                     text=f"Export wand pictures\n({"DETAILED" if boolean_one_to_one_wand_export.get() else "BASIC"})",
                                     font=Util.tk_font("Tl"))
    one_to_one_wand_label.grid(row=0, column=0, padx=20)
    tb.Checkbutton(wand_export_mode, style="info-rounded-toggle", variable=boolean_one_to_one_wand_export,
                   command=toggle_one_to_one_wand).grid(row=0, column=1, padx=20)
    wand_export_mode.pack(pady=4)

    use_noita_font_frame = tb.Frame(main_appearance_frame)

    boolean_use_noita_font = tb.BooleanVar(value=config["appearance"].get("use_noita_font", True))

    def toggle_noita_font():
        config["appearance"]["use_noita_font"] = boolean_use_noita_font.get()
        Util.USE_NOITA_FONT = boolean_use_noita_font.get()
        noita_font_label.config(text=f"Wand export font: {"Noita" if boolean_use_noita_font.get() else "Basic"}")

    noita_font_label = tb.Label(use_noita_font_frame,
                                text=f"Wand export font: {"Noita" if boolean_use_noita_font.get() else "Basic"}",
                                font=Util.tk_font("Tl"))
    noita_font_label.grid(row=0, column=0, padx=5)
    tb.Checkbutton(use_noita_font_frame, style="primary-rounded-toggle", variable=boolean_use_noita_font,
                   command=toggle_noita_font).grid(row=0, column=1, padx=5)
    use_noita_font_frame.pack(pady=4)

    save_to_start_frame = tb.Frame(main_appearance_frame)

    boolean_played_save_to_start = tb.BooleanVar(value=config["appearance"].get("place_played_save_to_start", False))

    def toggle_move_played_save():
        config["appearance"]["place_played_save_to_start"] = boolean_played_save_to_start.get()

    tb.Label(save_to_start_frame, text="Move recently played\nsaves up to the top:", font=Util.tk_font("Tl")).grid(
        row=0, column=0, padx=20)
    tb.Checkbutton(save_to_start_frame, style="success-rounded-toggle", variable=boolean_played_save_to_start,
                   command=toggle_move_played_save).grid(row=0, column=1, padx=20)
    save_to_start_frame.pack(pady=4)

    def update_notification_threshold(event):
        config["appearance"]["notification_threshold"] = notification_threshold_val.get()
        Util.NOTIFICATION_THRESHOLD = notification_threshold_val.get()
        notification_threshold_label.config(
            text=f"Block the less important\nnotifications (limit strength={notification_threshold_val.get()}):")

    notification_threshold_val = tb.IntVar(value=config["appearance"].get("notification_threshold"))

    notification_threshold_label = tb.Label(main_appearance_frame,
                                            text=f"Block the less important\nnotifications (limit strength={notification_threshold_val.get()}):",
                                            font=Util.tk_font("Tl"))
    notification_threshold_label.pack(pady=10)
    tb.Scale(main_appearance_frame, style="info", variable=notification_threshold_val,
             command=update_notification_threshold, from_=0, to=5, length=320).pack()

    main_appearance_frame.pack(pady=10)
    main_panel.add_item(main_appearance_title)

    """
    Save frames FRAME
    """

    def update_config(key):
        if key == "ENTRY_Default":
            k_v_vars[key].set(True)
            return
        config["enabled_save_displays"][key] = k_v_vars[key].get()

        if key == "Latest stats":
            if isinstance(main_panel.items[-2], Ef.TitledFrame):
                main_panel.items[-2].title_label.config(
                    text="Xml Stats shown:" + ("" if config["enabled_save_displays"]["Latest stats"] else "(unused)"))
        if key == "ENTRY_Spoiler sites":
            if isinstance(main_panel.items[-4], Ef.TitledFrame):
                main_panel.items[-4].title_label.config(text="Spoiler links:" + (
                    "" if config["enabled_save_displays"]["ENTRY_Spoiler sites"] else "(unused)"))

    def toggle_by_click(e, label_key):
        label_key.config(bootstyle="primary-inverse")
        key = label_key.cget("text")
        global first_key_frame_selected
        if first_key_frame_selected:
            if key == first_key_frame_selected:
                first_key_frame_selected = None
                return
            config["enabled_save_displays"] = Util.swap_dict_keys(config["enabled_save_displays"],
                                                                  first_key_frame_selected, key)
            first_key_frame_selected = None
            frame_move_manager.reload_frame()
        else:
            first_key_frame_selected = key

    def bind_lab_enter(e, key):
        key.config(bootstyle="secondary-inverse")

    def bind_lab_leave(e, key):
        if not key.cget("text") == first_key_frame_selected:
            key.config(bootstyle="dark-inverse")
        else:
            key.config(bootstyle="primary-inverse")

    stat_frame_title = Ef.TitledFrame(main_panel.scrollable_frame, "Stats Frames:", padding=setting_frame_padding)
    world_stat_frames = tb.Frame(stat_frame_title.content)
    sub_frame = tb.Frame(world_stat_frames)
    i = 1
    k_v_vars = {}
    frame_labels = []
    default_entry = tb.Frame(sub_frame)

    k_v_vars["ENTRY_Default"] = tb.BooleanVar()
    k_v_vars["ENTRY_Default"].set(True)
    tb.Checkbutton(default_entry, style="success-round-toggle", variable=k_v_vars["ENTRY_Default"],
                   command=lambda key="ENTRY_Default": update_config(key)).grid(row=0, column=0, sticky="w")
    text_label = tb.Label(default_entry, text="Default", font=Util.tk_font("Tl"))
    text_label.grid(row=0, column=1, sticky="nw")

    default_entry.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    idx_frame = 0
    for k, v in config["enabled_save_displays"].items():
        if not k == "force_first_frames":
            frame_entry = tb.Frame(sub_frame)
            k_v_vars[k] = tb.BooleanVar()
            k_v_vars[k].set(v)
            check = tb.Checkbutton(frame_entry, style="success-round-toggle", variable=k_v_vars[k],
                                   command=lambda key=k: update_config(key))

            check.grid(row=0, column=0, sticky="w")
            text_label = tb.Label(frame_entry, text=k.replace("ENTRY_", ""), font=Util.tk_font("Tl"),
                                  style="" if k.startswith("ENTRY_") else "dark-inverse")
            if not k.startswith("ENTRY_"):
                check.config(bootstyle=("success" if idx_frame < config["enabled_save_displays"][
                    "force_first_frames"] else "warning") + "-round-toggle")
                idx_frame += 1
                text_label.bind("<Button-1>", lambda e, key=text_label: toggle_by_click(e, key))
                text_label.bind("<Enter>", lambda e, key=text_label: bind_lab_enter(e, key))
                text_label.bind("<Leave>", lambda e, key=text_label: bind_lab_leave(e, key))
                frame_labels.append(check)
            text_label.grid(row=0, column=1, sticky="nw")

            frame_entry.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")
            i += 1
    sub_frame.pack(pady=8)
    int_var = tb.IntVar(value=config["enabled_save_displays"]["force_first_frames"])
    force_label = tb.Label(world_stat_frames,
                           text=f"Force-render the top {config["enabled_save_displays"]["force_first_frames"]} frames:",
                           font=Util.tk_font("Tl"))

    def update_frame_forcer(event):
        force_amount = int_var.get()
        force_label.config(text=f"Force-render the top {force_amount} frames:")
        for x in range(len(frame_labels)):
            if x < force_amount:
                frame_labels[x].config(bootstyle="success-round-toggle")
            else:
                frame_labels[x].config(bootstyle="warning-round-toggle")
        config["enabled_save_displays"]["force_first_frames"] = force_amount
        Ef.FORCE_FRAMES = force_amount

    scaly = tb.Scale(world_stat_frames, from_=0, to=len(frame_labels), style="danger", orient="horizontal",
                     variable=int_var, length=350, command=update_frame_forcer)
    force_label.pack(pady=10)
    scaly.pack(pady=5)
    world_stat_frames.pack()
    main_panel.add_item(stat_frame_title)

    """
    Keybindings
    """
    keybind_title = Ef.TitledFrame(main_panel.scrollable_frame, "Keybindings:", padding=setting_frame_padding)
    keybind_frame = tb.Frame(keybind_title.content)

    index = 0
    k_v_vars_binds = {}
    for v, k in sorted({value: key for key, value in config["keybind"].items()}.items()):
        k_v_vars_binds[k] = tb.StringVar()
        k_v_vars_binds[k].set(v)
        sub_frame = tb.Frame(keybind_frame)
        tb.Label(sub_frame, text=k_v_vars_binds[k].get() + ":" + (" " * (5 - len(k_v_vars_binds[k].get()))),
                 font=Util.tk_font("Tl")).grid(row=0, column=0, sticky="nw")
        center_key_bind_padding = " " * ((18 - len(k)) // 2)
        key_display = tb.Label(sub_frame, text=center_key_bind_padding + k + (
            " " if (18 - len(k)) % 2 else "") + center_key_bind_padding, style="primary-inverse",
                               font=Util.tk_font("Tl"))

        def update_key(e, key, key_label):
            global next_input_is_selector
            key_label.config(text="    PRESS A KEY   ")
            key_label.config(bootstyle="warning-inverse")
            next_input_is_selector = key

        def bind_enter(e, key):
            if not next_input_is_selector:
                key.config(bootstyle="info-inverse")

        def bind_leave(e, key):
            if not next_input_is_selector:
                key.config(bootstyle="primary-inverse")

        key_display.bind("<Button-1>",
                         lambda e, key=k_v_vars_binds[k].get(), key_label=key_display: update_key(e, key, key_label))
        key_display.bind("<Enter>", lambda e, key=key_display: bind_enter(e, key))
        key_display.bind("<Leave>", lambda e, key=key_display: bind_leave(e, key))
        key_display.grid(row=0, column=1, sticky="nw")
        sub_frame.grid(row=index, column=0, padx=7, pady=12, sticky="nsew")
        index += 1
    keybind_frame.pack(padx=30, pady=25)
    main_panel.add_item(keybind_title)

    """
    Scroll FRAME
    """
    scroll_title = Ef.TitledFrame(main_panel.scrollable_frame, "Scroll config:", padding=setting_frame_padding)
    scroll_frames_setting = tb.Frame(scroll_title.content)
    Ef.update_frame_config_variables(config)

    inverted_check_toggle = tb.BooleanVar()
    inverted_check_toggle.set(config["scroll_frame_settings"]["scroll_inverted"])
    autoscroll_check_toggle = tb.BooleanVar()
    autoscroll_check_toggle.set(config["scroll_frame_settings"]["auto_scroll"])

    def update_scroll(event, key, val):
        if key == "scroll_inverted":
            val = val.get()
            inverted_check_toggle.set(val)
            config["scroll_frame_settings"]["scroll_inverted"] = val
            Ef.SCROLL_INVERTED = val
        if key == "scroll_intensity":
            config["scroll_frame_settings"]["scroll_intensity"] = val.get()
            scroll_intense_label.config(text=f"Scroll intensity: {config["scroll_frame_settings"]["scroll_intensity"]}")
            Ef.SCROLL_INTENSITY = val.get()
        if key == "auto_scroll":
            val = val.get()
            autoscroll_check_toggle.set(val)
            config["scroll_frame_settings"]["auto_scroll"] = val
            Ef.AUTO_SCROLL = val
            visibility_scale.config(bootstyle="info" if val else "secondary")
        if key == "scroll_frame_visibility":
            val = val.get()
            config["scroll_frame_settings"]["scroll_frame_visibility"] = val / 100
            scroll_visibility_label.config(
                text=f"Scroll the frame when \nits {" " * (3 - len(str(val)))}{val}% visible:")
            Ef.SCROLL_FRAME_VISIBILITY = val / 100

    split_frame = tb.Frame(scroll_frames_setting)
    tb.Label(split_frame, text=" Inverted scrolling:", font=Util.tk_font("Tl")).grid(row=0, column=0)
    inv_check = tb.Checkbutton(split_frame, style="primary", variable=inverted_check_toggle)
    inv_check.config(
        command=lambda scroll_k="scroll_inverted", scroll_v=inverted_check_toggle: update_scroll("", scroll_k,
                                                                                                 scroll_v))
    inv_check.grid(row=0, column=1, padx=30)
    split_frame.pack(pady=15)

    split_frame = tb.Frame(scroll_frames_setting)
    tb.Label(split_frame, text="sub-frame-scrolling:", font=Util.tk_font("Tl")).grid(row=0, column=0)
    inv_check = tb.Checkbutton(split_frame, style="info", variable=autoscroll_check_toggle)
    inv_check.config(
        command=lambda scroll_k="auto_scroll", scroll_v=autoscroll_check_toggle: update_scroll("", scroll_k, scroll_v))
    inv_check.grid(row=0, column=1, padx=20)
    split_frame.pack(pady=10)

    tb.Label(scroll_frames_setting).pack(pady=3)
    scroll_intense_label = tb.Label(scroll_frames_setting,
                                    text=f"Scroll intensity: {config["scroll_frame_settings"]["scroll_intensity"]}",
                                    font=Util.tk_font("Tl"))
    scroll_intense_label.pack()
    scroll_intense_slicer = tb.IntVar(value=config["scroll_frame_settings"]["scroll_intensity"])
    intensity_scale = tb.Scale(scroll_frames_setting, variable=scroll_intense_slicer, from_=1, to=400, style="primary",
                               orient="horizontal", length=250, command=lambda e, scroll_k="scroll_intensity",
                                                                               scroll_v=scroll_intense_slicer: update_scroll(
            e, scroll_k, scroll_v))
    intensity_scale.pack()

    tb.Label(scroll_frames_setting).pack(pady=10)
    scroll_val = int(config["scroll_frame_settings"]["scroll_frame_visibility"] * 100)
    scroll_visibility_label = tb.Label(scroll_frames_setting,
                                       text=f"Scroll the frame when \nits {" " * (3 - len(str(scroll_val)))}{scroll_val}% visible:",
                                       font=Util.tk_font("Tl"))
    scroll_visibility_label.pack()
    scroll_intense_slicer = tb.IntVar(value=scroll_val)
    visibility_scale = tb.Scale(scroll_frames_setting, variable=scroll_intense_slicer, from_=0, to=100,
                                style="info" if config["scroll_frame_settings"]["auto_scroll"] else "secondary",
                                orient="horizontal", length=250, command=lambda e, scroll_k="scroll_frame_visibility",
                                                                                scroll_v=scroll_intense_slicer: update_scroll(
            e, scroll_k, scroll_v))
    visibility_scale.pack(padx=25, pady=10)

    scroll_frames_setting.pack()
    main_panel.add_item(scroll_title)

    advanced_options = Ef.TitledFrame(main_panel.scrollable_frame, "Application modifications:",
                                      extras="The following configs/displays  \nshould not need tampering!\n\n(unless you want to)")

    def show_advanced_frames():
        global show_advanced_settings_options
        show_advanced_settings_options = True
        spoiler_links_frame = Ef.ShowLinkEntries(main_panel.scrollable_frame, config, frame_move_manager.reload_frame)
        spoiler_links_frame.title_label.config(
            text="Spoiler links:" + ("" if config["enabled_save_displays"]["ENTRY_Spoiler sites"] else "(unused)"))
        main_panel.replace_idx(spoiler_links_frame, -4, False)
        main_panel.replace_idx(Ef.ModifyModdedStarterArgs(main_panel.scrollable_frame, config), -3, False)
        xml_stats_grabber_frame = Ef.ModifyXMLDataGrabber(main_panel.scrollable_frame, config)
        xml_stats_grabber_frame.title_label.config(
            text="Xml Stats shown:" + ("" if config["enabled_save_displays"]["Latest stats"] else "(unused)"))
        main_panel.replace_idx(xml_stats_grabber_frame, -2, False)
        unlisted_paths_frame = Ef.BasicPathEntry(main_panel.scrollable_frame, config.get("unlisted_paths", []),
                                                 set_world_frame, config, frame_move_manager.reload_frame)
        unlisted_paths_frame.title_label.config(text="Unlisted paths:" + ("(unused)" if perma_delist.get() else ""))
        main_panel.replace_idx(unlisted_paths_frame, -1, True)
        advanced_button.config(command=hide_advanced_frames)
        advanced_button.config(text="HIDE EXTENDED OPTIONS")
        advanced_button.config(bootstyle="primary")

    def hide_advanced_frames():
        global show_advanced_settings_options
        show_advanced_settings_options = False
        main_panel.replace_idx(tb.Frame(main_panel.scrollable_frame), -4, False)
        main_panel.replace_idx(tb.Frame(main_panel.scrollable_frame), -3, False)
        main_panel.replace_idx(tb.Frame(main_panel.scrollable_frame), -2, False)
        main_panel.replace_idx(tb.Frame(main_panel.scrollable_frame), -1, True)
        advanced_button.config(command=show_advanced_frames)
        advanced_button.config(text="SHOW EXTENDED OPTIONS")
        advanced_button.config(bootstyle="warning")

    if not show_advanced_settings_options:
        advanced_button = tb.Button(advanced_options, text="SHOW EXTENDED OPTIONS", style="warning",
                                    command=show_advanced_frames)
        advanced_button.pack(anchor="n", expand=True, fill="x", padx=20, pady=5)
    else:
        advanced_button = tb.Button(advanced_options, text="HIDE EXTENDED OPTIONS", style="primary",
                                    command=hide_advanced_frames)
        advanced_button.pack(anchor="n", expand=True, fill="x", padx=20, pady=5)
    main_panel.add_item(advanced_options)

    """
    spoiler links frame
    """

    main_panel.add_item(tb.Frame(main_panel.scrollable_frame))

    """
    MODDED STARTER ARGS
    """

    main_panel.add_item(tb.Frame(main_panel.scrollable_frame))

    """
    STARTS GRABBER MODIFIER
    """

    main_panel.add_item(tb.Frame(main_panel.scrollable_frame))

    """
    Unlisted paths display
    """
    main_panel.add_item(tb.Frame(main_panel.scrollable_frame))

    if show_advanced_settings_options:
        show_advanced_frames()
    """
    Footer
    """

    enw = None
    if not os.path.exists(Util.CONFIG_PATH + "/assets/death_maps/noita_map/capture_files"):
        enw = {"name": "Improve DeathMarker map", "style": "success-outline", "command": lambda: Util.opening_page(
            "https://drive.google.com/drive/folders/17ZEoLUdrBhiLyCSF-MiLpOwa4K4B0MVK?usp=sharing")}
    Ef.FooterFrame(panel, [
        enw,
        {"name": "CREDITS", "style": "info-outline", "command": credit_frame},
        {"name": "Open config folder", "style": "primary-outline",
         "command": lambda: Util.opening_folder(Util.CONFIG_PATH)},
        {"name": "RESET TO DEFAULT", "style": "danger-outline", "command": reset_config},
        {"name": "RETURN", "style": "warning-outline", "command": frame_move_manager.previous_frame}
    ], pad_x=5 if enw else 25, relief=RAISED).pack(padx=15, pady=14)

    header.pack(anchor="n", fill="x", padx=10, pady=10)
    main_panel.pack(fill="both", expand=True, padx=5)
    panel.pack()
    root.pack(fill="both", expand=True)
    main_panel.update_idletasks()
    main_panel.canvas.yview_moveto(settings_scroll_depth.get())


def set_world_frame(world_path):
    world_path = world_path.replace("\\", "/")
    try:
        with open(world_path + "/data.json") as f:
            selected_world_data = json.load(f)
    except Exception as e:
        selected_world_data = {"name": "", "description": ""}

    global action_to_funk_map
    global set_swap_select
    global config

    if isinstance(set_swap_select, Ef.Swapper):
        set_swap_select.re_toggle()
        set_swap_select = None
    action_to_funk_map["Play"] = lambda: play_selected_world(world_path)

    action_to_funk_map["Open"] = lambda: Util.opening_folder(world_path)
    frame_move_manager.add_frame(world_path, lambda: set_world_frame(world_path))

    if not os.path.exists(world_path):
        Util.notification(2, {"type": "warn", "title": "Save doesnt exist",
                              "message": f"Failed to load:\n{world_path}\n(Path does not exist!)"})
        try:
            config["world_paths"].remove(world_path)
        except:
            pass
        create_main_window()
        return

    if not os.listdir(world_path):
        return
    global root
    selected_world_data["name"] = selected_world_data.get("name", "")
    selected_world_data["description"] = selected_world_data.get("description", "")

    world_scroll_var = tb.DoubleVar(value=0.0)

    root.destroy()
    root = tb.Frame(window)

    panel = tb.Frame(root)

    def limit_name_size(*args):
        value = name_var.get()
        if len(value) > 30:
            name_var.set(value[:30])

    name_var = tb.StringVar()
    name_var.trace_add("write", limit_name_size)

    lb_name = tb.Entry(panel, width=31, textvariable=name_var, font=Util.tk_font("Hl"))
    lb_name.insert(tk.END, selected_world_data["name"])
    lb_name.pack(padx=15, pady=15, anchor="nw")

    scrollable_frame = Ef.ExtendedTkFrame(panel, world_scroll_var)
    top_info = Ef.ScrollSetElement(scrollable_frame.scrollable_frame, relief=GROOVE, padding=5)
    value_values = tb.Frame(top_info)
    tb.Label(value_values, text="   Short\nDescription", font=Util.tk_font("Tl")).grid(row=0, column=0)
    tb.Label(value_values, text="Mods", font=Util.tk_font("Tl")).grid(row=1, column=0)
    tb.Label(value_values, text="Spoiler\n sites", font=Util.tk_font("Tl")).grid(row=2, column=0)

    lb_desc = Ef.WorldSaver(value_values, world_path, name_var, selected_world_data, frame_size=[510, 110])
    lb_desc.text.insert(tk.END, selected_world_data["description"])
    lb_desc.text.config(font=Util.tk_font("Ts"))
    lb_desc.text.config(width=65)
    lb_desc.set_max_height(7)
    top_info.set_focus_widget(lb_desc)
    top_info.set_scroll(lb_desc.canvas)
    lb_desc.grid(row=0, column=1, pady=5, padx=5)

    mods = Util.get_mods(world_path)

    mod_panel = tb.Frame(value_values)
    if mods:
        menu_button = tb.Menubutton(mod_panel, text="Show this runs enabled mods", style="info")
        menu_button.pack()

        def disable_click(e):
            global mouse_btn_1_clicked_once
            mouse_btn_1_clicked_once = False

        menu_button.bind("<Button-1>", disable_click)
        menu = tk.Menu(menu_button, tearoff=0)
        menu.add_command(label=" "*43, state="disabled", font=Util.tk_font("Tm"))
        for item in mods:

            title_lines = Util.array_line_text(item["name"] + (":" if item["desc"] else ""), 33)
            menu.add_command(label="- " + title_lines[0], font=Util.tk_font("Tl"), command=lambda path=item["link"]: Util.opening_page(path))
            if len(title_lines) > 1:
                for title_line in title_lines[1:]:
                    menu.add_command(label="  "+title_line, font=Util.tk_font("Tl"), command=lambda path=item["link"]: Util.opening_page(path))
                menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

            for line in Util.array_line_text(item["desc"], 40):
                menu.add_command(label="   " + line, font=Util.tk_font("Tm"), command=lambda path=item["path"]: Util.opening_folder(path))
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        menu_button["menu"] = menu
        mod_panel.grid(row=1, column=1, pady=10, padx=0)
    elif Util.noita_world_was_modded(world_path):
        menu_button = tb.Menubutton(mod_panel, text="Illegitimate run", style="warning-outline")
        menu_button.pack()
        menu = tk.Menu(menu_button, tearoff=0)
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
        menu.add_command(label="The current run had some", font=Util.tk_font("Tl"), command=lambda link="https://noita.wiki.gg/wiki/Mod_Restrictions": Util.opening_page(link))
        menu.add_command(label="mod enabled on it", font=Util.tk_font("Tl"), command=lambda link="https://noita.wiki.gg/wiki/Mod_Restrictions": Util.opening_page(link))
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
        menu_button["menu"] = menu
        mod_panel.grid(row=1, column=1, pady=15, padx=0)
    else:
        menu_button = tb.Menubutton(mod_panel, text="Un-modded run", style="info-outline")
        menu_button.config(state="disabled")
        menu_button.pack()
        menu = tk.Menu(menu_button, tearoff=0)
        menu_button["menu"] = menu
        mod_panel.grid(row=1, column=1, pady=15, padx=0)

    world_data_grabbed = None
    stats_key_list = []
    if config["enabled_save_displays"]["ENTRY_Spoiler sites"] or config["enabled_save_displays"]["Latest stats"]:

        xml_conf_copy = {}
        for k, v in config["xml_stats_grab"].items():
            xml_conf_copy[k] = v.copy()
            stats_key_list.append(k)
        world_data_grabbed = Util.fill_all_xml_args(world_path, xml_conf_copy, False)

    if config["enabled_save_displays"]["ENTRY_Spoiler sites"]:

        spoiler_button_list = []
        for link_name, link_data in config["spoiler_links"].items():
            if "disabled" not in config["spoiler_links"][link_name].keys():
                base_url = link_data["link"]

                def open_base_link(link):
                    Util.opening_page(link)

                is_fancy_link = False
                for available_keys in stats_key_list:
                    if "{{" + available_keys + "}}" in base_url:
                        is_fancy_link = True
                        break
                available_fancy_link = False
                for keyword, xml_data in world_data_grabbed.items():
                    if "{{" + keyword + "}}" in base_url:
                        if xml_data:
                            available_fancy_link = True
                            if not isinstance(xml_data, str):
                                xml_data = str(xml_data)
                            base_url = base_url.replace("{{" + keyword + "}}", xml_data)
                        else:
                            available_fancy_link = False
                if is_fancy_link:
                    if available_fancy_link and os.path.exists(world_path+"/Nolla_Games_Noita/save00/player.xml"):
                        spoiler_button_list.append({"name": link_name[:20], "style": link_data["color"],
                                                    "command": lambda link=base_url: open_base_link(link)})
                else:
                    spoiler_button_list.append({"name": link_name, "style": link_data["color"],
                                                "command": lambda link=base_url: open_base_link(link)})

        for xml_key, xml_path in config["xml_stats_grab"].items():
            if "HIDDEN_" in xml_path and xml_key in world_data_grabbed:
                world_data_grabbed.pop(xml_key)

        a_lot_of_darn_buttons = False

        if len(spoiler_button_list) >= 7:
            a_lot_of_darn_buttons = True
        if len(spoiler_button_list) == 0:
            a_lot_of_darn_buttons = True
        if a_lot_of_darn_buttons:
            link_panel = tb.Frame(value_values)
            if len(spoiler_button_list) == 0:
                menu_button = tb.Menubutton(link_panel, text="No Links", style="primary-outline")
                menu_button.config(state="disabled")
            else:
                menu_button = tb.Menubutton(link_panel, text="Show Links", style="primary-outline")
                menu_button.config(state="enabled")
            menu_button.pack()
            menu = tk.Menu(menu_button, tearoff=0)
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
            for item in spoiler_button_list:
                menu.add_command(label="- " + item["name"], font=Util.tk_font("Tl"), command=item["command"])

            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
            menu_button["menu"] = menu
            link_panel.grid(row=2, column=1)
        else:
            Ef.FooterFrame(value_values, spoiler_button_list, pad_x=10, pad_y=5, max_elements_per_row=3,
                           relief=RAISED).grid(row=2, column=1)
    else:
        tb.Frame(value_values, width=10, height=60, padding=5).grid(row=2, column=1, padx=5, pady=5)
    value_values.pack(pady=2)
    div_frame = tb.Frame(top_info)
    if config["enabled_save_displays"]["ENTRY_Mina model"]:
        Ef.MinaMoment(div_frame, world_path, relief=GROOVE, padding=2, bootstyle="secondary").grid(row=0, column=0)

    else:
        tb.Frame(div_frame, width=100, height=200).grid(row=0, column=0)
    backup_frame = tb.Frame(div_frame)

    backup_frame.grid_rowconfigure(0, weight=1)
    backup_frame.grid_rowconfigure(1, weight=1)
    backup_frame.grid_columnconfigure(0, weight=1)
    backup_frame.grid_columnconfigure(1, weight=1)

    backup_fallback = True
    about_backup = False
    about_original = False
    backup_age_text = "\n\n"
    open_backup_folder = config["save_management"].get("default_saves_path", "")
    relist_backup = False
    if "backup_path" in selected_world_data.keys():
        if os.path.exists(selected_world_data["backup_path"]):
            str_time = ""
            game_float_age = Util.get_world_playtime(world_path)
            back_float_age = Util.get_world_playtime(selected_world_data["backup_path"])
            if game_float_age and back_float_age:
                if back_float_age["date"] == game_float_age["date"]:
                    play_time_dif = game_float_age["time"] - back_float_age["time"]
                    if play_time_dif == 0:
                        str_time = "This save and\n  its Backup are\n  identical..."
                    else:
                        str_time = f"This backup has\n  {Util.get_str_time(abs(play_time_dif))}\n  {"more" if play_time_dif < 0 else "less"} playtime."
                else:
                    int_date_g = game_float_age["date"].split("-")
                    int_date_b = back_float_age["date"].split("-")

                    day_diff = int(int_date_g[0]) - int(int_date_b[0])
                    if day_diff == 0:
                        day_diff = int(int_date_g[1]) - int(int_date_b[1])
                    str_time = f"This backup has\n  {["a newer", "the same", "an older"][max(-1, min(day_diff, 1)) + 1]} session...\n  {Util.get_str_time(back_float_age["time"])}\n  of playtime"
            if not game_float_age and back_float_age:
                str_time = "Backup run is:\n  " + Util.get_str_time(back_float_age["time"]) + "\n  old..."
            if game_float_age and not back_float_age:
                str_time = "Backup has no\n  ongoing run..."
            backup_age_text += "  " + str_time
        else:
            open_backup_folder = Util.get_valid_folder(selected_world_data["backup_path"])
            backup_age_text += "  Backup listed\n  doesnt exist\n  anymore..."
            relist_backup = True
    tb.Label(backup_frame, text=f"Backup Management:{backup_age_text}",
             font=Util.tk_font(Util.FONT_TYPE["Tm"] + 1)).grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
    if "backup_path" in selected_world_data.keys():
        if os.path.exists(selected_world_data["backup_path"]):
            content = os.listdir(selected_world_data["backup_path"])
            if "Nolla_Games_Noita" in content and "data.json" in content:
                about_backup = True
                backup_fallback = False
    if backup_fallback:
        if relist_backup:
            relist_button = tb.Button(backup_frame,
                                      text="Bind a Noita-save path\nto this save entry to\nbe its new backup",
                                      style="success-outline", command=lambda w_p=world_path: rebind_backup(w_p))
            relist_button.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        the_self = tb.Button(backup_frame, text="Create Backup", style="info-outline")
        the_self.config(command=lambda: create_backup_save(world_path, the_self, start_folder=open_backup_folder))
        the_self.grid(row=1, column=0, sticky="nsew", padx=5, pady=10)
    if "is_backup_of" in selected_world_data.keys():
        about_original = True

    mid_grid = tb.Frame(backup_frame)

    mid_grid.grid_rowconfigure(0, weight=1)
    mid_grid.grid_rowconfigure(1, weight=1)
    mid_grid.grid_columnconfigure(0, weight=1)
    mid_grid.grid_columnconfigure(1, weight=1)
    if about_backup and about_original:
        tb.Button(mid_grid, text="Go to Original", style="primary-outline",
                  command=lambda: set_world_frame(selected_world_data["is_backup_of"])).grid(row=0, column=0,
                                                                                             sticky="nsew")
        tb.Button(mid_grid, text="Go to Backup", style="secondary-outline",
                  command=lambda: set_world_frame(selected_world_data["backup_path"])).grid(row=0, column=1,
                                                                                            sticky="nsew")
        tb.Button(mid_grid, text="Update with\nthe Original", style="info-outline",
                  command=lambda: relace_saves(selected_world_data["is_backup_of"], world_path)).grid(row=1, column=0,
                                                                                                      pady=10,
                                                                                                      sticky="nsew")
        tb.Button(mid_grid, text="Restore from\nthe Backup", style="warning-outline",
                  command=lambda: relace_saves(selected_world_data["backup_path"], world_path)).grid(row=1, column=1,
                                                                                                     pady=10,
                                                                                                     sticky="nsew")
    else:
        if about_original:
            tb.Button(mid_grid, text="Go to Original", style="primary-outline",
                      command=lambda: set_world_frame(selected_world_data["is_backup_of"])).grid(row=0, column=0,
                                                                                                 sticky="nsew")
            tb.Button(mid_grid, text="Update with\nthe Original", style="info-outline",
                      command=lambda: relace_saves(selected_world_data["is_backup_of"], world_path)).grid(row=1,
                                                                                                          column=0,
                                                                                                          sticky="nsew",
                                                                                                          pady=10)
        if about_backup:
            tb.Button(mid_grid, text="Go to Backup", style="secondary-outline",
                      command=lambda: set_world_frame(selected_world_data["backup_path"])).grid(row=0, column=0,
                                                                                                sticky="nsew")
            tb.Button(mid_grid, text="Restore from\nthe Backup", style="warning-outline",
                      command=lambda: relace_saves(selected_world_data["backup_path"], world_path)).grid(row=1,
                                                                                                         column=0,
                                                                                                         sticky="nsew",
                                                                                                         pady=10)
    mid_grid.grid(row=1, column=1, sticky="nsew", pady=0)

    backup_frame.grid(row=0, column=1, sticky="nsew")
    div_frame.pack(expand=True, fill="both", padx=1, pady=1)

    scrollable_frame.add_item(top_info)

    Ef.ThreadedStatsLoader(top_info, world_path, scrollable_frame, config, world_data_grabbed, map_image).pack()

    scrollable_frame.pack(pady=0, padx=5, fill="both", expand=True)

    death_map_footer = None
    if not config["enabled_save_displays"]["Death markers"]:
        if os.path.exists(Util.CONFIG_PATH + "/assets/death_maps/noita_map"):
            sd = Ef.SessionDisplay(panel, world_path + "/Nolla_Games_Noita/save00/stats/sessions", Util.CONFIG_PATH,
                                   map_image, rendered=False)
            death_map_footer = {"name": "Death marker Map", "style": "info-outline", "command": sd.export_death_markers}

    def toggle_entry_listing_action():
        can_be_delisted = Util.entry_is_delistable(world_path, config["world_paths"])
        if isinstance(delistable, bool):
            if can_be_delisted:
                unlist_noita_save(world_path)
            else:
                if add_save_path(world_path) == world_path:
                    frame_move_manager.reload_frame()

    toggle_entry_listing = None
    delistable = Util.entry_is_delistable(world_path, config["world_paths"])
    if isinstance(delistable, bool):
        toggle_entry_listing = {"name": "Delist from Home" if delistable else "List to Homepage",
                                "style": f"{"danger" if delistable else "success"}-outline",
                                "command": toggle_entry_listing_action}

    has_outline = "-outline"
    if os.path.exists(world_path + "/Nolla_Games_Noita/save00/player.xml"):
        has_outline = ""
    Ef.FooterFrame(panel, [
        {"name": "Play save", "style": f"success{has_outline}", "command": lambda: play_selected_world(world_path)},
        toggle_entry_listing,
        {"name": "Open folder Location", "style": "primary-outline",
         "command": lambda: Util.opening_folder(world_path)},
        death_map_footer,
        {"name": "RETURN", "style": "warning-outline", "command": frame_move_manager.previous_frame}
    ], pad_x=5 if toggle_entry_listing or death_map_footer else 20, relief=RAISED).pack(padx=15, pady=15)

    panel.pack(pady=0, padx=0, fill="both", expand=True)
    root.pack(fill="both", expand=True)
    window.protocol("WM_DELETE_WINDOW", on_close)
    window.update_idletasks()


def create_main_window():
    global action_to_funk_map
    global set_swap_select
    global config
    global root

    new_save_count = look_for_unlisted_noita_saves()
    if new_save_count >= 1:
        scroll_depth.set(0.0)

    Util.update_modded_seeker_list(config)
    last_played_path = Util.get_last_played_path()
    if last_played_path:
        action_to_funk_map["Play"] = lambda: set_world_frame(last_played_path)
    else:
        action_to_funk_map["Play"] = start_new_save
    action_to_funk_map["Open"] = create_settings_window
    set_swap_select = None
    frame_move_manager.add_frame("HOME", create_main_window)
    root.destroy()
    window.protocol("WM_DELETE_WINDOW", on_close)
    root = tb.Frame(window)

    container = tb.Frame(root)
    tb.Frame(container).pack(pady=12)

    top_grid = tb.Frame(container)
    top_grid.grid_rowconfigure(0, weight=1)
    top_grid.grid_rowconfigure(1, weight=1)
    top_grid.grid_columnconfigure(0, weight=1)
    top_grid.grid_columnconfigure(1, weight=1)
    tb.Frame(top_grid, width=215, height=100).grid(row=0, column=0, sticky="nsew")

    image = Canvas(top_grid, width=300, height=115)
    image.create_image(0, 0, anchor=NW, image=LOGO)
    image.image = LOGO
    image.grid(row=0, column=1, sticky="nsew")

    search_frame = tb.Frame(top_grid, width=250, height=100)
    search_results = tb.Label(search_frame,
                              text="" if new_save_count == 0 else f"{new_save_count} save{"\nhas" if new_save_count == 1 else "s \nhave"} newly been\nloaded in...",
                              font=Util.tk_font("Tm"))
    search_bar = tb.Entry(search_frame, width=26, style="secondary")
    search_bar.pack(anchor="ne", padx=5, pady=5)
    search_results.pack(anchor="nw", padx=5, pady=5)
    search_frame.grid(row=0, column=2, sticky="nsew")
    top_grid.pack(fill="x")

    canvas = tk.Canvas(container)

    scroll_frame = Ef.ExtendedTkFrame(canvas, scroll_depth)
    search_bar.bind("<Return>", lambda e, frame=scroll_frame: search_worlds(e, frame, search_results))

    Ef.ThreadedWorldsLoader(scroll_frame.scrollable_frame, config["world_paths"].copy(), scroll_frame, config,
                            play_selected_world, set_world_frame)

    footer_button = []
    if last_played_path:
        has_outline = "-outline"
        if os.path.exists(last_played_path + "/Nolla_Games_Noita/save00/player.xml"):
            has_outline = ""
        footer_button.append({"name": "Open last played", "style": f"success{has_outline}",
                              "command": lambda: set_world_frame(last_played_path)})
    footer_button.append({"name": "Play new save", "style": "success-outline", "command": start_new_save})
    if len(config["world_paths"]) >= 1:
        footer_button.append({"name": "Play backup of a save", "style": "info-outline",
                              "command": lambda: run_selection(scroll_frame, create_backup_save)})

    footer_button.append({"name": "Settings", "style": "primary-outline", "command": create_settings_window})
    if len(config["world_paths"]) >= 2:
        footer_button.append(
            {"name": "Swap save entries", "style": "warning-outline", "command": lambda: run_selection(scroll_frame)})

    Ef.FooterFrame(scroll_frame, footer_button, pad_x=8, relief=RAISED).grid(pady=12)

    scroll_frame.pack(fill="both", expand=True)
    canvas.pack(fill="both", expand=True)
    container.pack(fill="both", expand=True)
    root.pack(fill="both", expand=True)
    scroll_frame.update_idletasks()
    scroll_frame.canvas.yview_moveto(scroll_depth.get())


def resize_window():
    global config
    state = config["appearance"].get("state", "normal")
    geometry = config["appearance"].get("geometry", "700x600+50+50")
    if state == "fullscreen":
        window.attributes("-fullscreen", True)
    elif state == "zoomed":
        window.attributes("-fullscreen", False)
        window.after(10, lambda: window.state("zoomed"))
    else:
        window.state("normal")
        window.geometry(geometry)


def save_config():
    global config
    config["game"]["noita_path"] = Util.NOITA_PATH
    config["game"]["noita_runner_arg"] = Util.RUNNER_ARG
    config["appearance"]["geometry"] = window.geometry()
    config["appearance"]["state"] = window.state()
    with open(Util.CONFIG_PATH + "/data.json", "w") as f:
        json.dump(config, f, indent=4)


def on_close():
    save_config()
    root.destroy()
    window.destroy()
    if os.path.exists(Util.CONFIG_PATH + "/temp"):
        try:
            shutil.rmtree(Util.CONFIG_PATH + "/temp")
        except:
            pass
    sys.exit()


config = {}

with open(Util.CONFIG_PATH + "/data.json") as f:
    try:
        config = json.load(f)
    except Exception as e:
        reset_error_configs = False
        Util.notification(4, {"type": "warn", "title": "FAULTY CONFIG!!!",
                              "message": f"Cannot proceed until\n{e}\n is fixed..."})
        if Util.notification(999, {"type": "ask", "title": "FAULTY CONFIG!!!",
                                   "message": f"Failed to load:\n{Util.CONFIG_PATH}/data.json\n...{e}\n\n Would you like to reset configs to default?"}):
            if reset_config(False):
                reset_error_configs = True
        if not reset_error_configs:
            sys.exit()

for config_key, config_stats in Util.DEFAULT_CONFIG.items():
    config = Util.setup_config_key(config, config_key, config_stats, config_key == "keybind")

if "spoiler_links" not in config.keys():
    config["spoiler_links"] = Util.DEFAULT_SPOILER_LINKS

if "modded_starter_agrs" not in config.keys():
    config["modded_starter_agrs"] = Util.DEFAULT_MOD_ARGS

if "world_paths" not in config.keys():
    config["world_paths"] = []

if "unlisted_paths" not in config.keys():
    config["unlisted_paths"] = []

Ef.update_frame_config_variables(config)
Util.user_able_to_create_symlink()
Util.NOTIFICATION_THRESHOLD = config["appearance"].get("notification_threshold", 1)
Util.USE_NOITA_FONT = config["appearance"].get("use_noita_font", True)
moved_path = move_playing_path()
if not moved_path:
    sys.exit()

if config["save_management"].get("auto_list_unknown_saves"):
    if config["save_management"].get("default_saves_path", "") == "":
        prev_folder_is_save_folder = moved_path.replace("\\", "/")
        prev_folder_is_save_folder = prev_folder_is_save_folder.replace(prev_folder_is_save_folder.split("/")[-1], "")
        config["save_management"]["default_saves_path"] = prev_folder_is_save_folder

if not isinstance(moved_path, bool):
    if config["save_management"].get("copy_config_to_new_saves"):
        if config["save_management"].get("favourite_config_file", "") == "":
            default_config_path = moved_path.replace("\\", "/") + "/Nolla_Games_Noita/save_shared/config.xml"
            if os.path.exists(default_config_path):
                config["save_management"]["favourite_config_file"] = default_config_path

config["game"]["noita_path"] = Util.NOITA_PATH
config["game"]["noita_runner_arg"] = Util.RUNNER_ARG

"""
INIT WINDOW
"""
window = tb.Window(title="Noita Worlds Manager", size=(700, 600))
WINDOW_SCALING = window.winfo_fpixels('1i')/WINDOW_SCALING
window.tk.call('tk', 'scaling', WINDOW_SCALING)
backup = Util.make_default_themes()
try:
    used_theme = Util.get_themes()[config["appearance"].get("theme", "dark")]
    custom_theme = ThemeDefinition(used_theme["name"], used_theme["colors"])
    style = tb.Style()
    style.register_theme(custom_theme)
    style.theme_use(custom_theme.name)
except Exception as e:
    Util.notification(2, {"type": "warn", "title": "No theme",
                          "message": f"Failed to load theme:\n{config["appearance"]["theme"]}.json\nDefaulting to built-in preset...\n\n{e}"})
    custom_theme = ThemeDefinition(backup["name"], backup["colors"])
    style = tb.Style()
    style.register_theme(custom_theme)
    style.theme_use(custom_theme.name)
    config["appearance"]["theme"] = backup["name"]

window.wm_minsize(700, 600)

_pressed_play = False
Util.update_modded_seeker_list(config)
if Util.process_running():
    _pressed_play = True
    reset_pressed_play()

scroll_depth = tb.DoubleVar(value=0.0)
select_scroll_depth = tb.DoubleVar(value=0.0)
settings_scroll_depth = tb.DoubleVar(value=0.0)

frame_move_manager = Ef.FrameFlowController("HOME", create_main_window, cancel_select_swapper)

resize_window()

action_to_funk_map = {"Play": start_new_save, "Open": create_settings_window,
                      "Back": frame_move_manager.previous_frame, "Next": frame_move_manager.next_frame,
                      "Home": frame_move_manager.home}

window.protocol("WM_DELETE_WINDOW", on_close)
ICON = Util.HOME_PATH + "/assets/image/ico.ico"
LOGO = ImageTk.PhotoImage(
    Image.open(Util.HOME_PATH + "/assets/image/logo.png").resize((300, 100), Image.Resampling.NEAREST))
root = tb.Frame(window)
root.pack(fill="both", expand=True)
Util.set_retro_font_family()
window.withdraw()
create_main_window()
map_image = ImageTk.PhotoImage(Image.open(Util.HOME_PATH + "/assets/image/normal_noita_map.png"))
window.bind("<Button>", lambda e: run_keypress(e))
window.bind("<Key>", lambda e: run_keypress(e))
Util.create_wand_stats_images(Util.HOME_PATH, window)
window.deiconify()
window.iconbitmap(ICON)
window.mainloop()
if __name__ == "__main__":
    pass

"""
--------------------------------------------------------- TODO ---------------------------------------------------------



- prepare instructions for users to make exe at home, incase download doesnt work


- improve code quality:
    - place noita interface stuff in its own dedicated script
    - place settings / config stuff in its own handler
    - divide ui aspects into their own respective categories
        - prerender, credits and settings panel instead of instantiating that shit every time, dumbass
    - more object orientated instead of whatever i decided to go with


- wand export pictures not true to the games wand view:
    - make spell images smaller (scale with noitas stuff)
    - spells and border not scaled or centered properly
    - alpha value is off (visible with nolla spell/ looks weird)

- find a better way to display multiple mods in a save display
- find a better way to display more than 6 spoiler links in the save display

- delisting upon detected deleted save, not working properly (when cancelling, also not moving top un_listed entries properly)

- image rescaling sometimes gets squashed (visible for large polyed mina display)

- merge saves functionality
    - be able so select two saves:
        - merge sessions played
        - merge gifs and images recorded
        - merge flags files
        - (anything that isnt the config file)

- perk pictures missing border

- dont count fungalshift to overall perk count
- identify more than one shift in a world (currently can only detect one)
- find a way to identify "newgame ++..." in an ongoing run

- use pack_forget and pack to hotswap between displays instead of recreating them every time:
    - prerender settings frame
    - prerender credits frame
    - prerender any frame i can

- progress panel: a display of the tree-chievements
    - under persistant/flags folder "progress_*" files are tree section entries

- perk progress panel
- spell progress panel
- enemy progress panel

- inventory panel
    - displays everything the player is holding + spells in their inventory

- xml stats grabber modify dropdown can sometimes be bigger than screen... cannot scroll though options?!?! make it user friendlier

- allow user to swap xml stats grabber entries position

- allow user to swap spoiler link entries position

- allow user to select a key in the list of dicts in the settings panel

--------------------------------------------------------- DONE ---------------------------------------------------------


"""