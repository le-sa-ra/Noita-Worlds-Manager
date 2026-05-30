from PIL import ImageDraw, ImageFont
from random import randint as rng
from psutil import process_iter
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
from datetime import datetime
from time import time, sleep
from tkinter import font
import subprocess
import webbrowser
import xmltodict
import hashlib
import ctypes
import struct
import winreg
import math
import stat
import json
import csv
import sys
import io
import os

mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\NoitaSavesManager_le-sa-ra_GWKKIMIZ")
if ctypes.windll.kernel32.GetLastError() == 183:
    messagebox.showerror("Cannot open NWM twice!", "You cannot have two NWM instances open at once!\nPlease close the currently running NWM instance\n\n(If the window isn't visible you will have to terminate it through the TaskManager)")
    sys.exit(0)

HOME_PATH = os.path.dirname(os.path.abspath(__file__))[:-4]
ROAMING = os.getenv('APPDATA')
CONFIG_PATH = ROAMING + r"\Noita_saves"
NOITA_SAVE_PATH = ROAMING.replace("Roaming", "") + r"LocalLow\Nolla_Games_Noita"
SEEK_RUNNING_APPLICATIONS = ["noita.exe"]


DEFAULT_CONFIG = {
    "game": {
        "noita_path": None,
        "noita_runner_arg": None
    },
    "save_management": {
        "new_save_entries_to_start": False,
        "auto_list_unknown_saves": False,
        "permanent_delisting": False,
        "one_to_one_backup": True,
        "default_saves_path": "",
        "copy_config_to_new_saves": True,
        "favourite_config_file": ""
    },
    "appearance": {
        "geometry": None,
        "state": None,
        "theme": "dark",
        "use_noita_font": True,
        "place_played_save_to_start": False,
        "accurate_wand_export": True,
        "notification_threshold": 3
    },
    "enabled_save_displays": {
        "ENTRY_Spoiler sites": False, "ENTRY_Mina model": True,
        "Held wands": True, "Gifs": True,
        "Death markers": True, "Latest stats": False,
        "Extra notes": False, "Active perks": False,
        "Bone wands": False, "Images": False, "force_first_frames": 3
    },
    "keybind": {
        "mbt-2": "Open",
        "key-Escape": "Home",
        "key-space": "Play",
        "mbt-5": "Next",
        "mbt-4": "Back"
    },
    "scroll_frame_settings": {
        "scroll_inverted": False,
        "scroll_intensity": 60,
        "auto_scroll": True,
        "scroll_frame_visibility": 1.0
    },
    "xml_stats_grab": {
        "stats_Playtime_APPEND_s": ["Stats", "stats", "$playtime_str"],
        "player_Health": ["Entity", "DamageModelComponent", "$hp"],
        "Money collected_APPEND_ $": [],
        "player_Current Balance_APPEND_ $": ["Entity", "WalletComponent", "$money"],
        "player_Money spent_APPEND_ $": ["Entity", "WalletComponent", "$money_spent"],
        "stats_Kills_APPEND_ ☠": ["Stats", "stats", "$enemies_killed"],
        "player_POS X": ["Entity", "_Transform", "$position.x"],
        "player_POS Y": ["Entity", "_Transform", "$position.y"],
        "stats_Seed": ["Stats", "stats", "$world_seed"],
        "player_HIDDEN_stats_file": ["Entity", "GameStatsComponent", "$stats_filename"],
        "": []
    }
}

DEFAULT_SPOILER_LINKS = {
    "Reveal Run Info": {"color": "info", "link": "https://www.noitool.com/info?seed={{stats_Seed}}"},
    "Reveal Run Map": {"color": "success", "link": "https://lymm37.github.io/noita-telescope/?seed={{stats_Seed}}"},
    "Noita Map": {"color": "primary-outline", "link": "https://noitamap.com/"},
    "General Achievements": {"color": "warning-outline", "link": "https://noita.wiki.gg/wiki/Steam_and_GOG_Achievements"},
    "All Noita Progress": {"color": "success-outline", "link": "https://ipeterov.github.io/noita-progress/"}
}

DEFAULT_MOD_ARGS = [
    {"mod_id": "0", "mod_name": "quant.ew", "looking_for": "noita_proxy.exe", "start_noita_too": False, "seek_running_name": True, "application_path": None, "argument_enabled": True},
    {"mod_id": "0", "mod_name": "noita-together", "looking_for": "/Noita Together.exe", "start_noita_too": True, "seek_running_name": False, "application_path": None, "argument_enabled": True}
]


def setup_config_key(config, key_subject, default_map, inv_map=False):
    if key_subject not in config.keys():
        config[key_subject] = {}
    for key_map, val_map in default_map.items():
        if inv_map:
            if val_map not in config[key_subject].values():
                config[key_subject][key_map] = val_map
        else:
            if key_map not in config[key_subject].keys():
                config[key_subject][key_map] = val_map
    return config.copy()


def __iterate_world_path_for_mods(path):
    name, ids = get_enabled_mod_list(path)
    results = get_enabled_mod_list(path, "0")
    name += results[0]
    ids += results[1]
    return name, ids


def open_path_process(path):
    try:
        runner = path
        if os.path.exists(path):
            name = path.replace("\\", "/").split("/")[-1]
            path = path[:-len(name)]
            os.chdir(path)
            runner = name
        os.startfile(runner)
        return True
    except:
        return False


def list_all_mods_possible(config):
    mod_id_set = []
    for path in config["world_paths"]:
        results = __iterate_world_path_for_mods(path)
        for i in range(len(results[0])):
            mod_uuid = f"{results[0][i]}--|--{results[1][i]}"
            if mod_uuid not in mod_id_set:
                mod_id_set.append(mod_uuid)
    for path in config.get("unlisted_paths", []):
        results = __iterate_world_path_for_mods(path)
        for i in range(len(results[0])):
            mod_uuid = f"{results[0][i]}--|--{results[1][i]}"
            if mod_uuid not in mod_id_set:
                mod_id_set.append(mod_uuid)
    mod_id_set.sort()
    return mod_id_set


def get_mod_app_path(mod_args_idx, config):
    open_folder_at = config["save_management"].get("default_saves_path", CONFIG_PATH)
    if config["modded_starter_agrs"][mod_args_idx]["application_path"]:
        folder_path = config["modded_starter_agrs"][mod_args_idx]["application_path"]
        ending = folder_path.split("/")[-1]
        open_folder_at = folder_path.replace(ending, "")

    if notification(2, {"type": "ask", "title": f"Set up mod path \"{config["modded_starter_agrs"][mod_args_idx]["mod_name"]}\"", "message": f"The world you are trying to run has the following mod:\n- {config["modded_starter_agrs"][mod_args_idx]["mod_name"]}\n\nCould you provide a path to the mods required application:\n- {config["modded_starter_agrs"][mod_args_idx]["looking_for"].split("/")[-1]}"}):
        file_ending = config["modded_starter_agrs"][mod_args_idx]["looking_for"].split("/")[-1].split(".")[-1]
        location = filedialog.askopenfilename(initialdir=open_folder_at, title=f"{config["modded_starter_agrs"][mod_args_idx]["mod_name"]} path location...",
                                              initialfile=config["modded_starter_agrs"][mod_args_idx]["looking_for"].split("/")[-1], defaultextension=".",
                                              filetypes=[("All Files", f"*.{file_ending if file_ending else "*"}")])

        if location:
            if location.endswith(".lnk"):
                location = get_shortcut_target(location)

            if location.endswith(config["modded_starter_agrs"][mod_args_idx]["looking_for"]):
                if os.path.exists(location):
                    config["modded_starter_agrs"][mod_args_idx]["application_path"] = location
                    return location
        if config["modded_starter_agrs"][mod_args_idx]["application_path"]:
            if os.path.exists(config["modded_starter_agrs"][mod_args_idx]["application_path"]):
                return config["modded_starter_agrs"][mod_args_idx]["application_path"]
        if notification(99, {"type": "ask", "title": f"No valid path to run \"{config["modded_starter_agrs"][mod_args_idx]["mod_name"]}\"", "message": f"The path provided {f"({location})" if location else ""} seems to not lead th the desired location:\n{config["modded_starter_agrs"][mod_args_idx]["looking_for"]}\n\nWould you like to try giving another path?\n(cancelling will open the save without running the mod app!)"}):
            return get_mod_app_path(mod_args_idx, config)
        else:
            notification(4, {"type": "info", "title": f"Setting", "message": "When you want to set the mod app path\nYou can go into the settings under \"Mod start args\"\nand set a path there..."})
            config["modded_starter_agrs"][mod_args_idx]["application_path"] = "None"

    if config["modded_starter_agrs"][mod_args_idx]["application_path"]:
        return config["modded_starter_agrs"][mod_args_idx]["application_path"]
    return ""


def update_modded_seeker_list(config):
    global SEEK_RUNNING_APPLICATIONS
    SEEK_RUNNING_APPLICATIONS = ["noita.exe"]
    for entry in config["modded_starter_agrs"]:
        if entry["seek_running_name"]:
            app_to_seek = entry["looking_for"].split("/")[-1].lower()
            if app_to_seek:
                SEEK_RUNNING_APPLICATIONS.append(app_to_seek)


def hashify(string):
    return hashlib.md5(string).hexdigest()


def get_valid_folder(path):
    try:
        if os.path.exists(path):
            if os.path.isdir(path):
                return path
        else:
            return get_valid_folder(path.replace(path.split("/")[-1], ""))
    except:
        return path


def is_valid_noita_path(location):
    if location:
        if os.path.isdir(location):
            if "Nolla_Games_Noita" in os.listdir(location):
                return location.replace("\\", "/")
        if "Nolla_Games_Noita" in location:
            return location.split("Nolla_Games_Noita")[0][:-1].replace("\\", "/")
    return False


def get_shortcut_target(path):
    if not path.endswith(".lnk"):
        return path
    try:
        cmd = f'''
        $s=(New-Object -COM WScript.Shell).CreateShortcut("{path}");
        $s.TargetPath
        '''
        result = subprocess.check_output(["powershell", "-Command", cmd])
        return result.decode().strip()
    except:
        return path


def create_symlink(origin: str, destination: str):
    if path_is_symlink(destination):
        return False
    if os.path.exists(origin):
        try:
            command = (
                '$ErrorActionPreference = "Stop"; '
                f'New-Item -ItemType Junction -Path "{os.path.normpath(destination)}" -Target "{os.path.abspath(origin)}"'
            )

            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0 and path_is_symlink(destination)
        except FileExistsError or OSError:
            return False
    return False


