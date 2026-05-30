from PIL import Image, ImageTk, ImageSequence
from tkinter import Canvas
from ttkbootstrap.constants import *
import ttkbootstrap as tb
import tkinter as tk
import socketserver
import http.server
import functools
import threading
import math
import json
import os

if __name__ == "__main__":
    import Utils as Util
else:
    import src.Utils as Util


WORLD_BANNER_SEARCH_TERM = ""
SCROLL_FRAME_VISIBILITY = 1.0
PERFECT_WAND_PRINT = True
SCROLL_INTENSITY = 60
SCROLL_INVERTED = False
FORCE_FRAMES = 0
AUTO_SCROLL = True


class Swapper:
    def __init__(self, frame, config, end_command, single_select=None):

        self.single_select = single_select
        self.is_single_select = True if single_select else False
        self.finalize = end_command
        self.save_config = config
        self.frame_elements = frame.get_elements()
        self.element_frame = frame
        self.re_toggle(self.set_save)
        self.save_path_1 = None
        self.save_path_2 = None

    def re_toggle(self, command=None):

        f_e = self.element_frame.get_elements().copy()
        for i in f_e:
            if not isinstance(i, WorldBannerFrame):
                self.element_frame.after(500, lambda: self.re_toggle(command))
                return

        for i in self.frame_elements:
            if isinstance(i, WorldBannerFrame):
                i.toggle_selector(self.single_select, command)

    def set_save(self, save):
        if self.save_path_1 and self.save_path_2:
            return
        if self.save_path_1:
            if self.save_path_1 == save.world_path:
                return
            self.save_path_2 = save.world_path
            self.swap(self.save_config)
            return
        self.save_path_1 = save.world_path
        if self.single_select:
            self.single_select(save)
            self.finalize()
        return

    def swap(self, conf):

        if self.save_path_1 is None:
            return
        if self.save_path_2 is None:
            return
        if self.save_path_2 == self.save_path_1:
            return

        paths = [self.save_path_1, self.save_path_2]
        i = []
        for idx, path in enumerate(conf["world_paths"]):
            if path in paths:
                i.append(idx)
                if len(i) >= 2:
                    break

        conf["world_paths"][i[0]], conf["world_paths"][i[1]] = conf["world_paths"][i[1]], conf["world_paths"][i[0]]
        ma = len(self.element_frame.items)-1
        self.element_frame.swap_items(ma-i[0], ma-i[1])

        self.finalize()


class FrameFlowController:
    def __init__(self, fallback_key, fallback, pre_process=None):

        self.frame_index = -1
        self.pre_process_function = pre_process
        self.frame_list = []
        self.fallback_frame = fallback
        self.fallback_key = fallback_key

        self.is_frame_internal_call = False

        self.last_home_refresh = Util.get_time()

    def _frame_set_exists(self, k):
        i = 0
        leftovers = self.frame_list[:self.frame_index]
        for frame_entry in leftovers[::-1]:
            if i >= 2:
                return -1
            if frame_entry["key"] == k:
                return i
            i += 1
        return -1

    def pre_process(self):
        if self.pre_process_function:
            self.pre_process_function()

    def home(self):
        self.pre_process()
        new_time = Util.get_time()
        if new_time-self.last_home_refresh > 3:
            self.last_home_refresh = new_time
            self.frame_index = -1
            self.frame_list = []
            self.fallback_frame()

    def add_frame(self, key, frame):
        if not self.is_frame_internal_call:
            self.pre_process()
            prev_frame_index = self._frame_set_exists(key)
            if prev_frame_index < 0:
                self.frame_index += 1
                self.frame_list = self.frame_list[:self.frame_index]
                self.frame_list.append({"key": key, "frame": frame})
            else:
                self.frame_index -= prev_frame_index
                self.frame_list = self.frame_list[:self.frame_index+1]
                self.reload_frame()
        self.is_frame_internal_call = False

    def previous_frame(self):
        self.pre_process()
        if self.frame_index < 1:
            return
        self.frame_index -= 1
        if not self.frame_list[self.frame_index]["key"] == self.fallback_frame:
            self.reload_frame()

    def next_frame(self):
        self.pre_process()
        if len(self.frame_list) > self.frame_index+1:
            self.frame_index += 1
            self.reload_frame()

    def reload_frame(self):
        self.pre_process()
        self.is_frame_internal_call = True
        self.frame_list[self.frame_index]["frame"]()


class MutedHTTPServerHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format, *args): pass