def path_is_symlink(symlink_path: str):
    try:
        return os.path.isdir(symlink_path) and bool(os.lstat(symlink_path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT) and not os.path.islink(symlink_path)
    except (AttributeError, FileNotFoundError):
        return False


def delete_save_link(symlink_path: str):
    try:
        if path_is_symlink(symlink_path):
            os.rmdir(symlink_path)
            return True
        return False
    except FileNotFoundError or OSError:
        return False


def update_symlink(new_world_path):
    if path_is_symlink(NOITA_SAVE_PATH):
        if delete_save_link(NOITA_SAVE_PATH):
            if create_symlink(new_world_path + "/Nolla_Games_Noita", NOITA_SAVE_PATH):
                return f"Created world link to:{new_world_path}"
            return notification(2, {"type": "warn", "title": "Could not create link", "message": f"Failed to create world link to:{new_world_path}"})
        return notification(2, {"type": "warn", "title": "Could not remove old link", "message": f"Failed to remove currently active world link"})
    return notification(2, {"type": "warn", "title": "Path is a real dir", "message": f"Desired junction path is not a Junction.\nCannot proceed unless:\n{NOITA_SAVE_PATH}\nDoesnt exist or is already a link..."})


def get_last_played_path():
    if os.path.exists(NOITA_SAVE_PATH):
        if path_is_symlink(NOITA_SAVE_PATH):
            real_path = os.path.realpath(NOITA_SAVE_PATH).replace("Nolla_Games_Noita", "")[:-1]
            if os.path.exists(real_path):
                if not path_is_symlink(real_path):
                    return real_path
    return None


def _get_file_size_by_path(path):
    if os.path.exists(path):
        return os.path.getsize(path)
    return 0


def look_for_good_xml_files(world_paths):
    # world,player,stats,kills,mod_conf,stream conf
    xmls_found = [None, None, None, None, None, None]
    xmls_sizes = [0, 0, 0, 0, 0, 0]
    for w_p in world_paths:

        world_path = w_p+"/Nolla_Games_Noita/save00/world_state.xml"
        player_path = w_p+"/Nolla_Games_Noita/save00/player.xml"
        mod_path = w_p+"/Nolla_Games_Noita/save00/mod_config.xml"
        stream_path = w_p+"/Nolla_Games_Noita/save00/streaming_event_config.xml"

        world_path_size = _get_file_size_by_path(world_path)
        if world_path_size > xmls_sizes[0]:
            xmls_found[0] = world_path
            xmls_sizes[0] = world_path_size
        player_path_size = _get_file_size_by_path(player_path)
        if player_path_size > xmls_sizes[1]:
            xmls_found[1] = player_path
            xmls_sizes[1] = player_path_size
        mod_path_size = _get_file_size_by_path(mod_path)
        if mod_path_size > xmls_sizes[4]:
            xmls_found[4] = mod_path
            xmls_sizes[4] = mod_path_size
        stream_path_size = _get_file_size_by_path(stream_path)
        if stream_path_size > xmls_sizes[5]:
            xmls_found[5] = stream_path
            xmls_sizes[5] = stream_path_size

        if os.path.exists(player_path):
            stats = get_player_stats(player_path)
            stats_file = w_p+"/Nolla_Games_Noita/save00/stats/sessions/"+stats["stats_filename="].split("/")[-1].split("_")[0]+"_stats.xml"
            kills_file = stats_file.replace("_stats.xml", "_kills.xml")
            stats_file_size = _get_file_size_by_path(stats_file)
            if stats_file_size > xmls_sizes[2]:
                xmls_found[2] = stats_file
                xmls_sizes[2] = stats_file_size
            kills_file_size = _get_file_size_by_path(kills_file)
            if kills_file_size > xmls_sizes[3]:
                xmls_found[3] = kills_file
                xmls_sizes[3] = kills_file_size

    return xmls_found


def notification(importance, message, fallback=True):
    global ICON_IMAGE
    if importance > NOTIFICATION_THRESHOLD:
        if isinstance(message, dict):
            out_val = {"info": messagebox.showinfo, "ask": messagebox.askokcancel, "warn": messagebox.showerror}[
                       message["type"]](message["title"], message["message"], parent=ICON_IMAGE)
        else:
            out_val = message(parent=ICON_IMAGE)
        return out_val
    return fallback


def perk_path_to_name_and_desc(path):
    if not path.startswith("mods/"):
        base_name = path.split("/")[-1].replace(".png", "")
        perk_name = None
        perk_desc = None
        if base_name in IMG_PATH_TO_NAME.keys():
            base_name = IMG_PATH_TO_NAME[base_name]
        if base_name in TRANSLATIONS["perk_"].keys():
            perk_name = TRANSLATIONS["perk_"][base_name]
        if base_name in TRANSLATIONS["perkdesc_"].keys():
            perk_desc = TRANSLATIONS["perkdesc_"][base_name].replace("\\n", " ")
            if perk_desc.endswith(" "):
                perk_desc = perk_desc[:-1]
            if perk_desc[-1] in "abcdefghijklmnopqrstuvwxyz0123456789":
                perk_desc += "."
        return perk_name, perk_desc
    else:
        return None, None


def get_newest_session_file(world_session_path):
    out_path = ""
    if os.path.exists(world_session_path):
        oldest_one = [0, 0]
        session_list = os.listdir(world_session_path)
        if len(session_list) == 0:
            return None
        for session in session_list:
            if session.endswith("_kills.xml"):
                big_time, smol_time = session.replace("_kills.xml", "").split("-")
                new_time = [int(big_time), int(smol_time)]
                if new_time[0] > oldest_one[0]:
                    oldest_one = new_time.copy()
                    out_path = session
                if new_time[0] == oldest_one[0]:
                    if new_time[1] > oldest_one[1]:
                        oldest_one = new_time.copy()
                        out_path = session
    return out_path


def reduced_string(value):
    return value.replace("Write extra notes here...", "").lower().replace("\n", "").replace(" ", "").replace("\\", "")


def get_world_playtime(world_path):
    if not os.path.exists(world_path + "/Nolla_Games_Noita/save00/player.xml"):
        return None
    file = get_any_xml_stat(world_path + "/Nolla_Games_Noita/save00/player.xml", {"session": ["Entity", "GameStatsComponent", "$stats_filename"]})["session"]
    session_name = file.split("/")[-1].replace("_kills", "_stats")
    if not os.path.exists(world_path + "/Nolla_Games_Noita/save00/stats/sessions/"+session_name):
        return None
    float_time = get_any_xml_stat(world_path + "/Nolla_Games_Noita/save00/stats/sessions/"+session_name, {"time": ["Stats", "stats", "$playtime"]})
    float_time["date"] = session_name.split("_")[0]
    try:
        float_time["time"] = float(float_time["time"])
    except:
        float_time = None
    return float_time


def spell_path_to_wiki_name(path):
    if not path.startswith("mods/"):
        spell_name = path.split("/")[-1].replace(".png", "")
        spell_name = spell_name.replace("spitter_green", "SPITTER_TIER_2").replace("spitter_purple",
                                                                                   "SPITTER_TIER_3").replace("_timer",
                                                                                                             "_TIMER")
        if spell_name in TRANSLATIONS["action_"].keys():
            spell_name = TRANSLATIONS["action_"][spell_name].split(" with ")[0]

        if spell_name in IMG_PATH_TO_NAME.keys():
            spell_name = IMG_PATH_TO_NAME[spell_name]
        if spell_name in ["Cement", "Blood", "Acid", "Water", "Oil"]:
            spell_name += " (Spell)"
        return spell_name
    else:
        return None


def opening_folder(path):
    if os.path.exists(path):
        os.startfile(path)
    else:
        notification(1, messagebox.showinfo("INFO", "Specified folder could not be found..."))


def opening_page(site, local_site=False):
    if site == "":
        return
    if local_site:
        webbrowser.open(site)
    else:
        if notification(2, {"type": "ask", "title": "INFO", "message": f"This program would like to open the following web-page:\n{site}"}):
            webbrowser.open(site)


def open_xml_dict(path, fallback={}):
    try:
        with open(path) as path_conf:
            data = xmltodict.parse(path_conf.read())
        return data
    except:
        return fallback


def update_mod_name_to_workshop_id(world_path):
    global MOD_NAME_TO_ID
    global CURRENT_WORLD_PATH
    MOD_NAME_TO_ID = {}
    CURRENT_WORLD_PATH = None
    if not os.path.exists(world_path + "/Nolla_Games_Noita/save00/mod_config.xml"):
        return
    try:
        with open(world_path + "/Nolla_Games_Noita/save00/mod_config.xml") as mod_conf:
            data = xmltodict.parse(mod_conf.read())
    except:
        return
    CURRENT_WORLD_PATH = world_path
    mod_list = [data["Mods"]['Mod']]
    if isinstance(data["Mods"], list):
        mod_list = data["Mods"]['Mod']
    for mod in mod_list[0]:
        mod_path = NOITA_PATH.replace("\\", "/") + "/mods/" + mod["@name"]
        if not os.path.exists(mod_path):
            mod_path = NOITA_PATH.split("common")[0].replace("\\", "/") + "workshop/content/881100/" + mod["@workshop_item_id"]
        MOD_NAME_TO_ID[mod["@name"]] = {"path": mod_path, "enabled": [False, True][int(mod["@enabled"])]}


def goto_top_entry(world_path):
    if os.path.exists(world_path + "/data.json"):
        try:
            with open(world_path + "/data.json") as f:
                selected_world_data = json.load(f)
            if os.path.exists(selected_world_data.get("is_backup_of", "")):
                return goto_top_entry(selected_world_data.get("is_backup_of", ""))
        except:
            pass
    return world_path


def iter_down_backups(world_path, all_entries):
    all_entries.append(world_path)
    if os.path.exists(world_path + "/data.json"):
        try:
            with open(world_path + "/data.json") as f:
                selected_world_data = json.load(f)
            if os.path.exists(selected_world_data.get("backup_path", "")):
                iter_down_backups(selected_world_data.get("backup_path", ""), all_entries)
        except:
            pass
    return all_entries


def entry_is_delistable(world_path, listed_entries):
    has_a_listed_entry = False
    for entry_path in iter_down_backups(goto_top_entry(world_path), []):
        if not world_path == entry_path:
            if entry_path in listed_entries:
                has_a_listed_entry = True
                break
    if has_a_listed_entry:
        return world_path in listed_entries
    if world_path in listed_entries:
        return None
    return False


def get_mods(world_path):
    update_mod_name_to_workshop_id(world_path)
    enabled_mods = []
    mods = []
    for mod_name in MOD_NAME_TO_ID:
        if MOD_NAME_TO_ID[mod_name]["enabled"]:
            enabled_mods.append({"name": mod_name, "path": MOD_NAME_TO_ID[mod_name]["path"]})

    for mod in enabled_mods:
        mod_path = mod["path"]
        mod_id = mod_path.split("/")[-1]
        mod_link = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        if mod_id == "0":
            new_mod_path = NOITA_PATH + "mods/" + mod["name"]
            if os.path.exists(new_mod_path):
                mod_path = new_mod_path

        xml_path = mod_path + "/mod.xml"
        if os.path.exists(xml_path):
            mod_info = get_any_xml_stat(xml_path, {"name": ["Mod", "$name"], "desc": ["Mod", "$description"]})
        else:
            mod_info = {"name": mod["name"], "desc": ""}
        mod_info["path"] = mod_path
        mod_info["desc"] = mod_info["desc"].replace("\\n", "")
        mod_info["link"] = mod_link
        if mod_id == "0":
            mod_info["link"] = "https://www.google.com/search?q=" + mod_info["name"] + f"{"" if "noita" in mod_info["name"].lower() else " Noita"} mod"
        mods.append(mod_info)
    return mods


def get_that_noita_together_player_model():
    if CURRENT_WORLD_PATH:
        curr_player_path = CURRENT_WORLD_PATH +"/Nolla_Games_Noita/save00/player.xml"
        found = None
        for xml_path in get_any_xml_stat(curr_player_path, {"player": ["Entity", "SpriteComponent", "$image_file"]})["player"]:
            if xml_path.startswith("mods/noita-together/files/emotes/entities_gfx/"):
                found = xml_path
                break
        if not found:
            return None
        player_xml = NOITA_PATH+found
        result = get_any_xml_stat(player_xml, {"player": ["Sprite", "$filename"]})["player"]
        with open(player_xml) as skin_specs:
            data = xmltodict.parse(skin_specs.read())
            widths = [int(data["Sprite"]["RectAnimation"][0]["@frame_width"]),
                      int(data["Sprite"]["RectAnimation"][0]["@frame_height"]) + 1,
                      int(data["Sprite"]["RectAnimation"][0]["@frame_count"])]
        return slice_mina("player", Image.open(NOITA_PATH + result).convert("RGBA"), widths)
    return None


def get_that_entangled_world_player_model_maybe():
    """
    I don't remember what I was on, but it must have been too much.
    '"""
    for k, v in MOD_NAME_TO_ID.items():
        if v["enabled"]:
            if os.path.exists(NOITA_PATH + f"mods/{k}"):
                if os.path.exists(NOITA_PATH + f"mods/{k}/files/system/player/tmp"):
                    for entry in os.listdir(NOITA_PATH + f"mods/{k}/files/system/player/tmp"):
                        if entry.endswith(".png") and "lukki" not in entry:
                            tmp_img = Image.open(NOITA_PATH + f"mods/{k}/files/system/player/tmp/{entry}")
                            if tmp_img.width == 420 and tmp_img.height == 922:
                                return slice_mina("player", Image.open(
                                    NOITA_PATH + f"mods/{k}/files/system/player/tmp/{entry}").convert("RGBA"),
                                                  [12, 20, 6])
    return None


def get_player_model():
    p_g_pics = {"player": None, "playerghost": None}
    widths = {"player": [12, 20, 6], "playerghost": [13, 20, 6]}
    qew_player_model = get_that_entangled_world_player_model_maybe()
    if qew_player_model:
        p_g_pics["player"] = qew_player_model

    for k, v in MOD_NAME_TO_ID.items():
        if v["enabled"] and k == "noita-together":
            nt_player_model = get_that_noita_together_player_model()
            if nt_player_model:
                p_g_pics["player"] = nt_player_model
                break
        elif v["enabled"]:
            for p_g in p_g_pics.keys():
                for skin_paths in ["/data/enemies_gfx/", "/files/skin/enemies_gfx/"]:
                    player_pic = v["path"] + f"{skin_paths}{p_g}.png"
                    if os.path.exists(v["path"] + f"{skin_paths}{p_g}.xml"):
                        with open(v["path"] + f"{skin_paths}{p_g}.xml") as skin_specs:
                            data = xmltodict.parse(skin_specs.read())
                            player_pic = v["path"] + "/" + data["Sprite"]["@filename"]
                            widths[p_g] = [int(data["Sprite"]["RectAnimation"][0]["@frame_width"]),
                                           int(data["Sprite"]["RectAnimation"][0]["@frame_height"]) + 1,
                                           int(data["Sprite"]["RectAnimation"][0]["@frame_count"])]
                    if os.path.exists(player_pic):
                        p_g_pics[p_g] = slice_mina(p_g, Image.open(player_pic).convert("RGBA"), widths[p_g])

        if p_g_pics["player"] and p_g_pics["playerghost"]:
            break
    for p_g in p_g_pics.keys():
        if not p_g_pics[p_g]:
            p_g_pics[p_g] = PLAYER_GHOST_SLICES[p_g]
    return p_g_pics


def get_player_accessories():
    imgs_out = {}
    for drip_key, drip_path in FANCY_IMG_PATHS.items():
        imgs_out[drip_key] = None
        for k, v in MOD_NAME_TO_ID.items():
            if v["enabled"]:
                img_out = None
                data = None
                if os.path.exists(v["path"]+"/"+drip_path[:-3]+"png"):
                    img_out = Image.open(v["path"]+"/"+drip_path[:-3]+"png")
                    data = {"Sprite": {"@offset_x": "0", "@offset_y": "0", "RectAnimation": [{"@frame_width": "12", "@frame_height": "19", "@frame_count": "6"}]}}
                if os.path.exists(v["path"]+"/"+drip_path):
                    with open(v["path"]+"/"+drip_path) as skin_specs:
                        data = xmltodict.parse(skin_specs.read())
                    if os.path.exists(v["path"]+"/"+data["Sprite"]["@filename"]):
                        img_out = Image.open(v["path"]+"/"+data["Sprite"]["@filename"])
                if data and img_out:
                    pics, offsets = slice_xml_image(data, image=img_out)
                    fin_pics = []
                    for pic in pics:
                        size = (min(pic.width * 10, 160), min(pic.height * 10, 200))
                        fin_pics.append(pic.resize(size, Image.Resampling.NEAREST))
                    imgs_out[drip_key] = [fin_pics, [offsets[0]*10, offsets[1]*10]]
    return imgs_out


def get_player_final_model(world_path):
    flag_path = world_path + "/Nolla_Games_Noita/save00/persistent/flags/"
    player_slices = {}

    player_path = world_path + "/Nolla_Games_Noita/save00/player.xml"

    for k, v in get_player_model().items():
        player_slices[k] = v.copy()

    is_poly = False
    if os.path.exists(player_path):
        try:
            with (open(player_path) as stats_xml):
                data = xmltodict.parse(stats_xml.read())
                if "polymorphed" in data["Entity"]["@tags"]:
                    is_poly = True

                    player_pic = EMPTY_PNG
                    scl = [12, 20, 4]
                    if isinstance(data["Entity"]["SpriteComponent"], list):
                        out_sprite_path = data["Entity"]["SpriteComponent"][0]["@image_file"]
                    else:
                        out_sprite_path = data["Entity"]["SpriteComponent"]["@image_file"]
                    if WAK.exists(out_sprite_path.replace(".xml", ".png")):
                        player_pic = WAK.open(out_sprite_path.replace(".xml", ".png"))
                    if WAK.exists(out_sprite_path):
                        skin_data = {"Sprite": {"@filename": None, "RectAnimation": [{"@frame_width": None, "@frame_height": None, "@frame_count": None}]}}
                        for xml_line in WAK.open(out_sprite_path).split("\n"):
                            if "filename=" in xml_line and not skin_data["Sprite"]["@filename"]:
                                skin_data["Sprite"]["@filename"] = xml_line.split("\"")[1].split(".png")[0] +".png"
                            elif "frame_count=" in xml_line and not skin_data["Sprite"]["RectAnimation"][0]["@frame_count"]:
                                skin_data["Sprite"]["RectAnimation"][0]["@frame_count"] = xml_line.split("\"")[1].split("\"")[0]
                            elif "frame_height=" in xml_line and not skin_data["Sprite"]["RectAnimation"][0]["@frame_height"]:
                                skin_data["Sprite"]["RectAnimation"][0]["@frame_height"] = xml_line.split("\"")[1].split("\"")[0]
                            elif "frame_width=" in xml_line and not skin_data["Sprite"]["RectAnimation"][0]["@frame_width"]:
                                skin_data["Sprite"]["RectAnimation"][0]["@frame_width"] = xml_line.split("\"")[1].split("\"")[0]
                            if skin_data["Sprite"]["@filename"] and skin_data["Sprite"]["RectAnimation"][0]["@frame_width"] and skin_data["Sprite"]["RectAnimation"][0]["@frame_height"] and skin_data["Sprite"]["RectAnimation"][0]["@frame_count"]:
                                break
                        if WAK.exists(skin_data["Sprite"]["@filename"]):
                            player_pic = WAK.open(skin_data["Sprite"]["@filename"])
                        scl = [int(skin_data["Sprite"]["RectAnimation"][0]["@frame_width"]),
                               int(skin_data["Sprite"]["RectAnimation"][0]["@frame_height"]) + 1,
                               int(skin_data["Sprite"]["RectAnimation"][0]["@frame_count"])]

                    slices = slice_image(player_pic, scl)
                    out_slices = []
                    for x in range(scl[2]):
                        cropped = slices[x]
                        size = (min(cropped.width * 10, 160), min(cropped.height * 10, 200))
                        out_slices.append(cropped.resize(size, Image.Resampling.NEAREST))
                    player_slices["player"] = out_slices.copy()
        except:
            pass
    modded_fancies = {}
    if not is_poly:
        modded_fancies = get_player_accessories()

    for drip, enabled in {"crown": os.path.exists(flag_path+"secret_hat"),
                          "amulet": os.path.exists(flag_path+"secret_amulet"),
                          "unearned___probably": os.path.exists(flag_path+"secret_amulet_gem")}.items():
        if enabled:
            using = FANCY_PLAYER_DRIP[drip]
            if modded_fancies.get(drip, False):
                using = modded_fancies[drip][0], using[1]
            using = [using[0], using[1]]
            if is_poly:
                using_out = [[None], None]
                using_out[0][0] = using[0][0].copy()
                using_out[1] = [0, 0]
                if drip == "crown":
                    using_out[0][0] = using_out[0][0].copy().transpose(Image.ROTATE_270)
                    using_out[1] = [-40, 110]
                if drip == "amulet":
                    using_out[0][0] = using_out[0][0].copy().transpose(Image.FLIP_TOP_BOTTOM)
                    using_out[1] = [-40, 60]
                if drip == "unearned___probably":
                    using_out[1] = [50, 80]

                for i in range(len(player_slices["player"])):
                    out = player_slices["player"][i].copy()
                    p = using_out
                    out.paste(p[0][0], (p[1][0], p[1][1]), p[0][0])
                    player_slices["player"][i] = out
            else:
                for i in range(len(using[0])):
                    out = player_slices["player"][i].copy()
                    p = using
                    out.paste(p[0][i], (p[1][0] - 60, p[1][1] - 140), p[0][i])
                    player_slices["player"][i] = out

    out_slices = {}
    for player_key, player_pics in player_slices.items():
        out_pics = []
        for pic in player_pics:
            out_pics.append(ImageTk.PhotoImage(pic))
        out_slices[player_key] = out_pics
    return out_slices


def slice_xml_image(xml_data, image=None):
    slices = [int(xml_data["Sprite"]["RectAnimation"][0]["@frame_width"]),
              int(xml_data["Sprite"]["RectAnimation"][0]["@frame_height"]) + 1,
              int(xml_data["Sprite"]["RectAnimation"][0]["@frame_count"])]
    if not image:
        image = WAK.open(xml_data["Sprite"]["@filename"][5:])
    return slice_image(image, slices), (int(xml_data["Sprite"]["@offset_x"]), int(xml_data["Sprite"]["@offset_y"]))


def slice_image(png, slices):
    all_pics = []
    for x in range(slices[2]):
        all_pics.append(png.crop(((x * slices[0]), 0, (x + 1) * slices[0], slices[1])))
    return all_pics


def slice_mina(p_g, png, sl):
    slices = slice_image(png, sl)
    out_slices = []
    for x in range(sl[2]):
        cropped = slices[x]
        if "playerghost" == p_g:
            cropped = cropped.transpose(Image.FLIP_LEFT_RIGHT)
        size = (min(cropped.width * 10, 160), min(cropped.height * 10, 200))
        out_slices.append(cropped.resize(size, Image.Resampling.NEAREST))
    return out_slices


def get_enabled_mod_list(world_path, enabled="1"):
    if not os.path.exists(world_path + "/Nolla_Games_Noita/save00/mod_config.xml"):
        return [[], []]
    try:
        mod_config = open(world_path + "/Nolla_Games_Noita/save00/mod_config.xml")
    except Exception:
        return [[], []]
    enabled_mods = []
    mod_ids = []
    for m in mod_config.read().split("<"):
        if m.startswith(f"Mod enabled=\"{enabled}\""):
            enabled_mods.append(
                m.split(f'Mod enabled="{enabled}" name="')[1].split('" settings_fold_open="')[0].replace("_", " "))
            if m.startswith(f'Mod enabled="{enabled}" name="'):
                mod_ids.append(m.split('workshop_item_id="')[1].split('"')[0])
    mod_config.close()

    return enabled_mods, mod_ids


def user_able_to_create_symlink():
    if not test_junction():
        if messagebox.askokcancel("Cannot create Junctions!",
"""Your system prevented the application from creating a directory junction.
This is usually caused by filesystem restrictions from:
    - app/game notbeing on an NTFS formatted drive
    - insufficient folder permissions
      (folders are not writable)
    - antivirus / ransomware protection
\n(you may try running the Program in administrator mode)
\nWould you like to continue learning about "Junctions":"""):
            webbrowser.open("https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions")
        sys.exit(-1)


def test_junction():
    base_dir = "junction_test"

    src = os.path.join(base_dir, "src")
    dest = os.path.join(base_dir, "dest")

    try:
        if os.path.exists(dest):
            delete_save_link(dest)
        if os.path.exists(src):
            os.rmdir(src)
        if os.path.exists(base_dir):
            os.rmdir(base_dir)
        os.mkdir(base_dir)
        os.mkdir(src)
        return (create_symlink(src, dest)
                and path_is_symlink(dest)
                and os.path.normcase(os.path.realpath(dest)) == os.path.normcase(os.path.abspath(src))
                and delete_save_link(dest)
                and not os.path.exists(dest))
    except Exception:
        return False
    finally:
        try:
            if os.path.exists(dest):
                delete_save_link(dest)
        except:
            pass
        try:
            if os.path.exists(src):
                os.rmdir(src)
        except:
            pass
        try:
            if os.path.exists(base_dir):
                os.rmdir(base_dir)
        except:
            pass


def process_running(process_names=None):
    if not process_names:
        process_names = SEEK_RUNNING_APPLICATIONS
    if not isinstance(process_names, list):
        process_names = [process_names]
    for proc in process_iter(['name']):
        name = proc.info['name']
        if name.lower() in process_names:
            return True
    return False


def swap_dict_keys(d, k1, k2):
    keys = list(d.keys())
    i, j = keys.index(k1), keys.index(k2)
    keys[i], keys[j] = keys[j], keys[i]
    return {k: d[k] for k in keys}


def get_str_time(playtime):
    try:
        duration_str = ""
        d, h, m, s = int(playtime // 86400), int(playtime % 86400) // 3600, int(playtime % 3600) // 60, int(playtime % 60)
        if d == 1: duration_str += "a day "
        if d >= 2: duration_str += get_formatted_int(d) + "days "
        if h == 1: duration_str += str(h) + "hr "
        if h >= 2: duration_str += str(h) + "hrs "
        if m == 1: duration_str += str(m) + "min "
        if m >= 2: duration_str += str(m) + "mins "
        if s >= 1: duration_str += str(s) + "s"
        return "0" if duration_str == "" else duration_str
    except:
        return "∞ time"


def get_formatted_int(value, abbreviate=True):
    try:
        if value == 0 or value == "0":
            return "0"
        if isinstance(value, str):
            value = int(value)
        is_negative = value < 0
        if is_negative:
            value *= -1
        str_val = str(value)
        dotted = '.'.join([str_val[max(i - 3, 0):i] for i in range(len(str_val), 0, -3)][::-1])
        if abbreviate:
            dotted = dotted[:4]
            if dotted.endswith("."):
                dotted = dotted[:-1]
        short_idx = (len(str_val) - 1) // 3
        if short_idx >= 22:
            return "∞"
        final_var = dotted.replace(".", "." if abbreviate else ",")
        if "." in final_var and final_var[-1] == "0":
            final_var = final_var[:-1]
        return f"{"-" if is_negative else ""}{final_var}{["", "k", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc", "Ud", "Dd", "Td", "Qad", "Qid", "Sd", "Spd", "Od", "Nd", "Vg"][short_idx if abbreviate else 0]}"
    except:
        return "∞"


def array_line_text(string, max_line_char_len):
    if not isinstance(string, str):
        return ""
    output = []
    final_output = []
    test_line = ""
    for word in string.replace("\n", " ").split(" ")+[None]:
        if word:
            test_line += word + " "
        if len(test_line) > max_line_char_len:
            remove_last_word = len(word if word else "")+1
            if len(test_line.split(" ")) == 1:
                remove_last_word = 1
            output.append(test_line[:-remove_last_word])
            test_line = (word if word else "") + " "
        elif word is None:
            output.append(test_line[:-1])
    for line in output:
        if line:
            final_output.append(line)
    return final_output


def string_line_text(string, max_line_char_len, prepend="", append="\n"):
    return f"{append}".join([prepend+line for line in array_line_text(string, max_line_char_len)])


def get_temple_reroll_count(world_path):
    with open(world_path, encoding="utf-8") as world_xml:
        segment = world_xml.read().split("        key=\"TEMPLE_PERK_REROLL_COUNT\" ")
        if len(segment) >= 2:
            return int(segment[1].split("      </E>")[0].split("value=\"")[1].split("\" >")[0])
        return 0


def _recurse_tree(data, path):
    if len(path) == 0:
        return data
    path[0] = path[0].replace("$", "@")
    if isinstance(data, list):
        entries = []
        for item in data:
            result = _recurse_tree(item, path.copy())
            entries.append(result)
        if entries:
            return entries
    if isinstance(data, dict):
        if path[0] in data:
            if len(path) == 1:
                return data[path.pop(0)]
            return _recurse_tree(data[path.pop(0)], path)
    return None