class FooterFrame(tb.Frame):
    def __init__(self, parent, button_data, pad_x=50, pad_y=15, max_elements_per_row=0, **kwargs):
        super().__init__(parent, **kwargs)
        self.button_entry = {}
        if max_elements_per_row <= 0:
            max_elements_per_row = len(button_data)
        for i, e in enumerate(button_data):
            if e:
                identifier = e.get("id", e["name"]+e.get("style", "_"))
                if e.get("command", False):
                    self.button_entry[identifier] = tb.Button(self, text=e["name"], style=e["style"], command=e["command"])
                    self.button_entry[identifier].grid(row=i//max_elements_per_row, column=i % max_elements_per_row, pady=pad_y, padx=pad_x)
                else:
                    self.button_entry[identifier] = tb.Label(self, text=e["name"])
                    style = e.get("style", False)
                    if style:
                        self.button_entry[identifier].config(bootstyle=style)
                    self.button_entry[identifier].grid(row=i//max_elements_per_row, column=i % max_elements_per_row, pady=pad_y, padx=pad_x)


class ScrollSetElement(tb.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.is_scrollable = False
        self.canvas = None
        self.is_horizontal = False
        self.focus_widget = [self]
        self._has_been_set = False

    def reset_focus_frames(self):
        self.focus_widget = [self]
        self._has_been_set = False

    def set_focus_widget(self, new_widget):
        if self._has_been_set:
            self.focus_widget.append(new_widget)
            return
        self._has_been_set = True
        self.focus_widget = [new_widget]

    def get_focus_widget(self):
        return self.focus_widget

    def set_scroll(self, canvas, is_horizontal=False):
        self.is_scrollable = True
        self.canvas = canvas
        self.is_horizontal = is_horizontal

    def _disable_scroll(self):
        self.is_scrollable = False

    def use_scroll(self, event):
        if not self.is_scrollable or isinstance(event, ExtendedTkFrame):
            return False
        SCROLL_SPEED = SCROLL_INTENSITY * (-1.0 if SCROLL_INVERTED else 1.0)
        if event.num == 4:
            delta_pixels = -SCROLL_SPEED
        elif event.num == 5:
            delta_pixels = SCROLL_SPEED
        else:
            delta_pixels = (event.delta // 120) * -SCROLL_SPEED

        if self.is_horizontal:
            first, last = self.canvas.xview()
        else:
            first, last = self.canvas.yview()

        if first == 0.0 if (-event.delta if SCROLL_INVERTED else event.delta) > 0 else last == 1.0:
            return False

        bbox = self.canvas.bbox("all")
        if not bbox:
            return False

        scroll_depth = bbox[2 if self.is_horizontal else 3] - bbox[0 if self.is_horizontal else 1]
        if scroll_depth <= 0:
            return False

        if self.is_horizontal:
            self.canvas.xview_moveto(max(0, min(first + ((delta_pixels*2) / scroll_depth), 1)))
        else:
            self.canvas.yview_moveto(max(0, min(first + (delta_pixels / scroll_depth), 1)))
        return True


class ScrollSelectionText(ScrollSetElement):
    def __init__(self, parent, frame_size=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.can_scroll = True

        if frame_size:
            canvas = tb.Canvas(self, width=frame_size[0], height=frame_size[1])
        else:
            canvas = tb.Canvas(self, **kwargs)

        scrollbar = tb.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, pady=5, padx=2)

        self.scroll_text_trame = tb.Frame(canvas)
        canvas.create_window((0, 0), window=self.scroll_text_trame, anchor="nw")

        self.set_scroll(canvas)

        self.text_height = 6
        self.text = tb.Text(self.scroll_text_trame, width=53, height=self.text_height)
        self.text.config(wrap="word")
        self.text.bind("<KeyRelease>", self._update_text_height)
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.on_instantiation = 0
        self.text.pack()

    def _scroll_to_cursor(self):
        self.canvas.update_idletasks()
        if self.on_instantiation <= 2:
            self.on_instantiation += 1
            return
        bbox = self.text.bbox("insert")
        if not bbox:
            return
        _, y, _, height = bbox
        abs_y = self.text.winfo_y() + y

        scrollregion = self.canvas.bbox("all")
        if not scrollregion:
            return

        total_height = scrollregion[3]

        canvas_top = self.canvas.canvasy(0)
        canvas_height = self.canvas.winfo_height()
        canvas_bottom = canvas_top + canvas_height
        margin = 10
        if abs_y < canvas_top + margin:
            new_top = abs_y - margin
        elif abs_y + height > canvas_bottom - margin:
            new_top = abs_y + height - canvas_height + margin
        else:
            return
        fraction = new_top / total_height
        self.canvas.yview_moveto(fraction)

    def set_max_height(self, height):
        self.text_height = height
        self._update_text_height()

    def _update_text_height(self, event=None):
        self.text.update_idletasks()

        text = self.text.count("1.0", "end-1c", "displaylines")
        lines = text[0] if text else 0

        self.text.configure(height=min(max(self.text_height, lines), 500) + 1)

        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)
        self._scroll_to_cursor()

    def _on_text_modified(self, event=None):
        self.text.tk.call(self.text._w, 'edit', 'modified', 0)
        self._update_text_height()


class EntrySelector(ScrollSetElement):
    def __init__(self, master, entries, selected_index=None, title="Entry", extra_button=None, random_button=True, **kwargs):

        super().__init__(master, width=620, height=480, **kwargs)
        self.selected_gif_idx = 0
        if len(entries) == 0:
            return
        self.entries = entries
        if selected_index is None:
            self.selected_gif_idx = Util.get_random_enough_int(len(self.entries))
        else:
            self.selected_gif_idx = selected_index

        self.topper = tb.Frame(self)
        self.title = tb.Label(self.topper, text=f"{title}:", font=Util.tk_font("Tl"))
        self.title.grid(row=0, column=2, pady=0, padx=0)
        self.extra_data = tb.Label(self.topper, text=f"", font=Util.tk_font("Ts"))
        self.extra_data.grid(row=0, column=6, pady=1, padx=10)

        if len(entries) >= 2:
            if random_button:
                tb.Button(self.topper, text="<??>", style="dark", command=self.set_random_entry_index).grid(row=0, column=0, pady=1, padx=10)
            tb.Button(self.topper, text="<<", style="dark", command=self.backwards).grid(row=0, column=1, pady=1, padx=5)
            self.index_count_label = tb.Text(self.topper, font=Util.tk_font("Tl"), width=len(str(len(self.entries))), height=1)
            self.index_count_label.insert(tk.END, str(self.selected_gif_idx + 1))
            self.index_count_label.grid(row=0, column=3, pady=0, padx=0)
            self.index_count_label.bind("<Return>", lambda a: self.selected_new_index(a))
            tb.Label(self.topper, text=f"/{len(self.entries)}", font=Util.tk_font("Tl")).grid(row=0, column=4, pady=0, padx=0)
            tb.Button(self.topper, text=">>", style="dark", command=self.forward).grid(row=0, column=5, pady=1, padx=5)

        if extra_button:
            tb.Button(self.topper, text=extra_button["name"], style=extra_button["style"], command=extra_button["command"]).grid(row=0, column=7, pady=0, padx=5)

        self.topper.pack(anchor="n", padx=5, pady=5)
        self.master_frame = master

    def set_title(self, new_title):
        self.title.destroy()
        self.title = tb.Label(self.topper, text=f"{new_title}:", font=Util.tk_font("Tl"))
        self.title.grid(row=0, column=2, pady=0, padx=0)

    def selected_new_index(self, event):
        new_index = self.index_count_label.get("1.0", "end-1c").replace("\n", "")
        try:
            int_index = int(new_index)
            if int_index <= 0:
                int_index = 1
            if int_index > len(self.entries):
                int_index = len(self.entries)
            fin_idx = int_index - 1
            if fin_idx == self.selected_gif_idx:
                self.index_count_label.delete("1.0", "end")
                self.index_count_label.insert(tk.END, str(self.selected_gif_idx + 1))
                return "break"
            self.selected_gif_idx = fin_idx
            self._re_draw(self.entries[self.selected_gif_idx])
        except:
            pass
        self.index_count_label.delete("1.0", "end")
        self.index_count_label.insert(tk.END, str(self.selected_gif_idx + 1))
        return "break"

    def forward(self):
        old_idx = self.selected_gif_idx
        self.selected_gif_idx = (self.selected_gif_idx + 1) % len(self.entries)
        if old_idx == self.selected_gif_idx:
            return
        self._re_draw(self.entries[self.selected_gif_idx])

    def backwards(self):
        old_idx = self.selected_gif_idx
        self.selected_gif_idx -= 1
        if self.selected_gif_idx < 0:
            self.selected_gif_idx = len(self.entries) - 1
        if old_idx == self.selected_gif_idx:
            return
        self._re_draw(self.entries[self.selected_gif_idx])

    def set_random_entry_index(self):
        entry_len = len(self.entries)
        prev_idx = self.selected_gif_idx
        new_idx = Util.get_random_enough_int(entry_len)
        while new_idx == prev_idx and entry_len > 1:
            new_idx = Util.get_random_enough_int(entry_len)
        if not new_idx == prev_idx:
            self.selected_gif_idx = new_idx
            self._re_draw(self.entries[self.selected_gif_idx])

    def _re_draw(self, entry):
        self.index_count_label.delete("1.0", "end")
        self.index_count_label.insert(tk.END, str(self.selected_gif_idx + 1))

        self.re_draw(entry)

    def re_draw(self, entry):
        pass


class AnimatedGIF(EntrySelector):
    def __init__(self, master, gifs, **kwargs):

        self.gifs = gifs

        super().__init__(master, self.gifs, title="Recording", **kwargs)

        self.master_frame = master
        self.img = Image.open(self.gifs[self.selected_gif_idx])
        self.frames = [ImageTk.PhotoImage(f.resize((640, 360))) for f in ImageSequence.Iterator(self.img)]
        self.single_frame = len(self.frames) == 1
        if self.single_frame:
            self.set_title("Image")
        self.idx = 0

        self.base_delay = self.img.info.get("duration", 80)
        self.img.close()
        self.speed_var = tb.DoubleVar(value=1.0)

        def open_gif():
            if os.path.exists(self.gifs[self.selected_gif_idx]):
                os.startfile(self.gifs[self.selected_gif_idx])
            else:
                Util.notification(2, {"type": "warn", "title": "File not found", "message": "Specified file could not be found anymore..."})

        self.label = tb.Label(self)
        self.label.bind("<Double-Button-1>", lambda a: open_gif())
        self.label.pack(pady=2)

        self.panel = tb.Frame(self)
        self.panel.pack(fill="x", padx=5, pady=5)

        self.slider = tb.Scale(self.panel, from_=-0.26, to=2.25, style="success", orient="horizontal", variable=self.speed_var, length=650)
        self.bottom_buttons = tb.Frame(self.panel)
        self.pause_play = tb.Button(self.bottom_buttons, text="PAUSE", style="light-outline", command=self.toggle_play)
        self.forward_frame = tb.Button(self.bottom_buttons, text="NEXT FRAME", style="info-outline", command=self.next_frame)
        self.backward_frame = tb.Button(self.bottom_buttons, text="LAST FRAME", style="warning-outline", command=self.prev_frame)
        times_two = tb.Separator(self.bottom_buttons, orient='vertical', style='info.Vertical.TSeparator')
        mid_slider = tb.Separator(self.bottom_buttons, orient='vertical', style='success.Vertical.TSeparator')
        pause_slider = tb.Separator(self.bottom_buttons, orient='vertical', style='danger.Vertical.TSeparator')
        pause_slider.grid(row=0, column=0, pady=5, padx=55)
        self.backward_frame.grid(row=0, column=1, pady=5, padx=24)
        mid_slider.grid(row=0, column=2, pady=5, padx=23)
        self.pause_play.grid(row=0, column=2, pady=5, padx=18)
        self.pause_play.lift(mid_slider)
        self.forward_frame.grid(row=0, column=3, pady=5, padx=23)
        times_two.grid(row=0, column=4, pady=5, padx=53)
        self.backward_frame.config(state="disabled")
        self.forward_frame.config(state="disabled")
        self.is_paused = False
        if not self.single_frame:
            self.bottom_buttons.pack(pady=5)
            self.slider.pack()
            date = self.gifs[self.selected_gif_idx].split("-")[-4]
            y, m, d = date[:4], date[4:6], date[6:]
            self.extra_data.config(text=f"Date: {d}/{m}/{y}")
        self.animate()

    def next_frame(self):
        self.idx += 1
        self.idx = self.idx % len(self.frames)

    def prev_frame(self):
        self.idx -= 1
        if self.idx < 0:
            self.idx = len(self.frames) - 1

    def toggle_play(self):
        en_dis = "disabled" if self.is_paused else "enabled"
        self.pause_play.config(text="PAUSE" if self.is_paused else " PLAY  ")
        self.backward_frame.config(state=en_dis)
        self.forward_frame.config(state=en_dis)
        self.is_paused = not self.is_paused
        self.slider.config(state="dark" if self.is_paused else "success")

    def re_draw(self, path):
        if path is None:
            return
        if not os.path.exists(path):
            return
        self.speed_var = tb.DoubleVar(value=1.0)
        self.index_count_label.delete("1.0", "end")
        self.index_count_label.insert(tk.END, str(self.selected_gif_idx + 1))
        self.img = Image.open(self.gifs[self.selected_gif_idx])
        self.frames = [ImageTk.PhotoImage(f.copy().resize((640, 360))) for f in ImageSequence.Iterator(self.img)]
        self.base_delay = self.img.info.get("duration", 80)
        self.img.close()

        self.slider.destroy()
        self.slider = tb.Scale(self.panel, from_=-0.25, to=2.25, style="success", orient="horizontal", variable=self.speed_var, length=650)
        self.slider.config(state="dark" if self.is_paused else "success")
        if not self.single_frame:
            self.slider.pack()
            date = self.gifs[self.selected_gif_idx].split("-")[-4]
            y, m, d = date[:4], date[4:6], date[6:]
            self.extra_data.config(text=f"Date: {d}/{m}/{y}")
        self.idx = 0
        self.label.configure(image=self.frames[int(self.idx)])

    def animate(self):
        self.label.configure(image=self.frames[int(self.idx)])
        if self.is_paused:
            self.slider.config(bootstyle="dark")
        else:
            self.slider.config(bootstyle="primary")
            speed = self.speed_var.get()
            real_speed = speed
            if -0.01 < speed < 0.01:
                real_speed = 0.0
                self.slider.config(bootstyle="danger")
            if 0.98 < speed < 1.02:
                real_speed = 1.0
                self.slider.config(bootstyle="success")
            if 1.98 < speed < 2.02:
                real_speed = 2.0
                self.slider.config(bootstyle="info")
            self.idx += real_speed
            if self.idx >= len(self.frames):
                self.idx = 0
            if self.idx < 0:
                self.idx = len(self.frames) - 1

        self.after(self.base_delay, self.animate)


class WandFrame(EntrySelector):
    def __init__(self, master, wands, random_button=True, title="Wands", **kwargs):
        self.wands = wands

        extra_btn = {"name": "export", "style": "info-outline", "command": self.make_picture}
        super().__init__(master.scrollable_frame, self.wands, random_button=random_button, extra_button=extra_btn, title=title, **kwargs)
        self.master = master
        self.mainframe = tb.Frame(self, width=600, height=480, relief=RAISED)
        self.splitframe = tb.Frame(self.mainframe)
        self.combined_empty = Image.alpha_composite(
            Util.INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"],
            Util.INVENTORY_SPRITE["ui_gfx/inventory/inventory_box_inactive_overlay.png"])

        self.stat_frame = tb.Frame(self.splitframe)
        self.stats_labels = {}

        idx = 0
        for key, val in Util.WAND_STATS_ICON.items():
            image = Canvas(self.stat_frame, width=25, height=25)
            image.create_image(0, 0, anchor=NW, image=val)
            image.image = val
            image.grid(row=idx, column=0, padx=20, pady=5, sticky="w")
            tb.Label(self.stat_frame, text=key, font=Util.tk_font("Tl")).grid(row=idx, column=1, padx=4, pady=5, sticky="w")
            self.stats_labels[key] = tb.Label(self.stat_frame, text="-", font=Util.tk_font("Tl"))
            self.stats_labels[key].grid(row=idx, column=2, padx=15, pady=5, sticky="w")

            idx += 1

        self.stat_frame.grid(row=0, column=0)

        self.label = tk.Label(self.splitframe, width=160, height=280)
        self.label.grid(row=0, column=1, sticky="nw")

        self.always_spell_frame = tb.Frame(self.splitframe)
        self.image_always_frame = None
        self.create_always_scrolls()
        self.always_spell_frame.grid(row=0, column=2, padx=0, sticky="nse")
        self.splitframe.pack(fill="x", expand=True, anchor="n", padx=2, pady=2)

        self.spell_frame = tb.Frame(self.mainframe)
        self.image_frame = None
        self.create_scroll_spells()

        self.spell_frame.pack(anchor="s", fill="x", expand=True, padx=2, pady=2)
        self.mainframe.pack(fill="both", expand=True, padx=30)
        self.draw_wand()

        self.wand_frames = []
        self.frame_wait = 0
        self.frame_idx = 0
        self.animate()

    def animate(self):
        if self.frame_wait < 1:
            self.after(100, self.animate)
            return
        self.label.configure(image=self.wand_frames[self.frame_idx])
        self.label.image = self.wand_frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.wand_frames)
        self.after(self.frame_wait, self.animate)

    def make_picture(self):
        if isinstance(self.wands[self.selected_gif_idx], str):
            stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites = Util.get_wand_structure(self.wands[self.selected_gif_idx])
        else:
            stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites = self.wands[self.selected_gif_idx]

        if PERFECT_WAND_PRINT:
            final_image = Util.one_to_one_wand_picture(stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites)
        else:
            final_image = Util.basic_wand_picture(stats, wand_sprite, spell_sprites, spell_index)
        if not os.path.exists(os.getenv('APPDATA') + "/Noita_saves/temp"):
            os.mkdir(os.getenv('APPDATA') + "/Noita_saves/temp")
        save_name = f"{os.getenv('APPDATA')}/Noita_saves/temp/{Util.get_random_enough_element(Util.WAND_NAME)}.png"
        final_image.save(save_name)
        final_image.close()
        os.startfile(save_name)

    def create_always_scrolls(self, items=0, other_items=0):

        canvas = tb.Canvas(self.always_spell_frame, width=80, height=330)

        if items > 3:
            scrollbar = tb.Scrollbar(self.always_spell_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            if other_items <= 7:
                self.set_scroll(canvas, False)
        else:
            scrollbar = tb.Frame(self.always_spell_frame, width=13, height=0)
        scrollbar.pack(side="right", fill="y")

        canvas.pack(side="left", fill="both", expand=True, pady=5, padx=0)

        self.image_always_frame = tb.Frame(canvas)
        canvas.create_window((0, 0), window=self.image_always_frame, anchor="nw")

        def update_a_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.image_always_frame.bind("<Configure>", update_a_scroll)
        #self.set_focus_widget(self.always_spell_frame)

    def create_scroll_spells(self, items=0):

        canvas = tb.Canvas(self.spell_frame, width=600, height=80)
        canvas.pack(side="top", fill="x", expand=True, pady=5, padx=2)

        if items > 7:
            scrollbar = tb.Scrollbar(self.spell_frame, orient="horizontal", command=canvas.xview)
            canvas.configure(xscrollcommand=scrollbar.set)
        else:
            scrollbar = tb.Frame(self.spell_frame, width=0, height=13)
        scrollbar.pack(side="bottom", fill="x")
        self.set_scroll(canvas, True)

        self.image_frame = tb.Frame(canvas)
        canvas.create_window((0, 0), window=self.image_frame, anchor="nw")

        def update_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.image_frame.bind("<Configure>", update_scroll)

    def draw_wand(self):
        self.reset_focus_frames()
        if isinstance(self.wands[self.selected_gif_idx], str):
            stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites = Util.get_wand_structure(self.wands[self.selected_gif_idx])
        else:
            stats, wand_sprite, spell_sprites, charges, spell_index, always_cast_sprites = self.wands[self.selected_gif_idx]
        if "Time Mod" in stats.keys():
            self.extra_data.config(text=f"Date: {stats.pop("Time Mod")}")
        idx = 0

        for k, v in stats.items():
            self.stats_labels[k].destroy()
            if k == "Spread":
                if not v.startswith("-"):
                    v += " "
            self.stats_labels[k] = tb.Label(self.stat_frame, text=f"{v}{(" "*(10-len(str(v))))}", font=Util.tk_font("Tl"))
            self.stats_labels[k].grid(row=idx, column=2, padx=15, pady=5, sticky="w")
            idx += 1

        tk_wand_sprites = []
        for w_s in wand_sprite["img"]:
            w_sprite = w_s.convert("RGBA").transpose(Image.Transpose.ROTATE_90)
            size = (min(w_sprite.width*10, 160), min(w_sprite.height*10, 280))
            tk_wand_sprites.append(ImageTk.PhotoImage(w_sprite.resize(size, Image.Resampling.NEAREST)))
        self.label.configure(image=tk_wand_sprites[0])
        self.label.image = tk_wand_sprites[0]
        self.label.bind("<Double-Button-1>", lambda e, link=Util.wand_to_simulator_link(stats, spell_sprites, spell_index): Util.opening_page(link))

        self.wand_frames = tk_wand_sprites
        self.frame_wait = wand_sprite["wait"]
        self.frame_idx = 0

        self.spell_frame.destroy()
        self.spell_frame = tb.Frame(self.mainframe)
        self.create_scroll_spells(stats["Capacity"])
        self.spell_frame.pack(anchor="s", fill="x", expand=True, padx=2, pady=2)

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
                charge = charges[spell_idx]
                small = Util.get_asset_image(spell_paths[0]).resize((50, 50), Image.Resampling.NEAREST).convert("RGBA")
                if spell_paths[1] == spell_paths[0]:
                    combined = self.combined_empty.copy()
                    combined.paste(small, (14, 15), small)
                    photo = ImageTk.PhotoImage(combined)
                else:
                    big = Util.get_asset_image(spell_paths[1]).resize((80, 80), Image.Resampling.NEAREST).convert("RGBA")
                    combined = Image.alpha_composite(Util.INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"], big)
                    combined.paste(small, (14, 15), small)
                    photo = ImageTk.PhotoImage(combined)
                spell = Canvas(self.image_frame, width=80, height=80)
                spell.create_image(0, 0, anchor="nw", image=photo)
                if charge >= 0:
                    spell.create_text(20, 20, text=str(charge), fill="white", font=Util.tk_font("Tl"))
                spell.image = photo
                wiki_spell = Util.spell_path_to_wiki_name(spell_paths[0])
                if wiki_spell:
                    spell.bind("<Double-Button-1>", lambda e, link=f"https://noita.wiki.gg/wiki/Special:Search/{wiki_spell}": Util.opening_page(link))
                spell.grid(row=0, column=idx)
                spell_idx += 1
            else:
                photo = ImageTk.PhotoImage(self.combined_empty)
                spell = Canvas(self.image_frame, width=80, height=80)
                spell.create_image(0, 0, anchor="nw", image=photo)
                spell.image = photo
                spell.grid(row=0, column=idx)
        idx = 1

        self.always_spell_frame.destroy()
        self.always_spell_frame = tb.Frame(self.splitframe)
        self.create_always_scrolls(len(always_cast_sprites), stats["Capacity"])
        self.always_spell_frame.grid(row=0, column=3, padx=0, sticky="nw")

        photo = ImageTk.PhotoImage(Util.get_asset_image("ui_gfx/inventory/icon_gun_permanent_actions.png").resize((50, 50), Image.Resampling.NEAREST).convert("RGBA"))
        spell = Canvas(self.image_always_frame, width=80, height=80)
        spell.create_image(14, 15, anchor="nw", image=photo)
        spell.image = photo
        spell.grid(row=0, column=0)

        if len(always_cast_sprites) == 0:
            return

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
            small = Util.get_asset_image(spell_paths[0]).resize((50, 50), Image.Resampling.NEAREST).convert("RGBA")
            big = Util.get_asset_image(spell_paths[1]).resize((80, 80), Image.Resampling.NEAREST).convert("RGBA")
            combined = Image.alpha_composite(Util.INVENTORY_SPRITE["ui_gfx/inventory/inventory_box.png"], big)
            combined.paste(small, (14, 15), small)
            photo = ImageTk.PhotoImage(combined)

            spell = Canvas(self.image_always_frame, width=80, height=80)
            spell.create_image(0, 0, anchor="nw", image=photo)
            spell.image = photo

            wiki_spell = Util.spell_path_to_wiki_name(spell_paths[0])
            if wiki_spell:
                spell.bind("<Double-Button-1>", lambda e, link=f"https://noita.wiki.gg/wiki/Special:Search/{wiki_spell}": Util.opening_page(link))
            spell.grid(row=idx, column=0)
            idx += 1

    def re_draw(self, ignore):
        self.master.scrolldepth.set(self.master.canvas.yview()[0])
        self.draw_wand()
        self.master.update_idletasks()
        self.master.canvas.yview_moveto(self.master.scrolldepth.get())
        self.master.update_idletasks()


class MinaMoment(tb.Frame):
    def __init__(self, master, world_path, **kwargs):

        super().__init__(master, **kwargs)
        slice_pair = Util.get_player_final_model(world_path)
        self.information = {}
        self.arm_png = None
        i = len(slice_pair.keys())-1
        for k in slice_pair.keys():
            label = tb.Label(self, style="secondary-inverse")
            label.configure(image=slice_pair[k][0])
            label.grid(row=0, column=i, padx=3)

            self.information[k] = {"idx": 0, "frames": slice_pair[k], "len": len(slice_pair[k]), "label": label}
            i -= 1
        self.animate()

    def animate(self):
        for v in self.information.values():
            v["label"].configure(image=v["frames"][v["idx"]])
            v["idx"] = (v["idx"] + 1) % v["len"]
        self.after(160, self.animate)


class SessionDisplay(tb.Frame):
    def __init__(self, master, path, config_path, map_image, rendered=True, **kwargs):

        self.tooltip_window = None
        self.server_thread = None
        self.httpd = None
        self.port = None

        super().__init__(master, **kwargs)
        if path is None:
            return
        if not os.path.exists(path):
            return

        self.path = path
        self.save_config_path = config_path
        self.death_map_path = self.save_config_path + "/assets/death_maps/" + Util.hashify(path.encode("utf-8")) + ".html"
        self.paths = os.listdir(path)[::-1]
        self.session_runs = 0
        self.overall_gold_collected = 0
        self.overall_save_playtime = 0
        self.overall_kills = 0

        self.most_playtime = 0
        self.most_gold = 0
        self.most_kills = 0

        self.map = map_image
        self.draw_speed = 5

        self.canvas = tb.Canvas(self, width=self.map.width(), height=self.map.height())
        self.canvas.bind("<Double-Button-1>", lambda e: self.export_death_markers())

        self.rendered = rendered
        if self.rendered:
            top_panel = tb.Frame(self, width=620, relief=GROOVE)
            self.s_count_button = tb.Button(top_panel, text="Runs: -", bootstyle="warning-outline")
            self.time_button = tb.Button(top_panel, text="Playtime: -", bootstyle="warning-outline")
            self.time_button.bind("<Enter>", lambda e: self.show_tooltip("Mark longest run", e))
            self.time_button.bind("<Leave>", self.hide_tooltip)
            self.gold_button = tb.Button(top_panel, text="Gold: -", bootstyle="warning-outline")
            self.gold_button.bind("<Enter>", lambda e: self.show_tooltip("Mark richest run", e))
            self.gold_button.bind("<Leave>", self.hide_tooltip)
            self.kills_button = tb.Button(top_panel, text="Kills: -", bootstyle="warning-outline")
            self.kills_button.bind("<Enter>", lambda e: self.show_tooltip("Mark most brutal run", e))
            self.kills_button.bind("<Leave>", self.hide_tooltip)
            self.s_count_button.grid(row=0, column=0, padx=7, pady=8)
            self.gold_button.grid(row=0, column=1, padx=5, pady=8)
            self.kills_button.grid(row=0, column=2, padx=5, pady=8)
            self.time_button.grid(row=0, column=3, padx=7, pady=8)
            top_panel.pack()

            current_run_stats = self.path.split("stats")[0]+"player.xml"
            if os.path.exists(current_run_stats):
                grab = Util.get_player_stats(current_run_stats)
                if grab.get("wallet_money_target=") is None:
                    grab["wallet_money_target="] = "-1"
                tooltip, x_y_rel_x_y, is_dead, is_in_pw, money_time = self.get_tooltip_and_coordinates_from_xml(self.path+"/"+grab["stats_filename="].split("/")[-1].split("_")[0]+"_stats.xml", [float(grab["position.x="]), float(grab["position.y="]), int(grab['wallet_money_target='])])
                self.overall_save_playtime -= money_time[1]
                self.overall_kills -= money_time[2]
                if tooltip:
                    self.s_count_button.config(command=lambda: self.highlight_circle(x_y_rel_x_y[2], x_y_rel_x_y[3], f"Ongoing run ({Util.get_formatted_int(int(math.floor(float(grab['hp='])*25)))} hp):\n{tooltip}"))
                    self.s_count_button.bind("<Enter>", lambda e: self.show_tooltip(" Mark latest run... ", e))
                    self.s_count_button.bind("<Leave>", self.hide_tooltip)
                else:
                    self.s_count_button.bind("<Enter>", lambda e: self.show_tooltip(" No ongoing run found... ", e))
                    self.s_count_button.bind("<Leave>", self.hide_tooltip)
            else:
                self.s_count_button.bind("<Enter>", lambda e: self.show_tooltip(" No ongoing run found... ", e))
                self.s_count_button.bind("<Leave>", self.hide_tooltip)

            self.canvas.pack(padx=10, pady=10)
            self.canvas.create_image(0, 0, anchor="nw", image=self.map)
            self.draw()
            self.update_buttons()
        else:
            self.draw_speed = 0

    def destroy(self):
        if self.server_thread:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.server_thread.join()
        super().destroy()

    def show_tooltip(self, text, event=None):
        self.tooltip_window = tk.Toplevel(self.canvas)
        self.tooltip_window.wm_overrideredirect(True)
        x, y_size = self.winfo_geometry().split("x")
        y, size_x, size_y = y_size.split("+")
        longest_line = 0
        for line in text.split("\n"):
            if len(line) > longest_line:
                longest_line = len(line)
        if event:
            self.tooltip_window.wm_geometry(f"+{event.x_root+((longest_line*(Util.FONT_TYPE["Tl"]-2))//4)}+{event.y_root + 15}")
        else:
            self.tooltip_window.wm_geometry(f"+{(self.winfo_rootx()+self.winfo_width()-int(size_x))//2}+{self.winfo_rooty()+self.winfo_height()-int(y)}")
        label = tb.Label(self.tooltip_window, text=text, relief="solid", borderwidth=1, justify="left", anchor="w", font=Util.tk_font("Tl"))
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()

    def update_buttons(self):

        self.s_count_button.config(text=f"Runs: {Util.get_formatted_int(self.session_runs)}")
        self.s_count_button.bind("<Enter>", lambda e: self.show_tooltip(f" {self.session_runs} ✔", e))

        self.gold_button.config(text=f"Gold: {Util.get_formatted_int(self.overall_gold_collected)}")
        self.gold_button.bind("<Enter>", lambda e: self.show_tooltip(f" {self.overall_gold_collected} $", e))

        self.kills_button.config(text=f"Kills: {Util.get_formatted_int(self.overall_kills)}")
        self.kills_button.bind("<Enter>", lambda e: self.show_tooltip(f" {self.overall_kills} ☠", e))

        self.time_button.config(text=f"Playtime: {Util.get_str_time(self.overall_save_playtime)}")
        try:
            hrs = f"{int(self.overall_save_playtime) // 3600} hrs"
        except:
            hrs = "unemployed..."
        self.time_button.bind("<Enter>", lambda e: self.show_tooltip(hrs, e))
        if len(self.paths) == 0:
            self.s_count_button.config(bootstyle="primary-outline")
            self.gold_button.config(bootstyle="info-outline")
            self.kills_button.config(bootstyle="danger-outline")
            self.time_button.config(bootstyle="success-outline")
        else:
            self.after(1000, self.update_buttons)

    def highlight_circle(self, x, y, text):
        circle_id = self.canvas.create_oval(x - 6, y - 6, x + 5, y + 5, fill="#D7B237", width=0)

        self.canvas.tag_bind(circle_id, "<Enter>", lambda e: self.show_tooltip(text, e))
        self.canvas.tag_bind(circle_id, "<Leave>", self.hide_tooltip)

    def get_tooltip_and_coordinates_from_xml(self, xml_path, added_cords=None, add_to_overall=True):
        if not os.path.exists(xml_path):
            return "", [0, 0, 0, 0], False, False, [-1, -1, -1]
        try:
            with open(xml_path, encoding="utf-8") as f:
                f.readline()
                f.readline()
                data = f.readline()
            death_cause = data.split("killed_by=\"")[1].split("\" ")[0].replace(" | ", " ") + data.split("killed_by_extra=\"")[1].split("\" ")[0]
            playtime = float(data.split("playtime=\"")[1].split("\" ")[0])

            is_dead = int(data.split("dead=\"")[1].split("\" ")[0]) and death_cause
            if is_dead:
                death_cause = str(death_cause[1:] if death_cause[0] == " " else death_cause)
                if death_cause.startswith("$animal"):
                    death_cause = death_cause.replace(death_cause.split(" ")[0], "")
                polyed = ", while polymorphed to "
                if polyed in death_cause:
                    if death_cause == polyed:
                        death_cause = "Polymorphed"
                    elif death_cause.endswith(polyed):
                        death_cause = death_cause.replace(polyed, "") + " (polymorphed)"
                    elif death_cause.startswith(polyed):
                        death_cause = "Polymorphed to " + death_cause.replace(polyed, "")
            else:
                death_cause = ""

            scaler_x = 620 / (17920 - (-17920))
            scaler_y = 420 / (17400 - (-6400))

            date = xml_path.split("/")[-1].split("-")[0]
            year, month, day = date[:4], date[4:6], date[6:]
            if not added_cords:
                death_pos_x = float(data.split("death_pos.x=\"")[1].split("\" ")[0])
                death_pos_y = float(data.split("death_pos.y=\"")[1].split("\" ")[0])
                gold_collected = data.split("gold_all=\"")[1].split("\" ")[0]
                x, y = max(min(((death_pos_x + 17920) % 35840) * scaler_x, 620-2), 1), max(
                    min((death_pos_y + 6400) * scaler_y, 420-2), 1)
            else:
                if len(added_cords) == 2:
                    death_pos_x, death_pos_y = added_cords

                    gold_collected = data.split("gold_all=\"")[1].split("\" ")[0]
                    x, y = max(min(((((death_pos_x + 17920) % 35840) - 17920) + 17920) * scaler_x, 620-2), 1), max(
                        min((death_pos_y + 6400) * scaler_y, 420-2), 1)
                if len(added_cords) == 3:
                    death_pos_x, death_pos_y = added_cords[0], added_cords[1]

                    gold_collected = added_cords[2]
                    x, y = max(min(((((death_pos_x + 17920) % 35840) - 17920) + 17920) * scaler_x, 620-2), 1), max(
                        min((death_pos_y + 6400) * scaler_y, 420-2), 1)
                if len(added_cords) == 4:
                    death_pos_x, death_pos_y, x, y = added_cords

            kills = int(data.split("enemies_killed=\"")[1].split("\" ")[0])

            str_kills = ""
            if kills >= 1:
                str_kills = f"\nOverall kills: {Util.get_formatted_int(kills)}"

            int_gold_collected = int(gold_collected)
            if add_to_overall:
                self.overall_gold_collected += int_gold_collected

            if not gold_collected == "0":
                gold_collected = f"\nOverall gold: {Util.get_formatted_int(gold_collected)}"
            else:
                gold_collected = ""
            pw = ""
            pw_traveled = int((death_pos_x + 17920) // 35840)
            if not pw_traveled == 0:
                pw = f"\n(PW: {abs(pw_traveled)} {"West" if pw_traveled < 0 else "East"})"
            tooltip_text = f"Started on: {day}/{month}/{year}\nPlaytime: {Util.get_str_time(playtime)}{str_kills}{gold_collected}{"\nCause of Death:\n" if death_cause else ""}{Util.string_line_text(death_cause, 26, "  ")}{pw}"

            if add_to_overall:
                if playtime > self.most_playtime:
                    if self.rendered:
                        self.time_button.config(command=lambda: self.highlight_circle(x, y, tooltip_text))
                    self.most_playtime = playtime
                if int_gold_collected > self.most_gold:
                    if self.rendered:
                        self.gold_button.config(command=lambda: self.highlight_circle(x, y, tooltip_text))
                    self.most_gold = int_gold_collected
                if kills > self.most_kills:
                    if self.rendered:
                        self.kills_button.config(command=lambda: self.highlight_circle(x, y, tooltip_text))
                    self.most_kills = kills

                self.overall_save_playtime += playtime
                self.overall_kills += kills
            return tooltip_text, [death_pos_x, death_pos_y, x, y], is_dead, not pw_traveled == 0, [int_gold_collected, playtime, kills]
        except:
            return "", [0, 0, 0, 0], False, False, [-1, -1, -1]

    def draw(self):

        if len(self.paths) == 0:
            self.draw_speed = 0
            self.update_buttons()
            return
        session = self.paths.pop()

        if os.path.exists(self.path + "/" + session):
            if session.endswith("stats.xml"):
                tooltip, x_y_rel_x_y, is_dead, is_in_pw, money_time = self.get_tooltip_and_coordinates_from_xml(self.path + "/" + session)
                if is_dead:
                    if is_in_pw:
                        circle_id = self.canvas.create_oval(x_y_rel_x_y[2] - 2, x_y_rel_x_y[3] - 2, x_y_rel_x_y[2] + 1, x_y_rel_x_y[3] + 1, fill="#00ff00", width=0)
                    else:
                        circle_id = self.canvas.create_oval(x_y_rel_x_y[2] - 1, x_y_rel_x_y[3] - 1, x_y_rel_x_y[2] + 1, x_y_rel_x_y[3] + 1, fill="red", width=0)
                    self.canvas.tag_bind(circle_id, "<Enter>", lambda e: self.show_tooltip(tooltip, e))
                    self.canvas.tag_bind(circle_id, "<Leave>", self.hide_tooltip)
                self.session_runs += 1
        self.after(self.draw_speed, self.draw)
        return

    def export_death_markers(self):
        if self.draw_speed >= 1:
            self.draw_speed = 0
            return
        if not os.path.exists(self.save_config_path+"/assets/death_maps/noita_map"):
            return
        if not os.path.exists(self.path):
            Util.notification(2, {"type": "warn", "title": "File not found",
                                  "message": "No path to sessions found!"})
            return
        if self.port:
            folder, filename = os.path.split(self.death_map_path)
            os.chdir(folder)
            Util.opening_page(f"http://127.0.0.1:{self.port}/{filename}", True)
            return

        html_map = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Death Map Viewer</title>
<link rel="stylesheet" href="noita_map/map_style.css">
</head>
<body>
<div id="noita_map"></div>
<script src="noita_map/openseadragon.min.js"></script>
<script>
    var viewer = OpenSeadragon({
        id: "noita_map",
        tileSources: "noita_map/capture.dzi",
        showNavigationControl: false,
        maxZoomPixelRatio: 20,
        zoomPerScroll: 1.5,
        animationTime: 0.5,
        imageSmoothingEnabled: false
    });

    var markers = ["""

        max_messages = [{"value": 0, "message": "", "criteria": "money collected"},
                        {"value": 0, "message": "", "criteria": "time spent"},
                        {"value": 0, "message": "", "criteria": "kills commited"}]

        for session in os.listdir(self.path):
            if session.endswith("stats.xml"):

                tooltip, x_y_rel_x_y, is_dead, is_in_pw, money_time = self.get_tooltip_and_coordinates_from_xml(self.path + "/" + session, add_to_overall=False)

                x, y = (max(min(((x_y_rel_x_y[0] + 18432) / 36864), 1.0), 0.0),
                        max(min(((x_y_rel_x_y[1] + 31744) / 36864), 2.0), 0.0))

                pw_traveled = int((x_y_rel_x_y[0] + 17920) // 35840)
                if not pw_traveled == 0:
                    x = max(min(((((x_y_rel_x_y[0] + 17920) % 35840 - 17920) + 18432) / 36864), 1.0), 0.0)

                for i in range(3):
                    if x_y_rel_x_y[0] == 0.0 and x_y_rel_x_y[1] == 0.0:
                        pass
                    elif max_messages[i]["value"] < money_time[i]:
                        max_messages[i]["value"] = money_time[i]
                        max_messages[i]["message"] = f"""{{x: {x}, y: {y}, text: \"Most {{CRITERIA_HERE}} in one run:<br>{tooltip.replace("\n", "<br>")}\", type:\"unique\"}},
"""
                if x_y_rel_x_y[0] != 0.0 and x_y_rel_x_y[1] != 0.0:
                    html_map += f"""{{x: {x}, y: {y}, text: \"{tooltip.replace("\n", "<br>")}\", type:{("\"dead\"" if is_dead else "\"leave\"") if not is_in_pw else "\"pw\""}}},
"""

        current_run_stats = self.path.split("stats")[0]+"player.xml"
        if os.path.exists(current_run_stats):
            grab = {'position.x=': None, 'position.y=': None, 'stats_filename=': None, 'wallet_money_target=': None, 'hp=': None}
            with open(current_run_stats, encoding="utf-8") as f:
                for x in range(3000):
                    line = f.readline()
                    key = line.split("\"")[0].replace(" ", "")
                    if key in grab.keys():
                        key = line.split("\"")[0].replace(" ", "")
                        grab[key] = line.split(key + "\"")[1].split("\" ")[0]
                    if grab['stats_filename='] and grab['position.x='] and grab['position.y='] and grab['wallet_money_target='] and grab['hp=']:
                        break

            if grab.get("wallet_money_target=") is None:
                grab["wallet_money_target="] = "-1"
            tooltip, x_y_rel_x_y, is_dead, is_in_pw, money_time = self.get_tooltip_and_coordinates_from_xml(self.path+"/"+grab["stats_filename="].split("/")[-1].split("_")[0]+"_stats.xml", [float(grab["position.x="]), float(grab["position.y="]), int(grab['wallet_money_target='])], add_to_overall=False)

            x, y = (max(min(((x_y_rel_x_y[0] + 18432) / 36864), 1.0), 0.0),
                    max(min(((x_y_rel_x_y[1] + 31744) / 36864), 2.0), 0.0))

            pw_traveled = int((x_y_rel_x_y[0] + 17920) // 35840)
            if not pw_traveled == 0:
                x = max(min(((((x_y_rel_x_y[0] + 17920) % 35840 - 17920) + 18432) / 36864), 1.0), 0.0)
            html_map += f"""{{x: {x}, y: {y}, text: \"Ongoing Run ({Util.get_formatted_int(int(math.floor(float(grab['hp='])*25)))} hp):<br>{tooltip.replace("\n", "<br>")}\", type:"unique"}},
"""
        full_criteria = False
        if max_messages[0]["message"] and max_messages[1]["message"] and max_messages[2]["message"]:
            if max_messages[0]["message"] == max_messages[1]["message"] == max_messages[2]["message"]:
                html_map += max_messages[0]["message"].replace("{CRITERIA_HERE}", f"{max_messages[0]["criteria"]}, {max_messages[1]["criteria"]} & {max_messages[2]["criteria"]}")
                full_criteria = True
        if not full_criteria:
            for i in range(3):
                marker = max_messages[i]["message"].replace("{CRITERIA_HERE}", f"{max_messages[i]["criteria"]}")
                for j in range(3):
                    if i != j:
                        if max_messages[i]["message"] and max_messages[j]["message"]:
                            if max_messages[i]["message"] == max_messages[j]["message"]:
                                marker = max_messages[i]["message"].replace("{CRITERIA_HERE}", f"{max_messages[i]["criteria"]} & {max_messages[j]["criteria"]}")
                html_map += marker
        f = open(self.death_map_path, "w", encoding="utf-8")
        f.write(html_map + """];

    viewer.addHandler('open', function() {

        markers.forEach(function(m) {
            var el = document.createElement("div");
            el.className = "hover-area-"+m.type+" field";

            var tooltip = document.createElement("div");
            tooltip.className = "tooltip";
            tooltip.innerHTML = m.text; 
            el.appendChild(tooltip);

		    viewer.addOverlay({
		    	element: el,
		    	location: new OpenSeadragon.Point(m.x,m.y),
		    	checkResize: false
		    });
        });
    });
</script>
</body>
</html>""")
        f.close()

        folder, filename = os.path.split(self.death_map_path)

        handler = functools.partial(MutedHTTPServerHandler, directory=folder)

        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]

        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

        Util.opening_page(f"http://127.0.0.1:{self.port}/{filename}", True)


class ExtendedTkFrame(tb.Frame):
    def __init__(self, parent, scroll_depth=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.items = []
        self.scrolldepth = scroll_depth
        self.canvas = tb.Canvas(self, highlightthickness=0)
        self.scrollbar = tb.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollable_frame = tb.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind("<Configure>", self._on_resize)

    def destroy(self):
        if self.scrolldepth:
            self.scrolldepth.set(self.canvas.yview()[0])
        super().destroy()

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def is_visible_widget(self, widget):
        widget.update_idletasks()

        widget_height = widget.winfo_height()
        border_margin = widget_height*((1-SCROLL_FRAME_VISIBILITY) if AUTO_SCROLL else -99999)
        widget_top = widget.winfo_rooty()
        widget_bottom = widget_top + widget_height

        canvas_top = self.canvas.winfo_rooty()
        canvas_bottom = canvas_top + self.canvas.winfo_height()

        return widget_top >= canvas_top - border_margin and widget_bottom <= canvas_bottom + border_margin

    def _on_mousewheel(self, event):

        widget = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())

        mouse_hovering_on_element = None
        if widget:
            while widget.master not in self.items and widget.master is not None:
                widget = widget.master
            widget = widget.master
            mouse_hovering_on_element = widget

        if mouse_hovering_on_element:
            try:
                for focus_on_frame in mouse_hovering_on_element.get_focus_widget():
                    if Util.mouse_is_over_widget(focus_on_frame):
                        if self.is_visible_widget(focus_on_frame):
                            if mouse_hovering_on_element.use_scroll(event):
                                return
            except:
                pass

        SCROLL_SPEED = SCROLL_INTENSITY * (-1.0 if SCROLL_INVERTED else 1.0)
        if event.num == 4:
            delta_pixels = -SCROLL_SPEED
        elif event.num == 5:
            delta_pixels = SCROLL_SPEED
        else:
            delta_pixels = (event.delta // 120) * -SCROLL_SPEED

        first, last = self.canvas.yview()

        bbox = self.canvas.bbox("all")
        if not bbox:
            return

        scroll_height = bbox[3] - bbox[1]
        if scroll_height <= 0:
            return

        self.canvas.yview_moveto(max(0, min(first + (delta_pixels / scroll_height), 1)))

    def get_elements(self):
        return self.items

    def swap_items(self, i1, i2):
        self.items[i1], self.items[i2] = self.items[i2], self.items[i1]
        self._reposition_items()

    def add_item(self, frame, refresh=True, inverse=False):
        if inverse:
            self.items.insert(0, frame)
        else:
            self.items.append(frame)
        if refresh:
            return self._reposition_items()

    def remove_item(self, frame):
        self.items.remove(frame)
        self._reposition_items()

    def _on_resize(self, event):
        self._reposition_items()

    def refresh(self):
        self._reposition_items()

    def bulk_population(self, size, width, height):
        if len(self.items) == 0:
            for i in range(size):
                self.items.append(tb.Frame(self.scrollable_frame, width=width, height=height))
            self._reposition_items()
            return True
        return False

    def replace_idx(self, widget, index, refresh):
        self.items[index] = widget
        if refresh:
            self._reposition_items()

    def _reposition_items(self):
        if not self.items:
            return 1

        self.update_idletasks()
        width = self.winfo_width()
        if width <= 1:
            return 1

        item_widths = [w.winfo_reqwidth() for w in self.items]
        max_item_width = max(item_widths) if item_widths else 2
        columns = max(1, width // max_item_width)

        for widget in self.scrollable_frame.winfo_children():
            widget.grid_forget()

        leftover_padding = math.floor(max((width - (max_item_width*min(columns, len(self.items))))-13, 0)/(min(len(self.items)+1, columns+1)))
        for index, widget in enumerate(self.items):
            cols = (index % columns)
            widget.grid(row=index // columns, column=cols, padx=(0 if cols % 2 else leftover_padding), pady=10, sticky="nsew")

        for col in range(columns):
            self.scrollable_frame.grid_columnconfigure(col, weight=1)


class WorldBannerFrame(tb.Frame):
    def __init__(self, parent, world_path, open_command=None, more_command=None, **kwargs):
        if "data.json" not in os.listdir(world_path):
            with open(world_path + "/data.json", "w") as f:
                json.dump({"name": world_path.split("/")[-1].split("\\")[-1], "description": ""}, f, indent=4)
        super().__init__(parent, **kwargs)
        self.functional_data = True
        try:
            with open(world_path + "/data.json") as f:
                self.selected_world_data = json.load(f)
        except Exception as e:
            self.functional_data = False
            Util.notification(3, {"type": "warn", "title": "Faulty save", "message": f"Failed to properly load data from\n{world_path}\n\nThe Save data.json seems to be faulty...\n{e}"})
            self.selected_world_data = {"name": world_path.split("/")[-1].split("\\")[-1], "description": "FAILED TO LOAD DATA!"}

        self.selected_world_data["name"] = self.selected_world_data.get("name", "")
        self.selected_world_data["description"] = self.selected_world_data.get("description", "")
        self.active_run = os.path.exists(world_path + "/Nolla_Games_Noita/save00/player.xml")

        is_cheated = Util.noita_world_was_modded(world_path)

        self.panel = tb.Frame(self, padding=6, style="secondary", relief=GROOVE)

        west_panel = tb.Frame(self.panel, style="secondary")
        west_panel.grid(row=0, column=0, padx=0, pady=0)
        east_panel = tb.Frame(self.panel, style="secondary")
        east_panel.grid(row=0, column=1, padx=0, pady=0)

        lable = tb.Text(west_panel, width=10, height=3)
        lable.insert(tk.END, '\n'.join(
            self.selected_world_data["name"][i:i + 10] for i in range(0, len(self.selected_world_data["name"]), 10)))
        lable.config(state="disabled", font=Util.tk_font("Hm"))
        lable.grid(row=0, column=0, padx=5, pady=5)

        sub_panel = tb.Frame(west_panel, style="secondary")
        sub_panel.grid(row=1, column=0, padx=0, pady=0)

        self.world_path = world_path
        self.is_selector = False
        self.command = lambda value=world_path: open_command(value)
        self.select = tb.Button(sub_panel, text="PLAY", style=f"success{"" if self.active_run else "-outline"}", command=self.command)
        self.select.grid(row=0, column=0, pady=10, padx=10)
        tb.Button(sub_panel, text="More...", style="light" if self.functional_data else "warning-outline", command=lambda value=world_path: more_command(value)).grid(row=0, column=1, pady=10, padx=10)

        self.text = ScrollSelectionText(east_panel, frame_size=[420, 75], style="secondary")
        self.text.set_focus_widget(self.text.text)
        self.text.set_max_height(4)

        desc = self.selected_world_data["description"]
        self.text.text.insert(tk.END, desc if desc else "  ")
        self.text.text.config(state="disabled", font=Util.tk_font("Ts"))
        self.text.pack(anchor="n", padx=10)

        south_panel = tb.Frame(east_panel)
        south_panel.pack(anchor="s", padx=5, pady=5)

        mod_panel = tb.Frame(east_panel)
        mods = Util.get_mods(world_path)
        if mods:
            menu_button = tb.Menubutton(mod_panel, text="Modded run", style="info")
            menu_button.pack()
            menu = tk.Menu(menu_button, tearoff=0)
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
            for mod in mods:
                menu.add_command(label="- " + mod["name"], font=Util.tk_font("Tl"), command=lambda link=mod["link"]: Util.opening_page(link))
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

            menu_button["menu"] = menu
        elif is_cheated:
            menu_button = tb.Menubutton(mod_panel, text="Illegitimate run", style="warning-outline")
            menu_button.pack()
            menu = tk.Menu(menu_button, tearoff=0)
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
            menu.add_command(label="The current run had some", font=Util.tk_font("Tl"), command=lambda link="https://noita.wiki.gg/wiki/Mod_Restrictions": Util.opening_page(link))
            menu.add_command(label="mod enabled on it", font=Util.tk_font("Tl"), command=lambda link="https://noita.wiki.gg/wiki/Mod_Restrictions": Util.opening_page(link))
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
            menu_button["menu"] = menu
        else:
            menu_button = tb.Frame(mod_panel, style="secondary", width=133, height=33)

            def open_it(e):
                if Util.process_running():
                    Util.opening_page("https://www.youtube.com/watch?v=lWqJTKdznaM&t=21s")
            menu_button.bind("<Button-1>", lambda e: open_it(e))
            menu_button.grid(row=0, column=0)

        mod_panel.pack(anchor="se", padx=10, pady=5)

        self.search_term = (Util.reduced_string(self.selected_world_data["name"])+"|" +
                            Util.reduced_string(self.selected_world_data["description"])+"|" +
                            Util.reduced_string(self.selected_world_data.get("extra_notes", ""))+"|" +
                            ("-mods|-modded|-workshop|" + ("|".join(Util.reduced_string(m["name"]) for m in mods)) +
                             ("|".join(Util.reduced_string(m) for m in Util.get_enabled_mod_list(world_path)[0])) if mods or is_cheated else "-vanilla|-original|") +
                            ("-active|-playing" if self.active_run else "")+("" if self.functional_data else "-faulty|-error|-broken"))
        if "backup_path" in self.selected_world_data.keys():
            if os.path.exists(self.selected_world_data["backup_path"]):
                self.search_term += "|-backups"
        elif "is_backup_of" in self.selected_world_data.keys():
            if os.path.exists(self.selected_world_data["is_backup_of"]):
                self.search_term += "|-backups"
        self.panel.pack_propagate(False)
        self.hidden_displacer = tb.Frame(self, width=673, height=169)
        self.panel.pack(pady=5, padx=10, fill="both", expand=True)
        self.is_visible = "False"
        self.display_banner(self.contains_keyword())

    def contains_keyword(self):
        if isinstance(WORLD_BANNER_SEARCH_TERM, list):
            for search_term in WORLD_BANNER_SEARCH_TERM:
                if search_term.startswith("!"):
                    if search_term[1:] in self.search_term:
                        return False
                else:
                    if search_term not in self.search_term:
                        return False
            return True
        else:
            if WORLD_BANNER_SEARCH_TERM.startswith("!"):
                return WORLD_BANNER_SEARCH_TERM[1:] not in self.search_term
            return WORLD_BANNER_SEARCH_TERM in self.search_term

    def display_banner(self, display=True):
        if display == self.is_visible:
            return 1 if display else 0
        if display:
            self.hidden_displacer.pack_forget()
            self.panel.pack(pady=5, padx=10, fill="both", expand=True)
            self.is_visible = True
            return 1
        else:
            self.is_visible = False
            self.panel.pack_forget()
            self.hidden_displacer.pack()
            return 0

    def get_focus_widget(self):
        return [self.text]

    def use_scroll(self, event):
        return self.text.use_scroll(event)

    def toggle_selector(self, single, new_command=None):
        if new_command:
            self.select.config(text="SELECT")
            self.select.config(command=lambda: new_command(self))
            if "backup_path" in self.selected_world_data.keys() and single:
                if os.path.exists(self.selected_world_data["backup_path"]):
                    self.select.config(bootstyle="info-outline")
                    return
            self.select.config(bootstyle="primary-outline")
        else:
            self.select.config(text="PLAY")
            self.select.config(command=self.command)
            self.select.config(bootstyle=f"success{"" if self.active_run else "-outline"}")


class TitledFrame(ScrollSetElement):
    def __init__(self, parent, title, extras=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title_label = tb.Label(self, text=title, font=Util.tk_font("Hm"))
        self.title_label.pack(anchor="nw", padx=10, pady=4)
        self.extra_label = None
        if extras:
            self.extra_label = tb.Label(self, text=extras, font=Util.tk_font("Tl"))
            self.extra_label.pack(anchor="se", padx=10, pady=4)

        self.content = tb.Frame(self, padding=5, relief=GROOVE)
        self.content.pack(fill="x", expand=True, pady=5, padx=5)


class PerkDisplay(TitledFrame):
    def __init__(self, parent, perks, re_roll_price, **kwargs):
        self.re_roll_text = f" Re-roll price at: {Util.get_formatted_int(re_roll_price)} $"
        super().__init__(parent, "Active Perks:",  self.re_roll_text,  **kwargs)

        self.perk_list = perks

        self.perk_count = 0

        self.tooltip_window = None
        self.perk_display_len = math.ceil(len(self.perk_list)/5)

        canvas = tb.Canvas(self.content, width=600, height=374)
        canvas.pack(fill="x", expand=True, pady=5, padx=5)

        if self.perk_display_len > 8:
            scrollbar = tb.Scrollbar(self, orient="horizontal", command=canvas.xview)
            scrollbar.pack(side="bottom", fill="x")
            canvas.configure(xscrollcommand=scrollbar.set)

        self.image_frame = tb.Frame(canvas)
        canvas.create_window((0, 0), window=self.image_frame, anchor="nw")

        def update_scroll(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.image_frame.bind("<Configure>", update_scroll)

        self.perk_index = 0
        self.set_scroll(canvas, True)

        self.after(1, self.add_perk)

    def show_tooltip(self, text, event=None):
        self.tooltip_window = tk.Toplevel(self.canvas)
        self.tooltip_window.wm_overrideredirect(True)
        x, y_size = self.winfo_geometry().split("x")
        y, size_x, size_y = y_size.split("+")
        longest_line = 0
        for line in text.split("\n"):
            if len(line) > longest_line:
                longest_line = len(line)
        if event:
            self.tooltip_window.wm_geometry(f"+{event.x_root+((longest_line*(Util.FONT_TYPE["Tl"]-2))//4)}+{event.y_root + 15}")
        else:
            self.tooltip_window.wm_geometry(f"+{(self.winfo_rootx()+self.winfo_width()-int(size_x))//2}+{self.winfo_rooty()+self.winfo_height()-int(y)}")
        label = tb.Label(self.tooltip_window, text=text, relief="solid", borderwidth=10, justify="left", anchor="w", font=Util.tk_font("Tl"))
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()

    def add_perk(self):
        if len(self.perk_list) == 0:
            return
        perk = self.perk_list.pop(0)
        perk_name_maybe = perk["img_path"].split("/")[-1].replace(".png", "")
        if perk_name_maybe in ["ingest_projectiles", "perks_hover_for_more", "todo", "duplicate"]:
            self.after(10, self.add_perk)
            return
        img = ImageTk.PhotoImage(Util.get_asset_image(perk["img_path"].replace("data/", "")).resize((75, 75), Image.Resampling.NEAREST).convert("RGBA"))

        perk_img = Canvas(self.image_frame, width=75, height=75)
        perk_img.create_image(0, 0, anchor="nw", image=img)
        if perk["count"] > 1:
            perk_img.create_text(20, 20, text=str(perk["count"]), fill="white", font=Util.tk_font("Tl"))
        perk_img.image = img
        name, desc = Util.perk_path_to_name_and_desc(perk["img_path"])
        if perk["img_path"].startswith("mods/"):
            name = perk["name"]
        if name and not perk["img_path"].startswith("mods/"):
            link_name = name
            if link_name in ["Always Cast (One-off)", "All-Seeing Eye"]:
                link_name += "_(Perk)"
            perk_img.bind("<Double-Button-1>", lambda e, link=f"https://noita.wiki.gg/wiki/Special:Search/{link_name.replace(" (One-off)", "")}": Util.opening_page(link))

        if name or desc:
            real_name = Util.string_line_text(f"{f"{name}" if name else ""}{" ("+str(perk["count"])+" X)" if perk["count"] > 1 else ""}", 25)
            real_desc = Util.string_line_text(desc, 25)
            text = f"{real_name}{",\n" if name and desc else ""}{f"\n{real_desc}" if real_desc else ""}"
            perk_img.bind("<Enter>", lambda e: self.show_tooltip(text, e))
            perk_img.bind("<Leave>", self.hide_tooltip)

        perk_img.grid(column=int(self.perk_index//5), row=int(self.perk_index % 5))
        self.perk_index += 1
        self.perk_count += perk["count"]
        le = Util.get_formatted_int(self.perk_count)
        self.extra_label.config(text=f"Overall perks: {le}{" "*(45-(len(le)+len(self.re_roll_text)))}{self.re_roll_text}")
        self.after(5, self.add_perk)


class WorldSaver(ScrollSelectionText):
    def __init__(self, parent, world_path, name=None, initial_data="", config_id="description", frame_size=None, **kwargs):
        super().__init__(parent, frame_size, **kwargs)

        self.world_path = world_path
        self.name = name
        self.text_ids = config_id
        self.initial_data = initial_data

    def destroy(self):
        local_conf = {}
        if os.path.exists(self.world_path + "/data.json"):
            try:
                with open(self.world_path + "/data.json") as f:
                    local_conf = json.load(f)
            except:
                pass
        if self.name:
            local_conf["name"] = self.name.get()
        local_conf[self.text_ids] = self.text.get("1.0", "end-1c")

        if self.initial_data == local_conf:
            super().destroy()
            return
        if os.path.exists(self.world_path):
            with open(self.world_path + "/data.json", "w") as f:
                json.dump(local_conf, f, indent=4)

        super().destroy()


class PlayerStatsDisplay(TitledFrame):
    def __init__(self, parent, player_stats, **kwargs):

        super().__init__(parent, "Latest stats:", **kwargs)

        self.stats_frame = tb.Frame(self.content, width=650, height=380 if self.extra_label else 430)
        self.stats_frame.pack()
        self.stats_frame.pack_propagate(False)

        main_frame = tb.Frame(self.stats_frame)
        main_frame.pack(fill="both", expand=True)

        canvas = tb.Canvas(main_frame)
        canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_y.pack(side="right", fill="y")

        scroll_x = tb.Scrollbar(self.stats_frame, orient="horizontal", command=canvas.xview)
        scroll_x.pack(side="bottom", fill="x")

        canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_frame = tb.Frame(canvas)

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        if not "player_HIDDEN_stats_file" in player_stats.keys():
            self.set_scroll(canvas)
            return
        if not player_stats["player_HIDDEN_stats_file"]:
            self.set_scroll(canvas)
            return
        idx = 0
        for k, v in player_stats.items():
            if "HIDDEN_" not in k:
                val_name = k
                real_name = k.split("_APPEND_")
                append_sign = ""
                value = v
                if len(real_name) == 2:
                    val_name = real_name[0]
                    append_sign = real_name[1]
                if not v:
                    append_sign = ""
                    value = "-"
                out = Util.nested_struct_to_string(value, append_sign=append_sign)
                for filters in ["player_", "stats_", "kills_", "world_state_", "streaming_event_config_", "mod_config_"]:
                    if val_name.startswith(filters):
                        val_name = val_name[len(filters):]
                line_out = out.split("\n")
                if len(line_out) > 300:
                    out = "\n".join(line_out[:299])+"\n..."
                if not value == "-":
                    tb.Label(scroll_frame, text=f"{val_name}:", font=Util.tk_font("Hs"), style="light").grid(row=idx, column=0, sticky="ne", pady=10)
                    tb.Label(scroll_frame, text=f"{out}", font=Util.tk_font("Tl")).grid(row=idx, column=1, sticky="nw", pady=10)
                    idx += 1
        self.set_scroll(canvas)


class ShowLinkEntries(TitledFrame):
    def __init__(self, parent, config, redraw, **kwargs):

        super().__init__(parent, "Unlisted Paths:", **kwargs)
        colors = ["primary", "secondary", "success", "info", "warning", "danger", "light"]
        self.button_colors = [c+"-outline" for c in colors] + colors
        self.stats_frame = tb.Frame(self.content)
        self.save_config = config
        self.redraw = redraw
        self.stats_frame.pack()

        tb.Button(self.stats_frame, text="Add a link", style="info", command=self.add_new_link).pack(anchor="n")

        self.main_frame = tb.Frame(self.stats_frame)
        self.main_frame.pack(fill="both", expand=True)

        self.main_canvas = tb.Canvas(self.main_frame)
        self.main_canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tb.Scrollbar(self.main_frame, orient="vertical", command=self.main_canvas.yview)
        scroll_y.pack(side="right", fill="y")

        self.main_canvas.configure(yscrollcommand=scroll_y.set)

        self.main_frame = tb.Frame(self.main_canvas)

        self.main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))

        self.row = 0
        self.set_scroll(self.main_canvas)
        for link_name, link_data in self.save_config.get("spoiler_links", {}).items():
            self.add_frame_entry(link_name, link_data)
        self.set_scroll(self.main_canvas)

    def add_new_link(self):

        add_link_entry_frame = tb.Frame(self.content)
        tb.Label(add_link_entry_frame, text="Setup new link:", font=Util.tk_font("Tl")).pack(anchor="w", pady=10)

        entry_name_var = tb.StringVar()
        entry_append_var = tb.StringVar()

        def limit_string_size(*args):
            value = entry_name_var.get()
            if len(value) > 30:
                entry_name_var.set(value[:30])

        entry_name_var.trace_add("write", limit_string_size)

        tb.Label(add_link_entry_frame, text="Provide link name:", font=Util.tk_font("Tm")).pack(expand=True, fill="both")
        entry_name = tb.Entry(add_link_entry_frame, textvariable=entry_name_var, style="primary", width=30)
        entry_name.pack(pady=5)

        tb.Label(add_link_entry_frame, text="Provide the link:\n(you can use raw xml stats keys\n like so \"{{stats_Seed}}\" in your link as placeholders\nif your link allows such arguments)", font=Util.tk_font("Tm")).pack(pady=5, expand=True, fill="both")
        entry_append = tb.Entry(add_link_entry_frame, textvariable=entry_append_var, style="info", width=50)
        entry_append.pack()

        button_color_selected = tb.StringVar(value="primary-outline")

        tb.Label(add_link_entry_frame, text="Select color:", font=Util.tk_font("Tm")).pack(pady=10, expand=True, fill="both")

        container = tb.Frame(add_link_entry_frame)
        container.pack(fill="both", expand=True)

        canvas = tb.Canvas(container, height=37)
        canvas.pack(side="top", fill="both", expand=True)

        scroll_x = tb.Scrollbar(container, orient="horizontal", command=canvas.xview)
        scroll_x.pack(side="bottom", fill="x")

        canvas.configure(xscrollcommand=scroll_x.set)

        scroll_frame = tb.Frame(canvas)

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for col, button_style in enumerate(self.button_colors):
            def update_link_color(c, b):
                for a_b in scroll_frame.winfo_children():
                    if isinstance(a_b, tb.Button):
                        a_b.config(text=" ")
                button_color_selected.set(c)
                b.config(text=" ✓ ")

            button = tb.Button(scroll_frame, text=" ", style=button_style)
            if button_style == "primary-outline":
                button.config(text=" ✓ ")
            button.config(command=lambda color=button_style, b=button: update_link_color(color, b))
            button.config(bootstyle=button_style)
            button.grid(row=0, column=col, padx=5)

        self.stats_frame.pack_forget()

        def add_entry():
            xml_grab_name = entry_name.get()
            new_link = entry_append.get()
            if xml_grab_name.replace(" ", "") == "":
                Util.notification(4, {"type": "warn", "title": "Invalid name", "message": f"No valid name for the new\nlink argument provided..."})
                return
            if new_link.replace(" ", "") == "":
                Util.notification(4, {"type": "warn", "title": "Invalid name", "message": f"No valid link for the new\nlink argument provided..."})
                return
            if xml_grab_name not in self.save_config["spoiler_links"].keys():
                link_attrib = {"color": button_color_selected.get(), "link": new_link}
                self.save_config["spoiler_links"][xml_grab_name] = link_attrib
                self.add_frame_entry(xml_grab_name, link_attrib)
                self.canvas.yview_moveto(1.0)
                return_to_main()
            else:
                Util.notification(4, {"type": "warn", "title": "Already exists", "message": f"The key: {xml_grab_name}\nAlready exists as a\nlink button..."})

        def return_to_main():
            add_link_entry_frame.pack_forget()
            self.set_scroll(self.main_canvas)
            self.stats_frame.pack()

        footer_frame = tb.Frame(add_link_entry_frame)
        tb.Button(footer_frame, text="Cancel", style="warning-outline", command=return_to_main).grid(row=0, column=0, sticky="nsew", padx=5)
        tb.Frame(footer_frame).grid(row=0, column=1, sticky="nsew", padx=152)
        tb.Button(footer_frame, text="Add", style="success-outline", command=add_entry).grid(row=0, column=2, sticky="nsew", padx=5)
        footer_frame.pack(side="bottom", pady=10, expand=True, fill="both")
        add_link_entry_frame.pack(expand=True, fill="both")
        self.set_scroll(canvas, is_horizontal=True)

    def add_frame_entry(self, link_name, link_data):
        def view(name, data):
            Util.notification(999, {"type": "info", "title": "Link args:", "message": f"NAME: {name}\n\n"+"Link:\n"+data.get("link", "None")})

        link_frame = tb.Frame(self.main_frame, relief=RAISED, padding=16)
        tb.Label(link_frame, text=f"{link_name[:20]}{" "*(20-len(link_name))}", font=Util.tk_font("Tm")).pack(anchor="nw", pady=5)
        entry_frame = tb.Frame(link_frame)
        tb.Button(entry_frame, text="VIEW", style=link_data["color"], command=lambda n=link_name, d=link_data: view(n, d)).grid(row=0, column=1, stick="nsew", padx=20)

        def toggle_link(link_key, update_btn):
            if "disabled" in self.save_config["spoiler_links"][link_key].keys():
                self.save_config["spoiler_links"][link_key].pop("disabled")
                update_btn.config(text="Enabled ")
                update_btn.config(bootstyle="success-outline")
            else:
                self.save_config["spoiler_links"][link_key]["disabled"] = True
                update_btn.config(text="Disabled")
                update_btn.config(bootstyle="warning-outline")

        add_btn = tb.Button(entry_frame, text="Enabled ", style="success-outline")
        add_btn.config(command=lambda k=link_name, color_btn=add_btn: toggle_link(k, color_btn))
        if "disabled" in self.save_config["spoiler_links"][link_name].keys():
            add_btn.config(text="Disabled")
            add_btn.config(bootstyle="warning-outline")
        add_btn.grid(row=0, column=2, stick="nsew", padx=20)

        def perma_remove(link_key):
            if Util.notification(3, {"type": "ask", "title": "Permanent removal", "message": f"You are about to remove the\nfollowing link permanently:\n\n{link_key}\nAre you sure you want to proceed?"}, True):
                self.save_config["spoiler_links"].pop(link_key)
                self.redraw()
        del_btn = tb.Button(entry_frame, text="Remove spoiler link", command=lambda k=link_name: perma_remove(k), style="danger-outline")
        del_btn.grid(row=0, column=3, stick="nsew", padx=20)

        entry_frame.pack()
        link_frame.grid(pady=5, row=self.row, column=0, sticky="nsew")
        self.row += 1


class BasicPathEntry(TitledFrame):
    def __init__(self, parent, paths, view_panel, config, redraw, **kwargs):

        super().__init__(parent, "Unlisted Paths:", **kwargs)
        self.stats_frame = tb.Frame(self.content)
        self.stats_frame.pack()

        main_frame = tb.Frame(self.stats_frame)
        main_frame.pack(fill="both", expand=True)

        canvas = tb.Canvas(main_frame)
        canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_y.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scroll_y.set)

        scroll_frame = tb.Frame(canvas)

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        row = 0
        for path in paths:
            def open_world_path(world):
                if not os.path.exists(world):
                    Util.notification(3, {"type": "warn", "title": "Invalid path", "message": f"The following path:\n\n{world}\ndoesnt seem to exist..."})
                    return
                if Util.is_valid_noita_path(world):
                    view_panel(world)
                else:
                    Util.opening_folder(Util.get_valid_folder(world))
            entry_frame = tb.Frame(scroll_frame, relief=RAISED, padding=16)
            tb.Label(entry_frame, text=f"Entry {row+1}:", font=Util.tk_font("Tm")).grid(row=0, column=0, stick="nsew", padx=5)
            view_btn = tb.Button(entry_frame, text="VIEW", command=lambda world=path: open_world_path(world))
            view_btn.config(bootstyle=f"{"primary" if Util.is_valid_noita_path(path) else "warning" if os.path.exists(path) else "danger"}-outline")
            view_btn.grid(row=0, column=1, stick="nsew", padx=5)

            def re_add(world):
                if config["save_management"]["new_save_entries_to_start"]:
                    config["world_paths"].append(world)
                else:
                    config["world_paths"].insert(0, world)
                config["unlisted_paths"].remove(world)
                redraw()
            add_btn = tb.Button(entry_frame, text="Add entry back", command=lambda world=path: re_add(world),style="success-outline")
            add_btn.grid(row=0, column=2, stick="nsew", padx=5)

            def perma_remove(world):
                if Util.notification(3, {"type": "ask", "title": "Permanent removal", "message": f"You are about to remove the\nfollowing path permanently:\n\n{world}\nAre you sure you want to proceed?"}, True):
                    config["unlisted_paths"].remove(world)
                    redraw()
            del_btn = tb.Button(entry_frame, text="Remove entry", command=lambda world=path: perma_remove(world),style="danger-outline")
            del_btn.grid(row=0, column=3, stick="nsew", padx=10)

            entry_frame.grid(pady=5, row=row, column=0)
            row += 1
        self.set_scroll(canvas)


class ModifyModdedStarterArgs(TitledFrame):
    def __init__(self, parent, config, **kwargs):

        super().__init__(parent, "Mod start args:", **kwargs)
        self.stats_frame = tb.Frame(self.content)
        self.stats_frame.pack()
        self.save_config = config
        self.cleanup_args()
        self.mod_and_id_list = Util.list_all_mods_possible(self.save_config)

        menu_button = tb.Menubutton(self.stats_frame, text="Add start argument for:", style="info")
        menu_button.pack()
        menu = tk.Menu(menu_button, tearoff=0)
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        def add_start_argument_for_mod(mod_arg):
            mod_name, mod_id = mod_arg.split("--|--")
            new_entry = {
                "mod_id": mod_id,
                "mod_name": mod_name,
                "looking_for": "",
                "start_noita_too": True,
                "seek_running_name": False,
                "application_path": None,
                "argument_enabled": True
            }
            self.save_config["modded_starter_agrs"].append(new_entry)
            self.add_mod_arg_entry(new_entry, True)

        for mod in self.mod_and_id_list:
            menu.add_command(label="- " + mod.split("--|--")[0], font=Util.tk_font("Tl"), command=lambda m=mod: add_start_argument_for_mod(m))
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        menu_button["menu"] = menu

        main_frame = tb.Frame(self.stats_frame)
        main_frame.pack(fill="both", expand=True)

        canvas = tb.Canvas(main_frame)
        canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_y.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scroll_y.set)

        self.scroll_frame = tb.Frame(canvas)

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.row = 0

        for entry in self.save_config["modded_starter_agrs"]:
            self.add_mod_arg_entry(entry, False)
        self.set_scroll(canvas)

    def add_mod_arg_entry(self, entry, redraw):

        def show(selected_e):
            Util.notification(999, {"type": "info", "title": "MOD ARGS:", "message": f"{"\n\n".join(f"{k}:\n - {v}" for k, v in selected_e.items())}"})

        def remove_mod_arg(row, frame):
            if Util.notification(3, {"type": "ask", "title": "Remove modded starter", "message": f"You are about to remove:\n{self.save_config["modded_starter_agrs"][row]["mod_name"]}\n\nAre you sure you wish to continue?"}):
                self.save_config["modded_starter_agrs"][row]["mod_id"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["mod_name"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["looking_for"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["start_noita_too"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["seek_running_name"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["application_path"] = "MODARGSTOBEREWMOVED"
                self.save_config["modded_starter_agrs"][row]["argument_enabled"] = "MODARGSTOBEREWMOVED"
                frame.grid_forget()
                self.update_idletasks()

        entry_frame = tb.Frame(self.scroll_frame, relief=RAISED, padding=5)
        tb.Label(entry_frame, text=entry["mod_name"]+":", font=Util.tk_font("Tl")).pack(anchor="w")
        config_frame = tb.Frame(entry_frame)

        start_noita_too = tb.BooleanVar(value=self.save_config["modded_starter_agrs"][self.row]["start_noita_too"])
        seek_running_name = tb.BooleanVar(value=self.save_config["modded_starter_agrs"][self.row]["seek_running_name"])

        def toggle_entry_start_noita_too(row):
            self.save_config["modded_starter_agrs"][row]["start_noita_too"] = start_noita_too.get()
        start_noita_too_label = tb.Label(config_frame, text="Run noita as well: ", font=Util.tk_font("Tm"))
        start_noita_too_label.grid(row=0, column=0)
        start_noita_too_cb = tb.Checkbutton(config_frame, style="success-rounded-toggle", variable=start_noita_too, command=lambda r=self.row: toggle_entry_start_noita_too(r))
        start_noita_too_cb.grid(row=0, column=1, padx=5)

        look_for_str = tb.StringVar(value=self.save_config["modded_starter_agrs"][self.row]["looking_for"])
        look_for_entry = tb.Entry(config_frame, textvariable=look_for_str, style="info" if seek_running_name.get() else "dark", width=20, font=Util.tk_font("Tm"))

        def toggle_seek_running_name(row):
            self.save_config["modded_starter_agrs"][row]["seek_running_name"] = seek_running_name.get()
            seek_running_name_label.config(text="Hide NWM while \nmod app is running:")
            look_for_entry.config(bootstyle="info" if seek_running_name.get() else "dark")
        seek_running_name_label = tb.Label(config_frame, text="Hide NWM while \nmod app is running:", font=Util.tk_font("Tm"))
        seek_running_name_label.grid(row=0, column=2)
        seek_running_name_cb = tb.Checkbutton(config_frame, style="info-rounded-toggle", variable=seek_running_name, command=lambda r=self.row: toggle_seek_running_name(r))
        seek_running_name_cb.grid(row=0, column=3, padx=5)

        tb.Label(config_frame, text="Looking for mods\napplication name:", font=Util.tk_font("Tm")).grid(row=2, column=0, pady=5)

        def update_searech_mod_name(row, *args):
            self.save_config["modded_starter_agrs"][row]["looking_for"] = look_for_str.get()

        look_for_str.trace_add("write", lambda *args, r=self.row:update_searech_mod_name(r, *args))

        look_for_entry.grid(row=2, column=2)

        def update_mod_app_path(row):
            path = Util.get_mod_app_path(row, self.save_config)
            if not self.save_config["modded_starter_agrs"][row]["looking_for"]:
                found_name = path.split("/")[-1]
                if found_name.endswith(".exe"):
                    self.save_config["modded_starter_agrs"][row]["looking_for"] = found_name
                    look_for_str.set(found_name)

        tb.Label(config_frame, text="Set a path to\nmod application:", font=Util.tk_font("Tm")).grid(row=1, column=0)
        tb.Button(config_frame, text="Set path", style="primary-outline", command=lambda r=self.row: update_mod_app_path(r)).grid(row=1, column=2, pady=10)
        tb.Frame(config_frame).grid(row=3, column=2, pady=5)

        def toggle_mod_args(row):
            self.save_config["modded_starter_agrs"][row]["argument_enabled"] = not self.save_config["modded_starter_agrs"][row]["argument_enabled"]
            toggle_enable_arg_button.config(text=f"Argument {"Enabled" if self.save_config["modded_starter_agrs"][row]["argument_enabled"] else "Disabled"}")
            toggle_enable_arg_button.config(bootstyle=f"{"success" if self.save_config["modded_starter_agrs"][row]["argument_enabled"] else "warning"}-outline")
        toggle_enable_arg_button = tb.Button(config_frame, text=f"Argument {"Enabled" if self.save_config["modded_starter_agrs"][self.row]["argument_enabled"] else "Disabled"}", style=f"{"success" if self.save_config["modded_starter_agrs"][self.row]["argument_enabled"] else "warning"}-outline", command=lambda row=self.row: toggle_mod_args(row))
        toggle_enable_arg_button.grid(row=4, column=0, sticky="nsew")
        tb.Button(config_frame, text="VIEW", style="primary-outline", command=lambda e=entry: show(e)).grid(row=4, column=1, sticky="nsew")
        tb.Button(config_frame, text="Remove mod arg", style="danger-outline", command=lambda row=self.row, hide=entry_frame: remove_mod_arg(row, hide)).grid(row=4, column=2, sticky="nsew")
        config_frame.pack(side="bottom")
        entry_frame.grid(pady=5, row=self.row, column=0, sticky="w")
        self.row += 1
        if redraw:
            self.update_idletasks()

    def cleanup_args(self):
        remove_idx = []
        for idx, entry in enumerate(self.save_config["modded_starter_agrs"]):
            is_disabled = True
            for v in entry.values():
                is_disabled &= v == "MODARGSTOBEREWMOVED"
            if is_disabled:
                remove_idx.append(idx)
        for i in remove_idx[::-1]:
            self.save_config["modded_starter_agrs"].pop(i)

    def destroy(self):
        self.cleanup_args()
        super().destroy()


class ModifyXMLDataGrabber(TitledFrame):
    def __init__(self, parent, config, **kwargs):

        super().__init__(parent, "Xml Stats Display:", **kwargs)
        self.stats_frame = tb.Frame(self.content)
        self.stats_frame.pack()
        self.save_config = config
        example_xml_files = Util.look_for_good_xml_files(self.save_config["world_paths"])
        self.example_xml_files = {"world_state_": example_xml_files[0], "player_": example_xml_files[1], "stats_": example_xml_files[2], "kills_": example_xml_files[3], "mod_config_": example_xml_files[4], "streaming_event_config_": example_xml_files[5]}
        stats_name_to_data_map = {"world_state_": "Sessions World", "player_": "Sessions Player", "stats_": "Sessions stats", "kills_": "Sessions kills", "mod_config_": "Mod config", "streaming_event_config_": "Streamer config"}
        self.stats_name_to_data_map = {}
        for k, v in self.example_xml_files.items():
            if v:
                self.stats_name_to_data_map[k] = stats_name_to_data_map[k]

        menu_button = tb.Menubutton(self.stats_frame, text="Add stats-grabber for:", style="info")
        menu_button.pack()
        menu = tk.Menu(menu_button, tearoff=0)
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        for raw_path, stat in self.stats_name_to_data_map.items():
            menu.add_command(label="- " + stat, font=Util.tk_font("Tl"), command=lambda file=raw_path: self.add_xml_grabber_entry(file))
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        menu_button["menu"] = menu

        main_frame = tb.Frame(self.stats_frame)
        main_frame.pack(fill="both", expand=True)

        canvas = tb.Canvas(main_frame)
        canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_y.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scroll_y.set)

        self.scroll_frame = tb.Frame(canvas)

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.row = 0

        self.base_canvas = canvas
        self.set_scroll(self.base_canvas)
        for entry in self.save_config["xml_stats_grab"]:
            self.add_xml_arg_entry(entry, False)

    def add_xml_grabber_entry(self, xml_file_selected):
        self.set_scroll(None)
        add_xml_entry_frame = tb.Frame(self.content)
        tb.Label(add_xml_entry_frame, text="Set initial configuration:", font=Util.tk_font("Hm")).pack(anchor="w", pady=25)

        entry_name_var = tb.StringVar()
        entry_append_var = tb.StringVar()

        def limit_string_size(*args):
            value = entry_name_var.get()
            if len(value) > 20:
                entry_name_var.set(value[:20])
            value = entry_append_var.get()
            if len(value) > 10:
                entry_append_var.set(value[:10])

        entry_name_var.trace_add("write", limit_string_size)
        entry_append_var.trace_add("write", limit_string_size)

        tb.Label(add_xml_entry_frame, text="Set Name for the variable\nthat will be grabbed:", font=Util.tk_font("Tl")).pack(expand=True, fill="both")
        entry_name = tb.Entry(add_xml_entry_frame, textvariable=entry_name_var, style="primary", width=20)
        entry_name.pack(pady=15)

        tb.Label(add_xml_entry_frame, text="Provide optional text that will\nbe appended to the xml value:", font=Util.tk_font("Tl")).pack(pady=10, expand=True, fill="both")
        entry_append = tb.Entry(add_xml_entry_frame, textvariable=entry_append_var, style="info", width=10)
        self.stats_frame.pack_forget()
        entry_append.pack()

        def add_entry():
            xml_grab_name = entry_name.get()
            if xml_grab_name.replace(" ", "") == "":
                Util.notification(4, {"type": "warn", "title": "Invalid name", "message": f"No valid name for the new\nxml stat provided..."})
                return
            append_str = entry_append.get()
            final_config_key = xml_file_selected+xml_grab_name+("_APPEND_"+append_str if append_str else "")
            if final_config_key not in self.save_config["xml_stats_grab"].keys():
                self.save_config["xml_stats_grab"][final_config_key] = []
                self.add_xml_arg_entry(final_config_key, True)
                self.canvas.yview_moveto(1.0)
                return_to_main()
            else:
                Util.notification(4, {"type": "warn", "title": "Already exists", "message": f"The key: {final_config_key}\nAlready exists as an argument\nfor an xml stats grabber..."})

        def return_to_main():
            add_xml_entry_frame.pack_forget()
            self.set_scroll(self.base_canvas)
            self.stats_frame.pack()

        footer_frame = tb.Frame(add_xml_entry_frame)
        tb.Button(footer_frame, text="Cancel", style="warning-outline", command=return_to_main).grid(row=0, column=0, sticky="nsew", padx=5)
        tb.Frame(footer_frame).grid(row=0, column=1, sticky="nsew", padx=153)
        tb.Button(footer_frame, text="Add", style="success-outline", command=add_entry).grid(row=0, column=2, sticky="nsew", padx=5)
        footer_frame.pack(side="bottom", pady=14, expand=True, fill="both")
        add_xml_entry_frame.pack(expand=True, fill="both")

    def add_xml_arg_entry(self, entry, redraw):
        self.set_scroll(self.base_canvas)
        display_name = entry
        file_key_name = entry
        for k, v in self.stats_name_to_data_map.items():
            if display_name.startswith(k):
                display_name = display_name.replace(k, "")
                file_key_name = k
                break
        if not entry or "_HIDDEN_" in entry:
            return
        display_name = display_name.replace("_", " ").replace("APPEND ", "(as \"")
        if "(as \"" in display_name:
            display_name += "\")"

        def show(selected_e):
            xml_stat_copy = self.save_config["xml_stats_grab"][selected_e].copy()
            if "HIDDEN_" in xml_stat_copy:
                xml_stat_copy.remove("HIDDEN_")

            Util.notification(999, {"type": "info", "title": "GRABBER DETAILS:", "message": f"Grabber Name:\n{selected_e}\n\nXML KEYS:\n{"\n".join(f"{" "*i*5}{"- "+k}" for i, k in enumerate(xml_stat_copy))}"})

        entry_frame = tb.Frame(self.scroll_frame, relief=RAISED, padding=5)
        top_frame = tb.Frame(entry_frame)
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_rowconfigure(1, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)
        tb.Label(top_frame, text=display_name, font=Util.tk_font("Tl")).grid(row=0, column=0, sticky="nw")
        top_frame.pack(side="top", expand=True, fill="x")
        config_frame = tb.Frame(entry_frame)
        tb.Button(config_frame, text="VIEW", style="primary-outline", command=lambda e=entry: show(e)).grid(row=0, column=0, sticky="nsew", padx=5)
        tb.Button(config_frame, text="Modify", style="info-outline", state="enabled" if self.example_xml_files.get(file_key_name, False) else "disabled", command=lambda e=entry: self.modify_xml_tree(e)).grid(row=0, column=1, sticky="nsew")

        def toggle_xml_stat_show(selected_entry):
            if "HIDDEN_" in self.save_config["xml_stats_grab"][selected_entry]:
                self.save_config["xml_stats_grab"][selected_entry].remove("HIDDEN_")
            else:
                self.save_config["xml_stats_grab"][selected_entry].append("HIDDEN_")
            toggle_xml_button.config(text="Disabled" if "HIDDEN_" in self.save_config["xml_stats_grab"][entry] else "Enabled ")
            toggle_xml_button.config(bootstyle=f"{"warning" if "HIDDEN_" in self.save_config["xml_stats_grab"][entry] else "success"}-outline")
            self.update_idletasks()

        toggle_xml_button = tb.Button(config_frame, text="Disabled" if "HIDDEN_" in self.save_config["xml_stats_grab"][entry] else "Enabled ", style=f"{"warning" if "HIDDEN_" in self.save_config["xml_stats_grab"][entry] else "success"}-outline", command=lambda entry_name=entry: toggle_xml_stat_show(entry_name))
        toggle_xml_button.grid(row=0, column=2, sticky="nsew", padx=5)

        def remove_xml_arg(entry_name, frame):
            if Util.notification(3, {"type": "ask", "title": "Remove xml grabber", "message": f"You are about to remove:\n{entry_name}\n\nAre you sure you wish to continue?"}):
                self.save_config["xml_stats_grab"].pop(entry_name)
                frame.grid_forget()
                self.update_idletasks()

        tb.Button(config_frame, text="Remove xml grabber arg", style="danger-outline", command=lambda entry_name=entry, hide=entry_frame: remove_xml_arg(entry_name, hide), state="disabled" if entry in Util.DEFAULT_CONFIG["xml_stats_grab"].keys() else "enabled").grid(row=0, column=3, sticky="nsew")

        config_frame.pack(side="bottom", anchor="w", pady=10, padx=10)
        entry_frame.grid(pady=5, row=self.row, column=0, sticky="w")
        self.row += 1
        if redraw:
            self.update_idletasks()

    def modify_xml_tree(self, entry, xml_tree_path=None):
        self.set_scroll(None)
        mod_xml_entry_frame = tb.Frame(self.content)
        display_name = entry
        for k, v in self.stats_name_to_data_map.items():
            if display_name.startswith(k):
                display_name = display_name.replace(k, "").replace("_", " ").replace("APPEND ", "")
                break
        tb.Label(mod_xml_entry_frame, text="modifying:", font=Util.tk_font("Ts")).pack(anchor="nw", pady=6)
        tb.Label(mod_xml_entry_frame, text=display_name[:20], font=Util.tk_font("Hm")).pack(anchor="nw", pady=5)
        display_file_name = entry
        file_data = entry
        for k, v in self.stats_name_to_data_map.items():
            if display_file_name.startswith(k):
                display_file_name = v
                file_data = k
                break

        if xml_tree_path:
            base_xml_list = xml_tree_path.copy()
        else:
            base_xml_list = self.save_config["xml_stats_grab"][entry].copy()
        if len(base_xml_list) <= 0:
            base_xml_list = [Util.get_initial_xml_path(self.example_xml_files[file_data])]
        xml_tree_file = Util.get_any_xml_stat(self.example_xml_files[file_data], {"out": base_xml_list.copy()})["out"]
        print_out = []
        end_of_tree = True
        if isinstance(xml_tree_file, str):
            print_out.append([base_xml_list[-1], xml_tree_file[:min(len(xml_tree_file), 17)]])
        if isinstance(xml_tree_file, list):
            print_out.append([base_xml_list[-1], str(xml_tree_file)[:min(len(xml_tree_file)-4, 17)]+"..."])
        if isinstance(xml_tree_file, dict):
            end_of_tree = False
            for tree_key, output_val in xml_tree_file.items():
                if not output_val:
                    output_val = "No data set..."
                if isinstance(output_val, dict):
                    output_val = "\n".join(str(k)+" = " + (str(v)[:min(len(v), 17)] if v else "No data set...") for k, v in output_val.items())
                else:
                    output_val = str(output_val)[:min(len(output_val), 17)]
                print_out.append([tree_key.replace("@", "$"), output_val])

        def change_entry():
            self.save_config["xml_stats_grab"][entry] = base_xml_list
            return_to_main()

        def return_to_main():
            self.end_of_tree = True
            mod_xml_entry_frame.pack_forget()
            self.set_scroll(self.base_canvas)
            self.stats_frame.pack()

        tb.Label(mod_xml_entry_frame, text=f"(for: {display_file_name} xml file)\n", font=Util.tk_font("Hs")).pack(anchor="w", pady=10)

        sub_relief_frame = tb.Frame(mod_xml_entry_frame, relief=GROOVE, padding=5)
        path_str = ("/".join(base_xml_list))[:35]
        tb.Label(sub_relief_frame, text=f"Current xml-path:\n  "+path_str, font=Util.tk_font("Tl")).pack(anchor="w", pady=10)

        def revert_path():
            base_xml_list.pop()
            mod_xml_entry_frame.pack_forget()
            self.modify_xml_tree(entry, base_xml_list)

        xml_path_selection = tb.Frame(sub_relief_frame)
        xml_path_selection.grid_rowconfigure(0, weight=1)
        xml_path_selection.grid_rowconfigure(1, weight=1)
        xml_path_selection.grid_columnconfigure(0, weight=1)
        xml_path_selection.grid_columnconfigure(1, weight=1)
        btn = tb.Button(xml_path_selection, text="previous path" if len(base_xml_list)>1 else "  reset path  ", style="warning-outline", command=revert_path)
        btn.grid(row=0, column=0)
        menu_button = tb.Menubutton(xml_path_selection, text="Available paths:", style="info-outline")
        menu = tk.Menu(menu_button, tearoff=0)
        menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        append = ""
        if "_APPEND_" in entry:
            append = entry.split("_APPEND_")[-1]
        if end_of_tree:
            if print_out:
                print_out = print_out[0][1]
            else:
                print_out = "No data set..."
            menu_button.config(bootstyle="success-outline")
            menu_button.config(text=f"End of xml key:")
            menu.add_command(label=f"    {print_out}{append}    ", font=Util.tk_font("Tl"))
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))
        else:
            for path_entry in print_out:
                def append_new_xml_tree_path(new_xml_key, sub=None):
                    base_xml_list.append(new_xml_key)
                    if sub:
                        base_xml_list.append(sub)
                    mod_xml_entry_frame.pack_forget()
                    self.modify_xml_tree(entry, base_xml_list)
                menu.add_command(label=" - KEY: " + path_entry[0], font=Util.tk_font("Tl"), command=lambda xml_path=path_entry[0]: append_new_xml_tree_path(xml_path))
                if "\n" in path_entry[1]:
                    for line in path_entry[1].split("\n"):
                        if line.startswith("@"):
                            line = "$"+line[1:]
                        sub_path = None
                        if " = " in line:
                            sub_path = line.split(" = ")[0]
                        menu.add_command(label=f"    ({line})", font=Util.tk_font("Ts"), command=lambda xml_path=path_entry[0], sub=sub_path: append_new_xml_tree_path(xml_path, sub))
                else:
                    menu.add_command(label=f"    ({path_entry[1]})", font=Util.tk_font("Ts"), command=lambda xml_path=path_entry[0]: append_new_xml_tree_path(xml_path))
            menu.add_command(label="", state="disabled", font=Util.tk_font("Tm"))

        menu_button["menu"] = menu
        menu_button.grid(row=0, column=1, pady=5)
        xml_path_selection.pack(expand=True, fill="x")
        sub_relief_frame.pack(expand=True, fill="x", pady=20)
        footer_frame = tb.Frame(mod_xml_entry_frame)
        tb.Button(footer_frame, text="Cancel", style="warning-outline", command=return_to_main).grid(row=0, column=0, sticky="nsew", padx=5)
        tb.Frame(footer_frame).grid(row=0, column=1, sticky="nsew", padx=143)
        tb.Button(footer_frame, text="Update", style="success-outline", command=change_entry, state="disabled" if base_xml_list == self.save_config["xml_stats_grab"][entry] else"enabled").grid(row=0, column=2, sticky="nsew", padx=5)
        footer_frame.pack(side="bottom", pady=10, expand=True, fill="both")

        self.stats_frame.pack_forget()
        mod_xml_entry_frame.pack()


class ThreadedWorldsLoader(tb.Frame):
    def __init__(self, parent, path_entries, scrollable_frame, config, play_selected_world, set_world_frame, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.path_entries = path_entries
        self.scrollable_frame = scrollable_frame
        self.save_config = config
        self.play_selected_world = play_selected_world
        self.set_world_frame = set_world_frame
        self.entry_len = len(self.path_entries)
        self.frame_gen_pause = 40
        if self.entry_len > 40:
            scrollable_frame.bulk_population(self.entry_len, 673, 169)
            for x in range(40):
                self.draw_entry(self.path_entries.pop())
            self.after(self.frame_gen_pause, self.threaded_load)
            self.scrollable_frame.refresh()
        else:
            for path in self.path_entries:
                if not os.path.exists(path):
                    if Util.notification(3, {"type": "ask", "title": "Save doesnt exist",
                                           "message": f"Failed to load:\n{path}\n as the path does not exist!\nwould you like to unlist this save?"}):
                        self.save_config["world_paths"].remove(path)
                else:
                    self.scrollable_frame.add_item(WorldBannerFrame(self.parent, path, self.play_selected_world, self.set_world_frame), False, True)
            self.scrollable_frame.refresh()

    def threaded_load(self):
        if (self.entry_len - len(self.path_entries)) % 10 == 0:
            self.scrollable_frame.refresh()
        if len(self.path_entries) <= 0:
            self.scrollable_frame.refresh()
            return
        self.draw_entry(self.path_entries.pop())
        self.after(self.frame_gen_pause, self.threaded_load)

    def draw_entry(self, path):
        if not os.path.exists(path):
            if Util.notification(3, {"type": "ask", "title": "Save doesnt exist",
                                   "message": f"Failed to load:\n{path}\n as the path does not exist!\nwould you like to unlist this save?"}):
                self.save_config["world_paths"].remove(path)
        else:
            widget = WorldBannerFrame(self.parent, path, self.play_selected_world, self.set_world_frame)
            self.scrollable_frame.replace_idx(widget, self.entry_len-(1+len(self.path_entries)), False)


class ThreadedStatsLoader(tb.Frame):
    def __init__(self, parent, world_path, scrollable_frame, config, world_data_grabbed, noita_map=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.world_path = world_path
        self.scrollable_frame = scrollable_frame
        self.world_data_grabbed = world_data_grabbed
        self.noita_map = noita_map
        self.frame_load_delay = 10
        self.frame_redraw_delay = 1000
        self.save_config = config
        self.frame_gen_functions = {"Held wands": self.player_wands_displays,
                                    "Active perks": self.player_perk_displays,
                                    "Death markers": self.death_marker_displays,
                                    "Bone wands": self.bone_wands_displays,
                                    "Gifs": self.recorded_gif_displays,
                                    "Images": self.recorded_img_displays,
                                    "Extra notes": self.extra_notes,
                                    "Latest stats": self.get_player_stats}
        self.sorted_dict = {}
        for frame_id in list(config["enabled_save_displays"].keys()):
            if frame_id in self.frame_gen_functions:
                self.sorted_dict[frame_id] = self.frame_gen_functions[frame_id]

        if FORCE_FRAMES >= 1:
            for x in range(FORCE_FRAMES):
                if len(self.sorted_dict) >= 1:
                    key = next(iter(self.sorted_dict))
                    frame = self.sorted_dict.pop(key)
                    self._draw_iter_frame(key, frame)
                else:
                    break
            self.scrollable_frame.refresh()

        self.was_redrawn_already = False
        self.after(100, self.iter_frame_generation)
        self.after(self.frame_redraw_delay, self.redraw_frame)

    def redraw_frame(self):
        if len(self.sorted_dict) >= 1 and not self.was_redrawn_already:
            self.scrollable_frame.refresh()
            self.was_redrawn_already = True
            self.after(self.frame_redraw_delay, self.redraw_frame)

    def iter_frame_generation(self):
        if len(self.sorted_dict) >= 1:
            key = next(iter(self.sorted_dict))
            frame = self.sorted_dict.pop(key)
            self._draw_iter_frame(key, frame)
            self.was_redrawn_already = False
            self.after(self.frame_load_delay, self.iter_frame_generation)
        if len(self.sorted_dict) == 0 and not self.was_redrawn_already:
            self.scrollable_frame.refresh()
            self.was_redrawn_already = True
            return

    def _draw_iter_frame(self, key, frame):

        if key not in self.save_config["enabled_save_displays"].keys():
            self.save_config["enabled_save_displays"][key] = False
        if self.save_config["enabled_save_displays"][key]:
            try:
                frame()
                return True
            except Exception as e:
                Util.notification(1, {"type": "warn", "title": "Loading Failed!",
                                    "message": f"Failed to load \"{key}\" Frame for:\n{self.world_path}\n...\n{e}"})
                self.failed_frame(key)
                return False
        return None

    def player_wands_displays(self):
        if os.path.exists(self.world_path + "/Nolla_Games_Noita/save00/player.xml") and Util.WAND_STATS_ICON:
            player_stats = Util.get_player_xml_info(self.world_path + "/Nolla_Games_Noita/save00/player.xml", "wands")
            if len(player_stats) >= 1:
                self.scrollable_frame.add_item(WandFrame(self.scrollable_frame, player_stats, random_button=False, selected_index=0), False)

    def player_perk_displays(self):
        if os.path.exists(self.world_path + "/Nolla_Games_Noita/save00/player.xml") and Util.WAND_STATS_ICON:
            player_stats = Util.get_player_xml_info(self.world_path + "/Nolla_Games_Noita/save00/player.xml", "perks")
            perk_reroll_price = 200
            if os.path.exists(self.world_path + "/Nolla_Games_Noita/save00/world_state.xml"):
                perk_reroll_price = 200 * (2 ** Util.get_temple_reroll_count(self.world_path + "/Nolla_Games_Noita/save00/world_state.xml"))
            self.scrollable_frame.add_item(PerkDisplay(self.scrollable_frame.scrollable_frame, player_stats, perk_reroll_price), False)

    def death_marker_displays(self):
        if os.path.exists(self.world_path + "/Nolla_Games_Noita/save00/stats/sessions") and self.noita_map:
            config_path = os.getenv('APPDATA') + r"\Noita_saves"
            self.scrollable_frame.add_item(SessionDisplay(self.scrollable_frame.scrollable_frame, self.world_path + "/Nolla_Games_Noita/save00/stats/sessions", config_path, self.noita_map), False)

    def bone_wands_displays(self):
        bone_path = self.world_path + "/Nolla_Games_Noita/save00/persistent/bones_new"
        if os.path.exists(bone_path) and Util.WAND_STATS_ICON:
            bones = []
            for bone in os.listdir(bone_path):
                bone_xml = bone_path + "\\" + bone.split("/")[-1].split("\\")[-1]
                if bone_xml.endswith(".xml"):
                    bones.append(bone_xml)
            if len(bones) >= 1:
                self.scrollable_frame.add_item(WandFrame(self.scrollable_frame, bones, title="Bone Wand"), False)

    def recorded_gif_displays(self):
        if os.path.exists(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots_animated"):
            paths = []
            for gif in os.listdir(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots_animated"):
                paths.append(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots_animated\\" + gif.split("/")[-1].split("\\")[-1])
            if len(paths) >= 1:
                self.scrollable_frame.add_item(AnimatedGIF(self.scrollable_frame.scrollable_frame, paths), False)

    def recorded_img_displays(self):
        if os.path.exists(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots"):
            paths = []
            for gif in os.listdir(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots"):
                paths.append(self.world_path + "/Nolla_Games_Noita/save_rec/screenshots\\" + gif.split("/")[-1].split("\\")[-1])
            if len(paths) >= 1:
                self.scrollable_frame.add_item(AnimatedGIF(self.scrollable_frame.scrollable_frame, paths), False)

    def extra_notes(self):
        extra_notes = "Write extra notes here..."
        if os.path.exists(self.world_path + "/data.json"):
            with open(self.world_path + "/data.json") as f:
                local_conf = json.load(f)
                if "extra_notes" in local_conf.keys():
                    saved_notes = local_conf["extra_notes"]
                    if saved_notes:
                        extra_notes = saved_notes
        sub_f = ScrollSetElement(self.scrollable_frame.scrollable_frame)
        notes = WorldSaver(sub_f, self.world_path, config_id="extra_notes", frame_size=(620, 470))
        notes.text.config(font=Util.tk_font("Hs"))
        notes.text.config(width=61)
        notes.set_max_height(24)
        notes.text.insert(tk.END, extra_notes)
        notes.pack(padx=15)
        sub_f.set_focus_widget(notes)
        sub_f.set_scroll(notes.canvas)
        self.scrollable_frame.add_item(sub_f, False)

    def get_player_stats(self):
        session_path = self.world_path+"/Nolla_Games_Noita/save00/stats/sessions"
        date = ""
        try:
            if os.path.exists(session_path):
                session_paths = os.listdir(session_path)
                if len(session_paths) >= 1:
                    session_start_time = session_paths[-1].split("-")[0]
                    y,m,d = session_start_time[:4], session_start_time[4:6], session_start_time[6:]
                    date = f" ({d}/{m}/{y})"
        except:
            pass
        self.scrollable_frame.add_item(PlayerStatsDisplay(self.scrollable_frame.scrollable_frame, self.world_data_grabbed, extras=("" if os.path.exists(self.world_path+"/Nolla_Games_Noita/save00/player.xml") else "Previous run stats"+date)), False)

    def failed_frame(self, frame_name="Frame"):
        fr = tb.Frame(self.scrollable_frame.scrollable_frame)
        tb.Label(fr, text="!!!", font=Util.tk_font("Hl"), style="danger-inverse").pack()
        tb.Label(fr, text="Failed to get necessary", font=Util.tk_font("Hm")).pack()
        tb.Label(fr, text=f"data for \"{frame_name}\"", font=Util.tk_font("Hm")).pack()
        tb.Label(fr, text="!!!", font=Util.tk_font("Hl"), style="danger-inverse").pack()
        self.scrollable_frame.add_item(fr, False)


def update_search_term(new_term):
    global WORLD_BANNER_SEARCH_TERM
    if not isinstance(new_term, list):
        reduced_search_string = Util.reduced_string(new_term)
    else:
        reduced_search_string = new_term
    if "-&" in reduced_search_string:
        reduced_search_string = reduced_search_string.split("-&")
    WORLD_BANNER_SEARCH_TERM = reduced_search_string


def update_frame_config_variables(config):
    global SCROLL_FRAME_VISIBILITY
    global PERFECT_WAND_PRINT
    global SCROLL_INTENSITY
    global SCROLL_INVERTED
    global FORCE_FRAMES
    global AUTO_SCROLL

    PERFECT_WAND_PRINT = config["appearance"]["accurate_wand_export"]
    SCROLL_FRAME_VISIBILITY = config["scroll_frame_settings"]["scroll_frame_visibility"]
    SCROLL_INTENSITY = config["scroll_frame_settings"]["scroll_intensity"]
    SCROLL_INVERTED = config["scroll_frame_settings"]["scroll_inverted"]
    AUTO_SCROLL = config["scroll_frame_settings"]["auto_scroll"]
    FORCE_FRAMES = config["enabled_save_displays"]["force_first_frames"]