def get_initial_xml_path(xml_path):
    try:
        with open(xml_path) as stats_xml:
            data = xmltodict.parse(stats_xml.read().replace("<managed by stringstore>", "managed by stringstore"))
    except:
        return {}
    for k in data.keys():
        return k
    return None


def get_any_xml_stat(player_xml_path, stat_grab_dict, init_filter=""):
    empty_stats = {}
    for k in stat_grab_dict.keys():
        empty_stats[k] = None
    try:
        with open(player_xml_path) as stats_xml:
            data = xmltodict.parse(stats_xml.read().replace("<managed by stringstore>", "managed by stringstore"))
    except:
        return empty_stats
    for k, v in stat_grab_dict.items():
        if k.startswith(init_filter):
            if not len(v) == 0:
                if "HIDDEN_" in v:
                    v.remove("HIDDEN_")
                try:
                    empty_stats[k] = _recurse_tree(data.copy(), v)
                except:
                    empty_stats[k] = None
            else:
                empty_stats[k] = ""
    return empty_stats


def list_is_table(var):
    if isinstance(var, list):
        if isinstance(var[0], dict):
            key_set = var[0].keys()
            same_keys = True
            for a_k in var:
                same_keys &= key_set == a_k.keys()
            return key_set
    return None


def nested_struct_to_string(xml_struct, prepend="", append_sign=""):
    if "," in xml_struct:
        xml_struct = ("\n"+prepend+"  "+xml_struct).split(",")
    if not isinstance(xml_struct, (list, dict)):
        return prepend+xml_struct+append_sign
    if isinstance(xml_struct, list):
        sub_str = ""
        key_set = list_is_table(xml_struct)
        if key_set:
            end_str = "\n"+prepend
            max_lens = {k: len(k)+1 for k in key_set}
            for entry in xml_struct:
                for sub_k, sub_v in entry.items():
                    new_len = len(f"{sub_v}") + 1
                    if sub_k not in max_lens:
                        max_lens[sub_k] = new_len
                    if new_len > max_lens[sub_k]:
                        max_lens[sub_k] = new_len
            for k in key_set:
                end_str += (k[1:].upper()+" " if k.startswith("@") or k.startswith("$") else k.upper())+(" " * (max_lens[k]-len(k)))
            end_str += "\n"
            for entry in xml_struct:
                table_block = ""
                for sub_k, sub_v in entry.items():
                    new_str = f"{sub_v}"
                    table_block += f"{new_str}{" " * (max_lens[sub_k] - len(new_str))}"
                    table_block = table_block[1:] if table_block.startswith("@") or table_block.startswith("$") else table_block
                end_str += prepend+table_block + "\n"
            return end_str
        for entry in xml_struct:
            sub_str += nested_struct_to_string(entry, prepend+"  ", append_sign) + "\n"
        return sub_str
    if isinstance(xml_struct, dict):
        sub_str = "\n"
        longest_key = max([len(k) for k in xml_struct.keys()])
        for key, value in xml_struct.items():
            if not value:
                value = ""
            out = nested_struct_to_string(value, prepend+"  ", append_sign)
            if out.replace(" ", ""):
                sub_str += f"{prepend}{key[1:] if key.startswith("@") or key.startswith("$") else key}:{" "*(longest_key-len(key))}{out}\n"
        return sub_str
    return ""


def get_player_stats(current_run_stats):
    grab = {'position.x=': None, 'position.y=': None, 'stats_filename=': None, 'wallet_money_target=': None,
            'hp=': None}
    with open(current_run_stats, encoding="utf-8") as stats_xml:
        for line in stats_xml.read().split("\n"):
            key = line.split("\"")[0].replace(" ", "")
            if key in grab.keys():
                key = line.split("\"")[0].replace(" ", "")
                grab[key] = line.split(key + "\"")[1].split("\" ")[0]
            if grab['stats_filename='] and grab['position.x='] and grab['position.y='] and grab['wallet_money_target='] and grab['hp=']:
                break
    return grab


def get_steam_noita_path():
    lib = None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        potential_lib_path = steam_path + "/steamapps/libraryfolders.vdf"
        if os.path.exists(potential_lib_path):
            lib = potential_lib_path
        else:
            int(":{")
    except:
        for path in os.listdir("C:/"):
            if os.path.isdir("C:/" + path):
                try:
                    sub_content = os.listdir("C:/" + path)
                    for st in ["Steam", "steam", "SteamLibrary"]:
                        if st in sub_content:
                            potential_lib_path = "C:/" + path + "/" + st + "/steamapps/libraryfolders.vdf"
                            if os.path.exists(potential_lib_path):
                                lib = potential_lib_path
                                break
                except:
                    pass
    result_path = None
    if lib:
        curr_save_path = lib.replace("/steamapps/libraryfolders.vdf", "")
        with open(lib, encoding="utf-8") as f:
            for line in f.read().split("\n"):
                if "\"path\"" in line:
                    curr_save_path = line.split("\"")[-2]
                if "\"881100\"" in line:
                    potential_data_path = curr_save_path + r"\steamapps\common\Noita\data\data.wak"
                    if os.path.exists(potential_data_path):
                        result_path = potential_data_path.replace(r"data\data.wak", "")
                        break
    return result_path


def get_gog_noita_path():
    result_path = None
    for path in os.listdir("C:/"):
        if os.path.isdir("C:/" + path):
            test_path = "C:/"+path+"/GOG Galaxy/Games/Noita/"
            if os.path.exists(test_path):
                return test_path
    return result_path


def is_good_noita_path(path):
    if path is None:
        return False
    if not os.path.exists(path):
        return False
    for element in [path + "noita.exe", path + r"data\data.wak", path + r"data\translations\common.csv"]:
        if not os.path.exists(element):
            return False
    return True


def get_noita_path():

    gog_path = get_gog_noita_path()
    if not is_good_noita_path(gog_path):
        gog_path = None
    steam_path = get_steam_noita_path()
    if not is_good_noita_path(steam_path):
        steam_path = None

    runner = None
    result_path = None
    if steam_path and not gog_path:
        result_path = steam_path
        runner = "steam://rungameid/881100"
    if not steam_path and gog_path:
        result_path = gog_path
        runner = gog_path+"noita.exe"

    if steam_path and gog_path:
        if notification(99, {"type": "ask", "title": "Two valid Noita instances!", "message": "Detected a Noita instance from GOG and from Steam!\n\nWhat path should we use?\n\nGOG: " + steam_path + "\n\nSTEAM: " + gog_path + "\n\nWould you like to use the GOG instance?\n(cancelling will automatically use the steam instance instead)"}):
            result_path = gog_path
            runner = gog_path+"noita.exe"
        else:
            result_path = steam_path
            runner = "steam://rungameid/881100"
    if not result_path:
        got_path = None
        if not notification(99, {"type": "ask", "title": "No Noita found", "message": "Could not find your noita.exe automatically...\nThis Application cannot proceed without thew noita.exe path!\nWould you like to set the path manually?"}):
            sys.exit(1)
        while not got_path:
            got_path = filedialog.askopenfilename(initialdir="", title=f"Noita path location...",
                                                  initialfile="noita.exe", defaultextension=".",
                                                  filetypes=[("All Files", f"noita.exe")])
            if got_path:
                got_path = got_path[:-9]
                if not is_good_noita_path(got_path):
                    got_path = None
            if not got_path:
                if not notification(99, {"type": "ask", "title": "No Noita found", "message": "Could not find your noita.exe automatically...\nThis Application cannot proceed without thew noita.exe path!\nWould you like to set the path manually?"}):
                    sys.exit(1)

        result_path = got_path
        runner = got_path + "noita.exe"

    if runner is None:
        runner = result_path + "noita.exe"
    return result_path, runner


def get_player_items(data):
    items = []

    for d in data["Entity"]["Entity"]:
        if "Entity" in d.keys():
            for sub_d in d["Entity"]:
                if not isinstance(sub_d, dict):
                    return
                if "MaterialInventoryComponent" in sub_d.keys():
                    if "ItemComponent" in sub_d.keys():
                        result_mats = []
                        img_path = sub_d["ItemComponent"]["@ui_sprite"]
                        if isinstance(sub_d["MaterialInventoryComponent"]["count_per_material_type"]["Material"], dict):
                            result_mats.append(
                                f"{int(math.ceil(int(sub_d["MaterialInventoryComponent"]["count_per_material_type"]["Material"]["@count"]) / (15 if img_path.endswith("material_pouch.png") else 10)))}% {sub_d["MaterialInventoryComponent"]["count_per_material_type"]["Material"]["@material"]}")
                        else:
                            for entry in sub_d["MaterialInventoryComponent"]["count_per_material_type"]["Material"]:
                                result_mats.append(
                                    f"{entry["@material"]} {int(math.ceil(int(entry["@count"]) / (15 if img_path.endswith("material_pouch.png") else 10)))}%")

                        items.append({"slot": int(sub_d["ItemComponent"]["@inventory_slot.x"]), "img_path": img_path,
                                      "text": result_mats})
                elif "PhysicsImageShapeComponent" in sub_d.keys():
                    items.append({"slot": int(sub_d["ItemComponent"]["@inventory_slot.x"]),
                                  "img_path": sub_d["PhysicsImageShapeComponent"]["@image_file"].replace(
                                      "data/items_gfx/", "data/ui_gfx/items/"), "text": ""})
    return items


def get_player_spells(data):
    spells = []
    for d in data["Entity"]["Entity"]:
        if "Entity" in d.keys():
            if isinstance(d["Entity"], list):
                for sub_d in d["Entity"]:
                    if sub_d["@tags"] == "card_action":
                        s_e = {"slot": sub_d["ItemComponent"]["@inventory_slot.x"],
                               "count": sub_d["ItemComponent"]["@uses_remaining"]}
                        sprites = []
                        for spell_sprite in sub_d["SpriteComponent"]:
                            sprites.append(spell_sprite["@image_file"])
                        s_e["sprites"] = [sprites[0], sprites[2]]
                        spells.append(s_e)
            else:
                s_e = {"slot": d["Entity"]["ItemComponent"]["@inventory_slot.x"],
                       "count": d["Entity"]["ItemComponent"]["@uses_remaining"]}
                sprites = []
                if isinstance(d["Entity"]["SpriteComponent"], list):
                    for spell_sprite in d["Entity"]["SpriteComponent"]:
                        sprites.append(spell_sprite["@image_file"])
                    s_e["sprites"] = [sprites[0], sprites[2]]
                else:
                    s_e["sprites"] = d["Entity"]["SpriteComponent"]["@image_file"]
                spells.append(s_e)
    return spells


def get_player_perks(data):
    perks = []
    perk_dict = {}
    for d in data["Entity"]["Entity"]:
        if isinstance(d, str):
            return perks
        if d["@tags"] == "perk_entity" or "greed_curse":
            if "UIIconComponent" in d.keys():
                perk_path = d["UIIconComponent"]["@icon_sprite_file"]
                if perk_path in perk_dict.keys():
                    perk_dict[perk_path]["count"] += 1
                else:
                    perk_dict[perk_path] = {"name": d["UIIconComponent"]["@name"].replace("$perk_", ""),
                                            "img_path": d["UIIconComponent"]["@icon_sprite_file"], "count": 1}
    for perk in perk_dict.values():
        perks.append(perk)
    return perks


def get_png_from_xml_path(xml_for_sprite):
    data = get_asset_xml(xml_for_sprite)
    new_path = data["Sprite"]["@filename"][5:]
    if new_path.endswith(".png"):
        return new_path
    return get_png_from_xml_path(new_path)


def get_xml_dict_wand_struct(xml_dict):
    wand_sprite = xml_dict["AbilityComponent"]["@sprite_file"]
    if wand_sprite.startswith("data/"):
        wand_sprite = wand_sprite[5:]

    wand_animation = None

    if wand_sprite.endswith(".xml"):
        wand_animation = get_asset_xml(wand_sprite)
        wand_sprite = get_png_from_xml_path(wand_sprite)

    if wand_animation:
        if wand_animation["Sprite"]["RectAnimation"]["@loop"] == "1" and not wand_animation["Sprite"]["RectAnimation"]["@frame_count"] == "0":
            wand_animation = wand_animation["Sprite"]["RectAnimation"]
        else:
            wand_animation = None

    if wand_animation:
        wand_sprites = {"img": slice_image(get_asset_image(wand_sprite.replace(".xml", ".png")),
                                           [int(wand_animation["@frame_width"]),
                                            int(wand_animation["@frame_height"]) + 1,
                                            int(wand_animation["@frame_count"])]),
                        "wait": max(1, int(float(wand_animation["@frame_wait"]) * 600))}
    else:
        wand_sprites = {"img": [get_asset_image(wand_sprite.replace(".xml", ".png"))], "wait": 0}
    wand_stats = {"Shuffle": ["No", "Yes"][int(xml_dict["AbilityComponent"]["gun_config"]["@shuffle_deck_when_empty"])],
                  "Spells/Cast": xml_dict["AbilityComponent"]["gun_config"]["@actions_per_round"],
                  "Cast delay": f"{int(xml_dict["AbilityComponent"]["gunaction_config"]["@fire_rate_wait"]) / 60:.2f} s",
                  "Rechrg. Time": f"{int(xml_dict["AbilityComponent"]["gun_config"]["@reload_time"]) / 60:.2f} s",
                  "Mana max": int(math.floor(float(xml_dict["AbilityComponent"]["@mana_max"]))),
                  "Mana chg. Spd": xml_dict["AbilityComponent"]["@mana_charge_speed"],
                  "Capacity": int(xml_dict["AbilityComponent"]["gun_config"]["@deck_capacity"]),
                  "Spread": f"{float(xml_dict["AbilityComponent"]["gunaction_config"]["@spread_degrees"]):.1f} DEG"}
    sprite_paths = []
    spell_always_casts = []
    spell_charge = []
    sprite_idx = []
    real_dict = [xml_dict["Entity"]]
    if isinstance(xml_dict["Entity"], list):
        real_dict = xml_dict["Entity"]
    always_sprites = []
    for card in real_dict:
        if "card_action" in card["@tags"]:
            new_always = int(card["ItemComponent"]["@permanently_attached"])
            spell_always_casts.append(new_always)
            idx = int(card["ItemComponent"]["@inventory_slot.x"])

            if not new_always:
                spell_charge.append(int(card["ItemComponent"]["@uses_remaining"]))
                if idx == 0:
                    sprite_idx.append(len(sprite_idx))
                else:
                    sprite_idx.append(idx)

            r_card = [card["SpriteComponent"]]
            if isinstance(card["SpriteComponent"], list):
                r_card = card["SpriteComponent"]
            for spell in r_card:
                if new_always:
                    always_sprites.append(spell["@image_file"].replace("data/", ""))
                else:
                    sprite_paths.append(spell["@image_file"].replace("data/", ""))
    wand_stats["Capacity"] -= sum(spell_always_casts)
    return wand_stats, wand_sprites, list(zip(sprite_paths[0::3], sprite_paths[2::3])), spell_charge, sprite_idx, list(
        zip(always_sprites[0::3], always_sprites[2::3]))


def get_player_wands(data):
    wands = []
    for d in data["Entity"]["Entity"]:
        if isinstance(d, str):
            return wands
        if "Entity" in d.keys():
            real_d = [d["Entity"]]
            if isinstance(d["Entity"], list):
                real_d = d["Entity"]
            for sub_d in real_d:
                if ("wand" in sub_d["@tags"] or "custom_wand" in sub_d["@tags"]) and "broken_wand" not in sub_d["@tags"]:
                    wands.append(get_xml_dict_wand_struct(sub_d))
            else:
                if "wand" in d["@tags"] or "custom_wand" in d["@tags"]:
                    wands.append(get_xml_dict_wand_struct(d["Entity"]))
    return wands


def get_player_xml_info(player_xml_path, stat_type=None):
    with open(player_xml_path) as f:
        data = xmltodict.parse(f.read())

    info = {
        "wands": get_player_wands,
        "perks": get_player_perks,
        "items": get_player_items,  # not working
        "spells": get_player_spells  # not working
    }
    if stat_type:
        return info[stat_type](data)
    all_info = {}
    for k, v in info.items():
        all_info[k] = v(data)
    return all_info


def get_wand_structure(path):
    with open(path) as f:
        stats_dict, wand_sprite, spell_img_paths, spell_charge, sprite_idx, always_cast_instructions = get_xml_dict_wand_struct(
            xmltodict.parse(f.read())["Entity"])
    stats_dict["Time Mod"] = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d/%m/%Y")

    return stats_dict, wand_sprite, spell_img_paths, spell_charge, sprite_idx, always_cast_instructions


def get_asset_xml(path):
    if path.startswith("mods/") and len(MOD_NAME_TO_ID) >= 1:
        mod_name = path.split("/")[1]
        if mod_name in MOD_NAME_TO_ID.keys():
            file_path = MOD_NAME_TO_ID[mod_name]["path"] + path.split(mod_name)[-1]
            if os.path.exists(file_path):
                with open(file_path) as f:
                    return xmltodict.parse(f.read())
    for mod_key, data in MOD_NAME_TO_ID.items():
        if data["enabled"]:
            mod_img_path = data["path"] + "/data/" + path
            if os.path.exists(mod_img_path):
                with open(mod_img_path) as f:
                    return xmltodict.parse(f.read())
    try:
        return xmltodict.parse(WAK.open(path))
    except:
        return None


def get_asset_image(path):
    if isinstance(path, (list, tuple)):
        path = path[0]
    if path.startswith("mods/") and len(MOD_NAME_TO_ID) >= 1:
        mod_name = path.split("/")[1]
        if mod_name in MOD_NAME_TO_ID.keys():
            mod_img_path = MOD_NAME_TO_ID[mod_name]["path"] + path.split(mod_name)[-1]
            if os.path.exists(mod_img_path):
                data = Image.open(mod_img_path)
                return data
    for mod_key, data in MOD_NAME_TO_ID.items():
        if data["enabled"]:
            mod_img_path = data["path"] + "/data/" + path
            if os.path.exists(mod_img_path):
                data = Image.open(mod_img_path)
                return data
    try:
        return WAK.open(path)
    except:
        if INVENTORY_SPRITE:
            return INVENTORY_SPRITE["ui_gfx/gun_actions/_unidentified.png"]
        else:
            return None


def create_wand_stats_images(abs_path, parent_image):
    global ICON_IMAGE
    global EMPTY_PNG
    EMPTY_PNG = Image.open(abs_path + "/assets/image/empty.png")
    parent_image.update()
    parent_image.update_idletasks()
    ICON_IMAGE = parent_image

    global WAND_STATS_ICON
    if WAND_STATS_ICON:
        for k, v in WAND_STATS_ICON.items():
            WAND_STATS_ICON[k] = ImageTk.PhotoImage(v.resize((25, 25), Image.Resampling.NEAREST).convert("RGBA"))
    global INVENTORY_SPRITE
    if INVENTORY_SPRITE:
        for k in INVENTORY_SPRITE:
            INVENTORY_SPRITE[k] = get_asset_image(k).resize(
                (80, 80),
                Image.Resampling.NEAREST
            ).convert("RGBA")
    for p_g in PLAYER_GHOST_SLICES.keys():
        PLAYER_GHOST_SLICES[p_g] = slice_mina(p_g, WAK.open("enemies_gfx/" + p_g + ".png").convert("RGBA"), [12, 19, 6] if p_g == "player" else [13, 19, 6])
    for p_g in FANCY_PLAYER_DRIP.keys():
        xml_file = FANCY_PLAYER_DRIP[p_g][0]
        out_slices = []
        pics, offset = slice_xml_image(xmltodict.parse(WAK.open(xml_file)))
        for pic in pics:
            size = (min(pic.width * 10, 160), min(pic.height * 10, 200))
            out_slices.append(pic.resize(size, Image.Resampling.NEAREST))
        FANCY_PLAYER_DRIP[p_g] = out_slices, [offset[0]*10, offset[1]*10]


def _get_retro_font_family():
    preferred = [
        "Terminal",
        "Lucida Console",
        "Consolas",
        "Courier New"
    ]

    available = set(font.families())

    for f in preferred:
        if f in available:
            return f
    return "TkDefaultFont"


def set_retro_font_family():
    global DEFAULT_FONT_STYLE
    DEFAULT_FONT_STYLE = _get_retro_font_family()


def get_themes():
    themes = {}
    for style_path in os.listdir(CONFIG_PATH + "/style"):
        try:
            with open(CONFIG_PATH + "/style/" + style_path) as f:
                style_conf = json.load(f)
                themes[style_path.replace(".json", "")] = style_conf
                f.close()
        except:
            pass
    if len(themes) >= 1:
        return themes
    return DEFAULT_THEMES


def make_default_themes():
    if not os.path.exists(CONFIG_PATH + "/style"):
        os.mkdir(CONFIG_PATH + "/style")
    default_theme = {}
    for default_theme in DEFAULT_THEMES:
        if f"/style/{default_theme["name"]}.json" == "/style/custom.json" or not os.path.exists(CONFIG_PATH + f"/style/{default_theme["name"]}.json"):
            with open(CONFIG_PATH + f"/style/{default_theme["name"]}.json", "w") as f:
                json.dump(default_theme, f, indent=4)
    return default_theme


def wand_to_simulator_link(stats, spell_sprites, spell_index):
    spell_starter = "%2C"
    spell_string = ""
    spell_idx = 0
    for idx in range(stats["Capacity"]):
        if idx in spell_index:
            try:
                spell_paths = spell_sprites[spell_idx]
            except:
                try:
                    spell_paths = spell_sprites[0]
                except:
                    spell_paths = "", "ui_gfx/inventory/inventory_box_inactive_overlay.png"
            spell_name = spell_paths[0].split("/")[-1].replace(".png", "").upper()

            if spell_name in TRANSLATIONS["action_"].keys():
                spell_name = TRANSLATIONS["action_"][spell_name]
            if spell_name in IMG_PATH_TO_NAME.keys():
                spell_name = IMG_PATH_TO_NAME[spell_name]
            spell_name = spell_name.replace("spitter_green", "Spitter Tier 2").replace("spitter_purple",
                                                                                       "Spitter Tier 3").replace(
                "_timer", "_TIMER")
            spell_string += spell_name
            spell_idx += 1
        spell_string += spell_starter

    return f"https://tinker-with-wands-online.vercel.app/?d={float(stats["Cast delay"].replace(" s", "")) * 60.0}&m={stats["Mana max"]}&c={stats["Mana chg. Spd"]}&q={stats["Spread"].replace(" DEG", "")}&n=&p=some_wand.png&v=1&a={stats['Spells/Cast']}&x={"0" if stats["Shuffle"] == "No" else "1"}&r={float(stats["Rechrg. Time"].replace(" s", "")) * 60.0}&l={stats["Capacity"]}&s=" + spell_string


def basic_wand_picture(stats, wand_sprite, spell_sprites, spell_index):
    combined_empty = Image.alpha_composite(INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"],
                                           INVENTORY_SPRITE["ui_gfx/inventory/inventory_box_inactive_overlay.png"])
    w_s = wand_sprite["img"][0].convert("RGBA")
    wand_size = min(500, w_s.width * 10), min(300, w_s.height * 10)
    wand = w_s.resize(wand_size, Image.Resampling.NEAREST)

    spell_len = 13
    spell_area_width = min(spell_len, max(len(spell_sprites), 6))
    image_width = (80 * spell_area_width) + 20
    image_height = (80 * int(math.ceil(len(spell_sprites) / spell_area_width))) + wand_size[1] + 40
    transparent_img = Image.new("RGBA", (image_width - 2, image_height - 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(transparent_img)
    img_font = ImageFont.truetype(image_font(), 17)
    draw.rectangle((0, 0, image_width - 6, 2), fill=(148, 128, 100, 255))
    draw.rectangle((0, 0, 2, image_height - 6), fill=(148, 128, 100, 255))
    draw.rectangle((image_width - 5, 3, image_width - 3, image_height - 3), fill=(148, 128, 100, 255))
    draw.rectangle((3, image_height - 5, image_width - 5, image_height - 3), fill=(148, 128, 100, 255))

    draw.rectangle((0, 0, 2, 2), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 5, image_height - 5, image_width - 3, image_height - 3), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 8, 0, image_width - 6, 2), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 5, 3, image_width, 5), fill=(180, 159, 129, 255))
    draw.rectangle((0, image_height - 8, 2, image_height - 6), fill=(180, 159, 129, 255))
    draw.rectangle((3, image_height - 5, 5, image_height), fill=(180, 159, 129, 255))

    transparent_img.paste(wand, (10, 20), wand)

    transparent_img.paste(WAND_STATS_ICON_PICTURE["Shuffle"], (wand_size[0] + 18, 20 + int((wand_size[1]/5))),
                          WAND_STATS_ICON_PICTURE["Shuffle"])
    draw.text((wand_size[0] + 50, 20 + (wand_size[1]/5)), "Shuffle", font=img_font, fill=(255, 255, 255, 255))
    draw.text((wand_size[0] + 190, 20 + (wand_size[1]/5)), str(stats["Shuffle"]), font=img_font, fill=(255, 255, 255, 255))

    transparent_img.paste(WAND_STATS_ICON_PICTURE["Spells/Cast"], (wand_size[0] + 18, 20 + int((wand_size[1]/5)*3)),
                          WAND_STATS_ICON_PICTURE["Spells/Cast"])
    draw.text((wand_size[0] + 50, 20 + ((wand_size[1]/5)*3)), "Spells/Cast", font=img_font, fill=(255, 255, 255, 255))
    draw.text((wand_size[0] + 190, 20 + ((wand_size[1]/5)*3)), str(stats["Spells/Cast"]), font=img_font, fill=(255, 255, 255, 255))

    spell_idx = 0
    for idx in range(stats["Capacity"]):
        if idx in spell_index:
            try:
                spell_paths = spell_sprites[spell_idx]
            except:
                try:
                    spell_paths = spell_sprites[0]
                except:
                    spell_paths = "ui_gfx/gun_actions/_unidentified.png", "ui_gfx/inventory/inventory_box_inactive_overlay.png"

            small = get_asset_image(spell_paths[0]).resize((60, 60), Image.Resampling.NEAREST).convert("RGBA")
            if spell_paths[1] == spell_paths[0]:
                photo = combined_empty.copy()
                photo.paste(small, (10, 10), small)
            else:
                big = get_asset_image(spell_paths[1]).resize((80, 80), Image.Resampling.NEAREST).convert("RGBA")
                photo = Image.alpha_composite(INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"], big)
                photo.paste(small, (10, 10), small)

            transparent_img.paste(photo, (10 + (80 * int(spell_idx % spell_area_width)),
                                          wand_size[1] + 30 + (80 * int(spell_idx // spell_area_width))), photo)

            spell_idx += 1
    return transparent_img


def one_to_one_wand_picture(stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites):
    combined_empty = Image.alpha_composite(INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"],
                                           INVENTORY_SPRITE["ui_gfx/inventory/inventory_box_inactive_overlay.png"])
    w_s = wand_sprite["img"][0].convert("RGBA").transpose(Image.Transpose.ROTATE_90)
    wand_size = min(145, w_s.width * 10), min(280, w_s.height * 10)
    wand = w_s.resize(wand_size, Image.Resampling.NEAREST)

    spell_area_width = 5 + (int((len(always_cast_sprites) + 3) // 3) if len(always_cast_sprites) > 0 else 0)
    image_width = (80 * spell_area_width) + 20
    image_height = (80 * int(math.ceil((stats["Capacity"]) / spell_area_width))) + 300
    transparent_img = Image.new("RGBA", (image_width - 2, image_height - 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(transparent_img)
    img_font = ImageFont.truetype(image_font(), 17)
    draw.rectangle((0, 0, image_width - 6, 2), fill=(148, 128, 100, 255))
    draw.rectangle((0, 0, 2, image_height - 6), fill=(148, 128, 100, 255))
    draw.rectangle((image_width - 5, 3, image_width - 3, image_height - 3), fill=(148, 128, 100, 255))
    draw.rectangle((3, image_height - 5, image_width - 5, image_height - 3), fill=(148, 128, 100, 255))

    draw.rectangle((0, 0, 2, 2), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 5, image_height - 5, image_width - 3, image_height - 3), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 8, 0, image_width - 6, 2), fill=(180, 159, 129, 255))
    draw.rectangle((image_width - 5, 3, image_width, 5), fill=(180, 159, 129, 255))
    draw.rectangle((0, image_height - 8, 2, image_height - 6), fill=(180, 159, 129, 255))
    draw.rectangle((3, image_height - 5, 5, image_height), fill=(180, 159, 129, 255))

    idx = 0
    if "Time Mod" in stats:
        stats.pop("Time Mod")
    for k, v in stats.items():
        transparent_img.paste(WAND_STATS_ICON_PICTURE[k], (18, 12 + (35 * idx)), WAND_STATS_ICON_PICTURE[k])
        draw.text((50, 14 + (35 * idx)), k, font=img_font, fill=(255, 255, 255, 255))
        draw.text((190, 14 + (35 * idx)), str(v), font=img_font, fill=(255, 255, 255, 255))
        idx += 1

    transparent_img.paste(wand, (int(332 - wand_size[0] // 2), int(140 - wand_size[1] / 2)), wand)

    spell_idx = 0
    for idx in range(stats["Capacity"]):
        if idx in spell_index:
            try:
                spell_paths = spell_sprites[spell_idx]
            except:
                try:
                    spell_paths = spell_sprites[0]
                except:
                    spell_paths = "ui_gfx/gun_actions/_unidentified.png", "ui_gfx/inventory/inventory_box_inactive_overlay.png"
            small = get_asset_image(spell_paths[0]).resize((60, 60), Image.Resampling.NEAREST).convert("RGBA")
            if spell_paths[1] == spell_paths[0]:
                photo = combined_empty.copy()
                photo.paste(small, (10, 10), small)
            else:
                big = get_asset_image(spell_paths[1]).resize((80, 80), Image.Resampling.NEAREST).convert("RGBA")
                photo = Image.alpha_composite(INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"], big)
                photo.paste(small, (10, 10), small)

            transparent_img.paste(photo,
                                  (10 + (80 * int(idx % spell_area_width)), 290 + (80 * int(idx // spell_area_width))),
                                  photo)

            charge = charges[spell_idx]
            if charge >= 0:
                draw.text((20 + (80 * int(idx % spell_area_width)), 300 + (80 * int(idx // spell_area_width))),
                          str(charge), font=img_font, fill=(255, 255, 255, 255))
            spell_idx += 1
        else:
            transparent_img.paste(combined_empty,
                                  (10 + (80 * int(idx % spell_area_width)), 290 + (80 * int(idx // spell_area_width))),
                                  combined_empty)
    if len(always_cast_sprites) > 0:
        photo = get_asset_image("ui_gfx/inventory/icon_gun_permanent_actions.png").resize((50, 50),
                                                                                          Image.Resampling.NEAREST).convert(
            "RGBA")
        transparent_img.paste(photo, (425, 20), photo)
        idx = 1
        for spell_entry in always_cast_sprites:
            try:
                spell, bg = spell_entry
                spell_paths = [spell, bg]
            except:
                try:
                    spell = spell_entry
                    bg = "ui_gfx/inventory/inventory_box_inactive_overlay.png"
                    spell_paths = [spell, bg]
                except:
                    spell_paths = "ui_gfx/gun_actions/_unidentified.png", "ui_gfx/inventory/inventory_box_inactive_overlay.png"
            small = get_asset_image(spell_paths[0]).resize((50, 50), Image.Resampling.NEAREST).convert(
                "RGBA")
            big = get_asset_image(spell_paths[1]).resize((80, 80), Image.Resampling.NEAREST).convert(
                "RGBA")
            photo = Image.alpha_composite(INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"], big)
            photo.paste(small, (14, 15), small)
            transparent_img.paste(photo, (410 + (80 * int(idx // 3)), 10 + (80 * int(idx % 3))), photo)
            idx += 1

    return transparent_img


def image_font():
    if USE_NOITA_FONT:
        return HOME_PATH + "/assets/font/NoitaPixel.ttf"

    ttf_files = [f for f in os.listdir(r"C:\Windows\Fonts") if f.lower().endswith(".ttf")]

    for pref in ["terminal", "consola", "cour", "perfectdos", "vga", "pxplus", "fixedsys"]:
        for f in ttf_files:
            if pref in f.lower():
                return f"C:/Windows/Fonts/{f}"

    return r"C:\Windows\Fonts\arial.ttf"


def pause(sec):
    sleep(sec)


def get_time():
    return time()


def get_random_enough_int(max_rand_val):
    return rng(0, max_rand_val-1)


def get_random_enough_element(element):
    return element[get_random_enough_int(len(element))]


def fill_all_xml_args(world_path, conf, bare_stats=False):
    player_path = world_path + "/Nolla_Games_Noita/save00/player.xml"
    is_bare = bare_stats
    if os.path.exists(player_path):
        player_stats = get_any_xml_stat(player_path, conf, "player_")
    else:
        latest_stats = get_newest_session_file(world_path + "/Nolla_Games_Noita/save00/stats/sessions/")
        player_stats = {k: None for k in conf.keys()}
        player_stats["player_HIDDEN_stats_file"] = latest_stats
        player_stats["Playtime_APPEND_s"] = ""
        player_stats["player_Health"] = ""
        is_bare = True
    player_kills_path = world_path + "/Nolla_Games_Noita/save00/stats/sessions/" + player_stats["player_HIDDEN_stats_file"].replace("??STA/sessions/", "")
    for path in [player_kills_path.replace("_kills", "_stats"),
                 player_kills_path,
                 world_path + "/Nolla_Games_Noita/save00/streaming_event_config.xml",
                 world_path + "/Nolla_Games_Noita/save00/world_state.xml",
                 world_path + "/Nolla_Games_Noita/save00/mod_config.xml"]:
        filter_name = path.split("/")[-1].replace(".xml", "")
        if filter_name.endswith("_stats"):
            filter_name = "stats"
        if filter_name.endswith("_kills"):
            filter_name = "kills"
        if os.path.exists(path):
            for k, v in get_any_xml_stat(path, conf, filter_name + "_").items():
                if k not in player_stats.keys():
                    player_stats[k] = {}
                elif not player_stats[k]:
                    player_stats[k] = v
    if "" in player_stats.keys():
        player_stats.pop("")
    if not is_bare:
        if player_stats.get("player_Health", -0.04):
            player_stats["player_Health"] = get_formatted_int(
                int(math.floor(float(player_stats["player_Health"]) * 25)))
        if player_stats.get("player_Current Balance_APPEND_ $", 0.0) and player_stats.get("player_Money spent_APPEND_ $", 0.0):
            try:
                col = int(float(player_stats["player_Current Balance_APPEND_ $"]))
                spent = int(float(player_stats["player_Money spent_APPEND_ $"]))
            except:
                col = 0
                spent = 0
            player_stats["Money collected_APPEND_ $"] = get_formatted_int(col + spent)
            player_stats["player_Money spent_APPEND_ $"] = get_formatted_int(spent)
            player_stats["player_Current Balance_APPEND_ $"] = get_formatted_int(col)
    return player_stats


def noita_world_was_modded(world_path):
    xml_world_path = world_path + "/Nolla_Games_Noita/save00/world_state.xml"
    if os.path.exists(xml_world_path):
        try:
            with open(xml_world_path) as f:
                data = xmltodict.parse(f.read())
                return data["Entity"]["WorldStateComponent"].get("@mods_have_been_active_during_this_run", "0") == "1"
        except:
            return None
    return None


def mouse_is_over_widget(widget):
    x, y = widget.winfo_pointerxy()
    target = widget.winfo_containing(x, y)
    while target:
        if target == widget:
            return True
        target = target.master
    return False


def tk_font(size):
    return DEFAULT_FONT_STYLE, size if isinstance(size, int) else FONT_TYPE[size]


class NoitaWak:
    def __init__(self, wak_path):
        self.fp = ""
        self.index = {}
        self._has_data = False
        if os.path.exists(wak_path):
            self.fp = open(wak_path, "rb")
            self.index = {}
            self._has_data = self._set_indices()

    def _set_indices(self):
        waky_file = self.fp

        pos = waky_file.read(1024).find(b"data/")
        if pos == -1:
            return False

        waky_file.seek(pos - 8)
        size = struct.unpack("<I", waky_file.read(4))[0]
        while True:
            data = waky_file.read(4)
            if len(data) < 4: break

            path_len = struct.unpack("<I", data)[0]
            if path_len == 0 or path_len > 300: break

            path = waky_file.read(path_len).decode("utf-8")
            offset = struct.unpack("<I", waky_file.read(4))[0]
            self.index[path[5:]] = (offset - 1 - size, size)
            size = struct.unpack("<I", waky_file.read(4))[0]
        return True

    def has_data(self):
        return self._has_data

    def listdir(self, root_dir):
        if root_dir.startswith("data/"):
            root_dir = root_dir[5:]
        if not root_dir.endswith("/"):
            root_dir += "/"
        result_dirs = []
        if not self._has_data:
            return result_dirs
        for i in self.index.keys():
            if i.startswith(root_dir):
                test_string = i.replace(root_dir, "")
                if len(test_string.split("/")) == 1:
                    result_dirs.append(i)
        return result_dirs

    def exists(self, path):
        if path.startswith("data/"):
            path = path[5:]
        if self._has_data:
            return path in self.index.keys()
        return False

    def open(self, path):
        if path.startswith("data/"):
            path = path[5:]
        if not self.exists(path):
            raise FileNotFoundError

        offset, size = self.index[path]
        self.fp.seek(offset)
        raw = self.fp.read(size)

        if path.endswith(".png"):
            return Image.open(io.BytesIO(raw))
        else:
            return raw.decode()


"""
INIT CONFIG
"""
config = {}
if not os.path.exists(CONFIG_PATH):
    os.mkdir(CONFIG_PATH)
if not os.path.exists(CONFIG_PATH + "/style"):
    os.mkdir(CONFIG_PATH + "/style")
if not os.path.exists(CONFIG_PATH + "/data.json"):
    with open(CONFIG_PATH + "/data.json", "w") as f:
        json.dump({"world_paths": []}, f, indent=4)


FONT_TYPE = {"Hl": -32, "Hm": -26, "Hs": -22,
             "Tl": -18, "Tm": -15, "Ts": -12}
DEFAULT_FONT_STYLE = "TkDefaultFont"

NOTIFICATION_THRESHOLD = 0

PLAYER_GHOST_SLICES = {"player": None, "playerghost": None}
FANCY_PLAYER_DRIP = {"crown": ["enemies_gfx/player_hat2.xml", (0, 0)],
                     "amulet": ["enemies_gfx/player_amulet.xml", (0, 0)],
                     "unearned___probably": ["enemies_gfx/player_amulet_gem.xml", (0, 0)]}
FANCY_IMG_PATHS = {"crown": "data/enemies_gfx/player_hat2.xml",
                   "amulet": "data/enemies_gfx/player_amulet.xml",
                   "unearned___probably": "data/enemies_gfx/player_amulet_gem.xml"}

USE_NOITA_FONT = True
CURRENT_WORLD_PATH = None
MOD_NAME_TO_ID = {}
ICON_IMAGE = None

NOITA_PATH = None
RUNNER_ARG = None
with open(CONFIG_PATH + "/data.json") as f:
    try:
        config = json.load(f)
        if config.get("game", None):
            NOITA_PATH = config["game"].get("noita_path", None)
            RUNNER_ARG = config["game"].get("noita_runner_arg", None)
    except Exception as e:
        config = None

valid_path = NOITA_PATH is not None
if valid_path:
    valid_path = os.path.exists(NOITA_PATH)

if not valid_path:
    NOITA_PATH, RUNNER_ARG = get_noita_path()
    if config:
        if config.get("game", None):
            config["game"]["noita_path"] = NOITA_PATH
            config["game"]["noita_runner_arg"] = RUNNER_ARG

WAK = NoitaWak(NOITA_PATH + "data/data.wak")

DEFAULT_THEMES = [{"name": "win-xp", "type": "light", "font": "Terminal",
                   "colors": {"primary": "#919191", "secondary": "#ABABAB", "success": "#4ABD1C", "info": "#4647BA",
                              "warning": "#DD972D", "danger": "#E9206A", "light": "#FFFFFF", "dark": "#999999",
                              "bg": "#C4C4C4", "fg": "#666666", "selectbg": "#555555", "selectfg": "#FFFFFF",
                              "border": "#000000", "inputfg": "#FFFFFF", "inputbg": "#AAAAAA", "active": "#1F1F1F"}},
                  {"name": "custom", "type": "dark", "font": "Terminal",
                   "colors": {"primary": "#ffff00", "secondary": "#00ffff", "success": "#00ff00", "info": "#0000ff",
                              "warning": "#ff9400", "danger": "#ff0000", "light": "#ffffff", "dark": "#000000",
                              "bg": "#000000", "fg": "#FFFFFF", "selectbg": "#444444", "selectfg": "#666666",
                              "border": "#222222", "inputfg": "#FFFFFF", "inputbg": "#ff00ff", "active": "#1F1F1F"}},
                  {"name": "dark", "type": "dark", "font": "Terminal",
                   "colors": {"primary": "#2A9FD6", "secondary": "#555555", "success": "#77B300", "info": "#9933CC",
                              "warning": "#FF8800", "danger": "#CC0000", "light": "#ADAFAE", "dark": "#222222",
                              "bg": "#1E1F1F", "fg": "#FFFFFF", "selectbg": "#555555", "selectfg": "#FFFFFF",
                              "border": "#222222", "inputfg": "#FFFFFF", "inputbg": "#2A2A2A", "active": "#1F1F1F"}}]

EMPTY_PNG = None

INVENTORY_SPRITE = {
    "ui_gfx/inventory/inventory_box.png": None,
    "ui_gfx/inventory/inventory_box_inactive_overlay.png": None,
    "ui_gfx/gun_actions/_unidentified.png": None, "ui_gfx/inventory/icon_warning.png": None,
    "ui_gfx/inventory/icon_gun_permanent_actions.png": None
}
for I_key in INVENTORY_SPRITE.keys():
    INVENTORY_SPRITE[I_key] = get_asset_image(I_key)

WAND_STATS_DICT = {
    "Shuffle": "ui_gfx/inventory/icon_gun_shuffle.png",
    "Spells/Cast": "ui_gfx/inventory/icon_gun_actions_per_round.png",
    "Cast delay": "ui_gfx/inventory/icon_fire_rate_wait.png",
    "Rechrg. Time": "ui_gfx/inventory/icon_gun_reload_time.png",
    "Mana max": "ui_gfx/inventory/icon_mana_max.png",
    "Mana chg. Spd": "ui_gfx/inventory/icon_mana_charge_speed.png",
    "Capacity": "ui_gfx/inventory/icon_gun_capacity.png",
    "Spread": "ui_gfx/inventory/icon_spread_degrees.png"
}
WAND_STATS_ICON = {}
WAND_STATS_ICON_PICTURE = {}
for k, path in WAND_STATS_DICT.items():
    WAND_STATS_ICON[k] = get_asset_image(path)
    WAND_STATS_ICON_PICTURE[k] = get_asset_image(path).resize((20, 20), Image.Resampling.NEAREST).convert("RGBA")

WAND_NAME = ["wand"] * 80000 + ["wnad"] * 13000 + ["uwund"] * 4000 + ["HAI"] * 2998 + ["uwu", "0w0"]

TRANSLATIONS = {"action_": {}, "perk_": {}, "perkdesc_": {}}
if os.path.exists(NOITA_PATH + "data/translations/common.csv"):
    with open(NOITA_PATH + "data/translations/common.csv", encoding="utf8") as common:
        for common_key, common_val in {str(row[0]): row[1] for row in csv.reader(common)}.items():
            if "greed_curse_damage" == common_key:
                TRANSLATIONS["perk_"]["greed_curse"] = common_val
            if "logdesc_greed_curse" == common_key:
                TRANSLATIONS["perkdesc_"]["greed_curse"] = common_val
            for trans_key in TRANSLATIONS.keys():
                if common_key.startswith(trans_key):
                    TRANSLATIONS[trans_key][common_key.replace(trans_key, "")] = common_val

    TRANSLATIONS["action_"]["mana"] = "Add Mana"
    TRANSLATIONS["perk_"]["fungal_shift"] = "The reality has shifted"
    TRANSLATIONS["perkdesc_"]["fungal_shift"] = "You sense things are no longer what they used to be."

IMG_PATH_TO_NAME = {
    "fire_gas": "gas_fire", "peace_with_gods": "peace_with_steve",
    "oil_blood": "bleed_oil", "duplicate_projectile": "spell_duplication",
    "slime_blood": "bleed_slime", "bleed_slime": "reverse_slowdown",
    "mystery_eggplant": "food_clock", "no_player_knockback": "no_more_knockback",
    "black_hole_timer": "Black Hole Death trigger", "blood_punch": "Blood To Power",
    "burning_critical": "Critical on Burning", "clusterbomb": "UNSTABLE_GUNPOWDER",
    "critical_blood": "Critical On Bloody Enemies", "critical_oil": "Critical on Oiled Enemies",
    "critical_water": "Critical on Wet (Water) Enemies",
    "critical_wet": "Critical on Wet (Water) Enemies",
    "duck_2": "Flock of Ducks", "Duplicate": "Divide By",
    "explode_on_alcohol": "Explosion On Drunk Enemies",
    "explode_on_alcohol_giga": "Explosion On Drunk Enemies",
    "explode_on_slime": "Explosion On Slimy Enemies",
    "explode_on_slime_giga": "Explosion On Slimy Enemies",
    "golden_punch": "Gold To Power", "Penetrate Walls": "Drilling Shot",
    "Polymorph charge": "Muodonmuutos", "sheep": "Muodonmuutos",
    "timer": "Add Trigger", "worm": "Worm_Launcher", "death_trigger": "Add Trigger",
    "Commander bolt": "Orbit Larpa", "timer_trigger": "Add Trigger",
    "charm_on_toxic": "Charm On Toxic Sludge",
    "MANA": "MANA_REDUCE", "luminous_drill_TIMER": "LASER_LUMINOUS_DRILL",
    "LUMINOUS_DRILL_TIMER": "LASER_LUMINOUS_DRILL", "lance_holy": "Holy Lance"
}
