import tkinter as tk
import json
from tkinter import ttk
from tkinter import filedialog, messagebox
import shutil
import pygame
import os
import subprocess
from OpenAI.OpenAI import OpenAIChat
from PIL import Image, ImageTk
import create_config
import generate
import sys
from openai import OpenAI
import base64
import time

try:
    import ctypes
    ctypes.windll.gdi32.AddFontResourceW("AlmendraSC-Regular.ttf")
    ctypes.windll.gdi32.AddFontResourceW("BaskervvilleSC-Regular.ttf")
except Exception:
    pass 

# Initialize the pygame mixer
pygame.mixer.init()

# Default
DEFAULT_LOCATION = ''
DEFAULT_BGM = ''
api_key = ''

BG = "#212326"  
BG2 = "#0d0a08"  
ACCENT = "#c0392b"
ACCENT2 = "#8b1a1a"
BORDER = "#7a3c14"
BORDER2 = "#2a1208"
TEXT = "#f0d9b0"
TEXT_MUTED = "#a89880"
TEXT_DIM = "#4a3020"

FONT_CANVAS_TITLE = ("Almendra SC", 48, "bold")
FONT_CANVAS_LABEL = ("Baskervville SC", 28, "bold")
FONT_CANVAS_VAL = ("Baskervville SC", 28)
FONT_CANVAS_BTN = ("Baskervville SC", 24, "bold")
FONT_CANVAS_ITEM = ("Baskervville SC", 24)
FONT_CANVAS_SYMBOL = ("Baskervville SC", 22)

# Parse the configuration file
def parse_config(filename):
    with open(filename, 'r') as file:
        content = file.read()

    sections = content.split('# ')[1:]
    parsed_data = {}
    for section in sections:
        title, *items = section.strip().split('\n')
        parsed_data[title.strip()] = [item.strip() for item in items]

    return parsed_data

# Write to the JSON file
def write_json(selected_scene, selected_show, selected_sound, selected_bgm, selected_style):
    data = {
        "scene": selected_scene.get() or DEFAULT_LOCATION,
        "show": [item for item in selected_show if selected_show[item].get()][:3],
        "sound": selected_sound,  # Directly use the string value of the last clicked sound
        "bgm": selected_bgm.get() or DEFAULT_BGM,
        "style":selected_style.get()
    }
    with open('game/next.json', 'w') as file:
        json.dump(data, file, indent=4)

# Function to play sound
def play_sound(sound_name):
    sound_path = os.path.join('game', 'audio', 'soundeffects', f"{sound_name}.mp3")
    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.play()

def save_api_key(api_key, filename='config.json'):
    data = {'api_key': api_key}

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def read_api_key(filename='config.json'):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump({'api_key' : ''}, f, indent=4)
        return ''

    with open(filename, 'r')as f:
        data = json.load(f)

    api_key = data.get('api_key')
    return api_key

photo = {}

def load_image():
    if "trash" in photo:
        return
    try:
        img = Image.open("resursi_UI/trash.png").convert("RGBA")
        data = img.get_flattened_data()
        new_data = []
        for item in data:
            if item[3] > 0:
                new_data.append((192, 57, 43, item[3]))
            else:
                new_data.append(item)
        img.putdata(new_data)
        resized_img = img.resize((20, 20), Image.LANCZOS)
    except Exception:
        resized_img = Image.new("RGBA", (20, 20), (192, 57, 43, 255))
    photo["trash"] = ImageTk.PhotoImage(resized_img)

# Main GUI Application
class Application(tk.Tk):
    def __init__(self, config_data):
        super().__init__()
        self.after(0, lambda: self.state('zoomed'))
        self.title("TTRPG Game Master Assistant")
        self.config_data = config_data 
        
        self.minsize(1300, 800)

        # Bindovanje resize eventa
        self._resize_job = None
        self.bind("<Configure>", self._schedule_resize)

        # Kreiranje Canvasa umjesto bijelog Frame-a
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=BG)
        self.canvas.pack(fill="both", expand=True)

        # Učitavanje prve pozadine
        self.original_bg = Image.open("resursi_UI/pocetni_ekran/pozadinaSpojena.png")
        self.bg_image = ImageTk.PhotoImage(self.original_bg)
        self.bg_img_item = self.canvas.create_image(0, 0, image=self.bg_image, anchor="nw")

        # Varijable
        self.selected_scene = tk.StringVar()
        self.selected_show = {item: tk.BooleanVar(value=True) for item in config_data['NPCs'] + config_data['Characters']}
        self.selected_sound = ""
        self.selected_bgm = tk.StringVar()
        self.selected_style = tk.StringVar(value="Dark Fantasy")

        self.styles_list = ["High Fantasy", "Dark Fantasy", "Magitech", "Sword & Sorcery"]
        self.style_idx = self.styles_list.index(self.selected_style.get()) if self.selected_style.get() in self.styles_list else 0

        bg_list = self.config_data.get('Backgrounds', [])
        self.bg_idx = 0
        if bg_list:
            if not self.selected_scene.get() in bg_list:
                self.selected_scene.set(bg_list[0])
            self.bg_idx = bg_list.index(self.selected_scene.get())

        bgm_list = self.config_data.get('Background music', [])
        self.bgm_idx = 0
        if bgm_list:
            if not self.selected_bgm.get() in bgm_list:
                self.selected_bgm.set(bgm_list[0])
            self.bgm_idx = bgm_list.index(self.selected_bgm.get())

        # Slanje poruka
        self.send_window = None
        self.send_text_area = None

        # UI elementi
        self.render_ui()

    def _schedule_resize(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, lambda: self._resize_background(event))

    def _resize_background(self, event):
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            new_width = self.winfo_width()
            new_height = self.winfo_height()

            # Resize slike
            resized = self.original_bg.resize((new_width, new_height), Image.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(resized)

            # Postavljanje nove slike
            self.canvas.itemconfig(self.bg_img_item, image=self.bg_image)
            self.render_ui()

    def save_to_history(self, question, answer):
     with open("OpenAI/chat_povijest.txt", "a", encoding="utf-8") as f:
        f.write(f"Upit: {question} \n{answer}\n\n{'-'*50}\n\n")

    def refresh_ui(self):
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                widget.destroy()
        self.render_ui()

    def render_ui(self):
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists(): return
        self.canvas.delete("ui")
        
        w = max(self.winfo_width(), 1300)

        self.canvas.create_text(w//2 + 2, 52, text="TTRPG DM HELPER", font=FONT_CANVAS_TITLE, fill="black", tag="ui")
        self.canvas.create_text(w//2, 50, text="TTRPG DM HELPER", font=FONT_CANVAS_TITLE, fill="#c0392b", tag="ui")

        title_x = 80
        content_x = 420
        line_spacing = 55

        # Pomoćna funkcija za hover efekte
        def make_hover(tag, color_in, color_out):
            self.canvas.tag_bind(tag, "<Enter>", lambda e, t=tag, c=color_in: self.canvas.itemconfig(t, fill=c))
            self.canvas.tag_bind(tag, "<Leave>", lambda e, t=tag, c=color_out: self.canvas.itemconfig(t, fill=c))

        def create_outlined_text(x, y, **kwargs):
            kw_out = kwargs.copy()
            kw_out['fill'] = "black"
            o = 1
            self.canvas.create_text(x-o, y-o, **kw_out)
            self.canvas.create_text(x+o, y-o, **kw_out)
            self.canvas.create_text(x-o, y+o, **kw_out)
            self.canvas.create_text(x+o, y+o, **kw_out)
            return self.canvas.create_text(x, y, **kwargs)

        # Pomoćna funkcija za iscrtavanje karusela
        def draw_carousel(title, ttype, val_text, y, ext=None, section_name=None):
            cg = ("ui", "center_group")
            create_outlined_text(title_x, y, text=title, font=FONT_CANVAS_LABEL, fill="white", anchor="w", tags=cg)
            val_x = content_x
            t_l = create_outlined_text(val_x, y, text="<", font=FONT_CANVAS_LABEL, fill="#c0392b", anchor="w", tags=cg)
            self.canvas.tag_bind(t_l, "<Button-1>", lambda e, t=ttype: self.change_carousel(t, -1))
            make_hover(t_l, "#ff4c4c", "#c0392b")
            
            val_x += 30
            t_v = create_outlined_text(val_x, y, text=f" {val_text} ", font=FONT_CANVAS_VAL, fill="#a89880", anchor="w", tags=cg)
            bbox = self.canvas.bbox(t_v)
            val_x = bbox[2] + 10 if bbox else val_x + 200
            
            t_r = create_outlined_text(val_x, y, text=">", font=FONT_CANVAS_LABEL, fill="#c0392b", anchor="w", tags=cg)
            self.canvas.tag_bind(t_r, "<Button-1>", lambda e, t=ttype: self.change_carousel(t, 1))
            make_hover(t_r, "#ff4c4c", "#c0392b")

            if section_name and ext:
                bbox_r = self.canvas.bbox(t_r)
                btn_x = bbox_r[2] + 30 if bbox_r else val_x + 60
                
                t_add = create_outlined_text(btn_x, y, text="[ADD]", font=FONT_CANVAS_BTN, fill="#c0392b", anchor="w", tags=cg)
                self.canvas.tag_bind(t_add, "<Button-1>", lambda e, s=section_name, _ext=ext: self.insert_file(s, _ext))
                make_hover(t_add, "#ff4c4c", "#c0392b")

                if val_text and val_text != "None":
                    bbox_add = self.canvas.bbox(t_add)
                    del_x = bbox_add[2] + 20 if bbox_add else btn_x + 80
                    t_del = create_outlined_text(del_x, y, text="[ X ]", font=FONT_CANVAS_BTN, fill="#c0392b", anchor="w", tags=cg)
                    self.canvas.tag_bind(t_del, "<Button-1>", lambda e, s=section_name, v=val_text: self.remove_item_from_section(s, v))
                    make_hover(t_del, "#ff4c4c", "#c0392b")

        def draw_list(title, items, is_sound, y_pos, section_name, ext):
            cg = ("ui", "center_group")
            create_outlined_text(title_x, y_pos, text=title, font=FONT_CANVAS_LABEL, fill="white", anchor="w", tags=cg)
            cx = content_x
            
            for idx, item in enumerate(items):
                b1 = create_outlined_text(cx, y_pos, text="[", font=FONT_CANVAS_BTN, fill="white", anchor="w", tags=cg)
                _bb = self.canvas.bbox(b1)
                cx = _bb[2] if _bb else cx + 10
                
                is_sel = self.selected_show[item].get() if item in self.selected_show else True
                t_color = "white" if is_sel else "#605548"
                
                t_name = create_outlined_text(cx, y_pos, text=item.upper() + " ", font=FONT_CANVAS_ITEM, fill=t_color, anchor="w", tags=cg)
                _bb = self.canvas.bbox(t_name)
                if _bb:
                    rect = self.canvas.create_rectangle(_bb[0], _bb[1], _bb[2], _bb[3], fill="", outline="", tags=cg)
                    self.canvas.tag_bind(rect, "<Button-1>", lambda e, i=item: self.toggle_item(i))
                    self.canvas.tag_raise(t_name)

                self.canvas.tag_bind(t_name, "<Button-1>", lambda e, i=item: self.toggle_item(i))
                make_hover(t_name, "#ffffff", t_color)
                
                cx = _bb[2] if _bb else cx + 80
                
                if is_sound:
                    t_play = create_outlined_text(cx, y_pos, text="► ", font=FONT_CANVAS_SYMBOL, fill="#c0392b", anchor="w", tags=cg)
                    self.canvas.tag_bind(t_play, "<Button-1>", lambda e, s=item: self.on_sound_button_click(s))
                    make_hover(t_play, "#ff4c4c", "#c0392b")
                    _bb = self.canvas.bbox(t_play)
                    cx = _bb[2] if _bb else cx + 20
                
                t_del = create_outlined_text(cx, y_pos, text="X", font=FONT_CANVAS_BTN, fill="#c0392b", anchor="w", tags=cg)
                self.canvas.tag_bind(t_del, "<Button-1>", lambda e, i=item, s=section_name: self.remove_item_from_section(s, i))
                make_hover(t_del, "#ff4c4c", "#c0392b")
                _bb = self.canvas.bbox(t_del)
                cx = _bb[2] if _bb else cx + 20

                b2 = create_outlined_text(cx, y_pos, text="]", font=FONT_CANVAS_BTN, fill="white", anchor="w", tags=cg)
                _bb = self.canvas.bbox(b2)
                cx = _bb[2] if _bb else cx + 10
                
                if idx < len(items) - 1:
                    comm = create_outlined_text(cx, y_pos, text=", ", font=FONT_CANVAS_BTN, fill="white", anchor="w", tags=cg)
                    _bb = self.canvas.bbox(comm)
                    cx = _bb[2] if _bb else cx + 15
                
                if cx > w - 150:
                    y_pos += 45
                    cx = content_x
            
            t_add = create_outlined_text(cx, y_pos, text="[ADD]", font=FONT_CANVAS_BTN, fill="#c0392b", anchor="w", tags=cg)
            self.canvas.tag_bind(t_add, "<Button-1>", lambda e, s=section_name, t=ext: self.insert_file(s, t))
            make_hover(t_add, "#ff4c4c", "#c0392b")
            
            _bb = self.canvas.bbox(t_add)
            cx = _bb[2] if _bb else cx + 80
            
            if section_name == "Characters":
                t_create = create_outlined_text(cx + 20, y_pos, text="[CREATE]", font=FONT_CANVAS_BTN, fill="#c0392b", anchor="w", tags=cg)
                self.canvas.tag_bind(t_create, "<Button-1>", lambda e: self.on_create_character())
                make_hover(t_create, "#ff4c4c", "#c0392b")

            return y_pos + line_spacing

        # Iscrtavanje
        start_y = 150
        draw_carousel("Style:", 'style', self.selected_style.get(), start_y)
        draw_carousel("Background:", 'bg', self.selected_scene.get() or "None", start_y + line_spacing, "*.png", "Backgrounds")

        
        curr_y = start_y + line_spacing * 2
        curr_y = draw_list("Characters:", self.config_data.get('Characters', []), False, curr_y, "Characters", "*.png")
        curr_y = draw_list("NPCs:", self.config_data.get('NPCs', []), False, curr_y, "NPCs", "*.png")
        curr_y = draw_list("Sound Effects:", self.config_data.get('Sound effects', []), True, curr_y, "Sound effects", "*.mp3")
        
        draw_carousel("Background Music:", 'bgm', self.selected_bgm.get() or "None", curr_y, "*.mp3", "Background music")

        h = max(self.winfo_height(), 800)
        bbox = self.canvas.bbox("center_group")
        if bbox:
            group_h = bbox[3] - bbox[1]
            avail_h = (h - 150) - 100  
            desired_y = 100 + max(0, avail_h - group_h) // 2
            offset = desired_y - bbox[1]
            if offset != 0:
                self.canvas.move("center_group", 0, offset)

        # Bottom Buttons
        btn_y1 = h - 130 # ASK DM ASSISTANT
        btn_y2 = h - 70  # SAVE and PLAY

        font_bottom = ("Almendra SC", 42, "bold")
        color_shadow = "#000000"
        color_text = "#b01b1b" 
        color_hover = "#ff4c4c"
        
        # ASK DM ASSISTANT
        self.canvas.create_text(82, btn_y1+2, text="ASK DM ASSISTANT", font=font_bottom, fill=color_shadow, anchor="w", tag="ui")
        chat_btn = self.canvas.create_text(80, btn_y1, text="ASK DM ASSISTANT", font=font_bottom, fill=color_text, anchor="w", tag="ui")
        self.canvas.tag_bind(chat_btn, "<Button-1>", lambda e: self.on_send())
        make_hover(chat_btn, color_hover, color_text)

        # SAVE THIS SETUP
        self.canvas.create_text(82, btn_y2+2, text="SAVE THIS SETUP", font=font_bottom, fill=color_shadow, anchor="w", tag="ui")
        save_btn = self.canvas.create_text(80, btn_y2, text="SAVE THIS SETUP", font=font_bottom, fill=color_text, anchor="w", tag="ui")
        self.canvas.tag_bind(save_btn, "<Button-1>", lambda e: self.on_ok())
        make_hover(save_btn, color_hover, color_text)

        # PLAY
        self.canvas.create_text(w - 78, btn_y2+2, text="PLAY", font=font_bottom, fill=color_shadow, anchor="e", tag="ui")
        play_btn = self.canvas.create_text(w - 80, btn_y2, text="PLAY", font=font_bottom, fill=color_text, anchor="e", tag="ui")
        self.canvas.tag_bind(play_btn, "<Button-1>", lambda e: self.on_run())
        make_hover(play_btn, color_hover, color_text)

    def toggle_item(self, item):
        if item in self.selected_show:
            val = self.selected_show[item].get()
            self.selected_show[item].set(not val)
        else:
            self.selected_show[item] = tk.BooleanVar(value=True)
        self.render_ui()

    def change_carousel(self, ttype, delta):
        if ttype == 'style':
            if not self.styles_list: return
            self.style_idx = (self.style_idx + delta) % len(self.styles_list)
            self.selected_style.set(self.styles_list[self.style_idx])
        elif ttype == 'bg':
            lst = self.config_data.get('Backgrounds', [])
            if not lst: return
            self.bg_idx = (self.bg_idx + delta) % len(lst)
            self.selected_scene.set(lst[self.bg_idx])
            # Load new background image
            try:
                path = os.path.join("game", "images", "locations", self.selected_scene.get() + ".png")
                self.original_bg = Image.open(path)
                resized = self.original_bg.resize((self.winfo_width(), self.winfo_height()), Image.LANCZOS)
                self.bg_image = ImageTk.PhotoImage(resized)
                self.canvas.itemconfig(self.bg_img_item, image=self.bg_image)
            except Exception as e:
                print(f"Failed to update background: {e}")
        elif ttype == 'bgm':
            lst = self.config_data.get('Background music', [])
            if not lst: return
            self.bgm_idx = (self.bgm_idx + delta) % len(lst)
            self.selected_bgm.set(lst[self.bgm_idx])
        self.render_ui()

    def convert_to_png(self, file_path):
        """Convert any image file to PNG using ffmpeg, returns new path."""
        base, ext = os.path.splitext(file_path)
        if ext.lower() == '.png':
            return file_path  # already PNG, nothing to do
        
        png_path = base + '.png'
        try:
            img = Image.open(file_path)
            
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            img.save(png_path, "PNG")
            return png_path
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert image:\n{e}")
            return None
    
    def insert_file(self, section_name, type):

        image_sections = ["Characters", "NPCs", "Backgrounds"]
        if section_name in image_sections:
            filetypes = [
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif"),
                ("All files", "*.*")
            ]
        else:
            filetypes = [
                ("Audio files", "*.mp3 *.wav *.ogg"),
                ("All files", "*.*")
            ]

        file_path = filedialog.askopenfilename(title="Odaberi datoteku", filetypes=filetypes)
        if not file_path:
            return

        if section_name in image_sections:
            file_path = self.convert_to_png(file_path)
            if file_path is None:
                return  # neuspjela konverzija

        self.add_item_to_section(section_name, file_path)

    def add_item_to_section(self, section_name, file_path):
        print(section_name)
        # Dohvati path
        name = os.path.splitext(os.path.basename(file_path))[0]

        # Dodaj u config_data
        self.config_data[section_name].append(name)


        # Postavi datoteku u odredjenu mapu
        # Definiraj mapu sekcija i njihovih putanja
        section_paths = {
            "Characters": os.path.join("game", "images", "characters"),
            "NPCs": os.path.join("game", "images", "npcs"),
            "Backgrounds": os.path.join("game", "images", "locations"),
            "Sound effects": os.path.join("game", "audio", "soundeffects"),
            "Background music": os.path.join("game", "audio", "bcgsound")
        }

        # Provjera postoji li odgovarajuci put
        if section_name in section_paths:
            dest_dir = section_paths[section_name]
            dest = os.path.join(dest_dir, os.path.basename(file_path))

            # Provjera da li datoteka već postoji
            if os.path.exists(dest):
                tk.messagebox.showwarning("Datoteka već postoji", f"Datoteka {os.path.basename(file_path)} već postoji u {dest_dir}.")
                return

            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy(file_path, dest)
        if section_name in ["Characters", "NPCs", "Backgrounds"]:
                try:
                    img = Image.open(dest)

                    if section_name == "Backgrounds":
                        # Ukloni transparentnost ako postoji
                        if img.mode in ("RGBA", "LA"):
                            background = Image.new("RGB", img.size, (255, 255, 255))  # bijela pozadina
                            background.paste(img, mask=img.split()[3])  # koristi alpha kanal kao masku
                            img = background
                        else:
                            img = img.convert("RGB")

                        # Prisilno skaliranje na 1280x720 bez zadržavanja omjera
                        img = img.resize((1280, 720), Image.LANCZOS)
                    else:
                        # Ostale sekcije (Characters i NPCs) zadrže omjer
                        max_sizes = {
                            "Characters": (512, 512),
                            "NPCs": (512, 512)
                        }
                        max_size = max_sizes.get(section_name, (512, 512))
                        img.thumbnail(max_size, Image.LANCZOS)

                    img.save(dest)

                except Exception as e:
                    print(f"Greška pri resize-u slike: {e}")

        # Ovo slozi da bude checkbox
        if section_name in ["Characters", "NPCs"]:
            self.selected_show[name] = tk.BooleanVar()

        # Refresh
        regenerate_config(overwrite=True)
        
        self.refresh_ui()

    def on_sound_button_click(self, sound_name):
        self.selected_sound = sound_name  # Update the selected_sound with the clicked sound's name
        play_sound(sound_name)  # Play the sound

    def on_create_character(self):
        selector = tk.Toplevel(self)
        selector.title("Create Character")
        selector.geometry("400x260")
        selector.resizable(False, False)
        selector.transient(self)
        selector.grab_set()
        selector.configure(bg="#282d39")

        ttk.Label(selector, text="Character Type", style="Custom.TLabel", anchor="center").pack(fill="x", padx=30, pady=(20, 0))
        sep = ttk.Separator(selector, orient="horizontal")
        sep.pack(fill="x", padx=30, pady=(4, 16))

        btn_cfg = [
            ("Playable Character", lambda: (selector.destroy(), self._open_playable_character_dialog())),
            ("NPC",                lambda: (selector.destroy(), self._open_stub_dialog("NPC"))),
            ("Monster",            lambda: (selector.destroy(), self._open_stub_dialog("Monster"))),
        ]

        for label, cmd in btn_cfg:
            ttk.Button(selector, text=label, command=cmd, style="Custom.TButton").pack(fill="x", padx=60, pady=6)

    def _open_stub_dialog(self, kind):
        stub = tk.Toplevel(self)
        stub.title(f"Create {kind}")
        stub.geometry("500x320")
        stub.resizable(False, False)
        stub.transient(self)
        stub.grab_set()
        stub.configure(bg="#282d39")

        ttk.Label(stub, text=f"Create {kind}", style="Custom.TLabel", anchor="w").pack(fill="x", padx=20, pady=(16, 0))
        sep = ttk.Separator(stub, orient="horizontal")
        sep.pack(fill="x", padx=20, pady=(4, 8))

        text_box = tk.Text(
            stub, wrap="word", height=10,
            bg="#1e2230", fg="#fbf9f5",
            font=("Arial", 10), relief="flat",
            insertbackground="#fbf9f5"
        )
        text_box.pack(fill="both", expand=True, padx=20)

        foot = tk.Frame(stub, bg="#282d39")
        foot.pack(fill="x", padx=20, pady=10)
        ttk.Button(foot, text="Create", command=stub.destroy, style="Custom.TButton").pack(side="right")

    def _open_playable_character_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Create Character")
        dialog.geometry("800x750")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        dialog.configure(bg="#282d39")

        RACES = ["Human", "Elf", "Dwarf", "Halfling", "Dragonborn", "Tiefling", "Gnome"]
        selected_race = tk.StringVar(value="Human")

        CLASSES = {
            "Martial":        ["Fighter", "Barbarian", "Monk", "Rogue"],
            "Divine":         ["Cleric", "Paladin", "Druid"],
            "Arcane":         ["Wizard", "Sorcerer", "Warlock"],
            "Hybrid/Support": ["Bard", "Ranger", "Artificer"],
        }
        selected_class = tk.StringVar(value="Fighter")

        BACKGROUNDS = {
            "Acolyte":      "You spent your formative years in service to a temple, shrine, monastery, or religious order. Faith guides your actions, whether through prayer, ritual, or devotion to a higher power. You may still serve your deity—or seek your own path beyond doctrine.",
            "Criminal":     "You survived by breaking the law. Thief, smuggler, fence, burglar, assassin, or gang enforcer—life in the shadows taught you to lie, steal, and disappear when trouble came. You know the underworld's codes, contacts, and dangers better than most.",
            "Folk Hero":    "You rose from common roots and earned the love of ordinary people through courage, sacrifice, or rebellion. Perhaps you stood against tyranny, defended your village, or survived impossible odds. To the people, you are a legend.",
            "Noble":        "Born into privilege, wealth, or aristocracy, you were raised among courts, politics, and expectation. You know the customs of high society and the burdens of status. Whether beloved heir, disgraced scion, or runaway noble, your name still carries weight.",
            "Sage":         "Your life was devoted to study, learning, and the pursuit of hidden truths. Libraries, ancient tomes, and forgotten ruins are your domain. Whether scholar, researcher, wizard's apprentice, or historian, your knowledge often surpasses your wisdom.",
            "Soldier":      "You trained for war, serving in a militia, army, mercenary company, or knightly order. Discipline, strategy, and survival were drilled into you through blood and steel. Whether you fought for king, coin, or cause, battle shaped who you are—and the scars you carry prove it.",
            "Outlander":    "The wild places of the world were your home. You grew among untamed forests, mountains, deserts, or tundra far from civilization. Survival, tracking, hunting, and reading nature came easier to you than understanding city folk.",
            "Charlatan":    "Deception is your trade. You forged identities, sold lies as truth, and conned the gullible for profit or survival. Whether swindler, fake noble, fortune teller, or master manipulator, you know how to wear any mask convincingly.",
            "Entertainer":  "You lived to perform. Musician, actor, dancer, storyteller, gladiator, jester, or acrobat—your talents captivated crowds and earned your living. You understand the thrill of applause and the power of performance.",
            "Artisan": "You mastered a craft through years of dedication and labor. Blacksmith, carpenter, alchemist, tailor, mason, jeweler, or other skilled maker—your hands create what others only imagine. Pride in your work defines you.",
            "Hermit": "You lived in seclusion, removed from society for years or decades. Isolation gave you time for reflection, meditation, or dark obsession. During your solitude, you may have discovered a profound truth—or something better left unknown."
        }
        selected_background = tk.StringVar(value="Acolyte")

        for section_title in ["Race", "Class", "Background/History", "Optional additional description"]:
            lbl = ttk.Label(dialog, text=section_title, style="Custom.TLabel", anchor="w")
            lbl.pack(fill="x", padx=30, pady=(15, 0))
            sep = ttk.Separator(dialog, orient="horizontal")
            sep.pack(fill="x", padx=30)

            if section_title == "Race":
                race_frame = ttk.Frame(dialog, style="Custom.TFrame")
                race_frame.pack(fill="x", padx=30, pady=(5, 0))
                for i, race in enumerate(RACES):
                    ttk.Radiobutton(
                        race_frame, text=race,
                        variable=selected_race, value=race,
                        style="Custom.TRadiobutton"
                    ).grid(row=0, column=i, sticky="w", padx=(0, 15))

            elif section_title == "Class":
                class_frame = ttk.Frame(dialog, style="Custom.TFrame")
                class_frame.pack(fill="x", padx=30, pady=(5, 0))
                for col, (group, subclasses) in enumerate(CLASSES.items()):
                    group_lbl = ttk.Label(class_frame, text=group, style="Custom.TLabel",
                                          font=("Arial", 11, "bold"))
                    group_lbl.grid(row=0, column=col, sticky="w", padx=(0, 30), pady=(0, 4))
                    for row, subclass in enumerate(subclasses, start=1):
                        ttk.Radiobutton(
                            class_frame, text=subclass,
                            variable=selected_class, value=subclass,
                            style="Custom.TRadiobutton"
                        ).grid(row=row, column=col, sticky="w", padx=(0, 30))

            elif section_title == "Background/History":
                bg_frame = ttk.Frame(dialog, style="Custom.TFrame")
                bg_frame.pack(fill="x", padx=30, pady=(5, 0))

                list_frame = ttk.Frame(bg_frame, style="Custom.TFrame")
                list_frame.grid(row=0, column=0, sticky="ns", padx=(0, 20))

                desc_frame = ttk.Frame(bg_frame, style="Custom.TFrame")
                desc_frame.grid(row=0, column=1, sticky="nsew")
                bg_frame.columnconfigure(1, weight=1)

                desc_text = tk.Text(
                    desc_frame, wrap="word", height=5, width=35,
                    bg="#1e2230", fg="#fbf9f5",
                    font=("Arial", 10), relief="flat",
                    state="disabled", cursor="arrow"
                )
                desc_text.pack(fill="both", expand=True)

                def update_description(*args):
                    key = selected_background.get()
                    desc = BACKGROUNDS.get(key, "")
                    desc_text.config(state="normal")
                    desc_text.delete("1.0", "end")
                    desc_text.insert("1.0", desc)
                    desc_text.config(state="disabled")

                selected_background.trace_add("write", update_description)

                for i, bg_name in enumerate(BACKGROUNDS):
                    ttk.Radiobutton(
                        list_frame, text=bg_name,
                        variable=selected_background, value=bg_name,
                        style="Custom.TRadiobutton"
                    ).grid(row=i, column=0, sticky="w", pady=1)

                update_description()

            elif section_title == "Optional additional description":
                extra_frame = ttk.Frame(dialog, style="Custom.TFrame")
                extra_frame.pack(fill="x", padx=30, pady=(5, 0))

                extra_text = tk.Text(
                    extra_frame, wrap="word", height=5,
                    bg="#1e2230", fg="#fbf9f5",
                    font=("Arial", 10), relief="flat",
                    insertbackground="#fbf9f5"
                )
                extra_text.pack(fill="x")

        btn_frame = tk.Frame(dialog, bg="#282d39")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)

        def open_custom_input():
            custom_win = tk.Toplevel(dialog)
            custom_win.title("Custom Character Description")
            custom_win.geometry("500x300")
            custom_win.resizable(False, False)
            custom_win.transient(dialog)
            custom_win.grab_set()
            custom_win.configure(bg="#282d39")

            ttk.Label(custom_win, text="Custom Description", style="Custom.TLabel", anchor="w").pack(fill="x", padx=20, pady=(16, 0))
            sep = ttk.Separator(custom_win, orient="horizontal")
            sep.pack(fill="x", padx=20, pady=(4, 8))

            text_box = tk.Text(
                custom_win, wrap="word", height=10,
                bg="#1e2230", fg="#fbf9f5",
                font=("Arial", 10), relief="flat",
                insertbackground="#fbf9f5"
            )
            text_box.pack(fill="both", expand=True, padx=20)

            foot = tk.Frame(custom_win, bg="#282d39")
            foot.pack(fill="x", padx=20, pady=10)
            ttk.Button(foot, text="Confirm", command=custom_win.destroy, style="Custom.TButton").pack(side="right")
        
        def create_image_openai():
            if not api_key:
                messagebox.showerror("API Key Missing", "Please set your OpenAI API key first (click 'ASK DM ASSISTANT').")
                return

            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, "game", "images", "characters")
            os.makedirs(output_dir, exist_ok=True)

            extra = extra_text.get("1.0", "end").strip()
            prompt_parts = [
                f"A {selected_race.get()} {selected_class.get()} character,",
                f"{selected_background.get()} background,",
                "fantasy portrait, cinematic lighting, full body, transparent png background",

            ]
            if extra:
                prompt_parts.append(extra)
            prompt = " ".join(prompt_parts)

            loading = tk.Toplevel(dialog)
            loading.title("Generating...")
            loading.geometry("320x80")
            loading.resizable(False, False)
            loading.transient(dialog)
            loading.grab_set()
            loading.configure(bg="#282d39")
            ttk.Label(loading, text="Generating character image, please wait…",
                      style="Custom.TLabel", anchor="center").pack(expand=True)
            loading.update()

            def do_generate():
                try:
                    client = OpenAI(api_key=api_key)
                    result = client.images.generate(
                        model="gpt-image-1",
                        prompt=prompt,
                        size="1024x1024"
                    )
                    image_base64 = result.data[0].b64_json
                    image_bytes = base64.b64decode(image_base64)
                    filename = f"character_{int(time.time())}.png"
                    file_path = os.path.join(output_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(image_bytes)
                    
                    dialog.after(0, lambda: on_done(file_path, None))
                except Exception as e:
                    dialog.after(0, lambda err=e: on_done(None, str(err)))

            def on_done(file_path, error):
                try:
                    loading.destroy()
                except Exception:
                    pass
                if error:
                    messagebox.showerror("Generation Failed", f"Image generation failed:\n{error}")
                    return
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.config_data.setdefault("Characters", []).append(name)
                self.selected_show[name] = tk.BooleanVar(value=True)
                regenerate_config(overwrite=True)
                self.refresh_ui()
                dialog.destroy()
                messagebox.showinfo("Done", f"Character '{name}' created successfully.")

            import threading
            threading.Thread(target=do_generate, daemon=True).start()



        ttk.Button(btn_frame, text="Custom", command=open_custom_input, style="Custom.TButton").pack(side="right", padx=(0, 24))
        ttk.Button(btn_frame, text="Create", command=create_image_openai, style="Custom.TButton").pack(side="right")

    
        

    def on_ok(self):
        write_json(self.selected_scene, self.selected_show, self.selected_sound, self.selected_bgm, self.selected_style)
        regenerate_config(overwrite=True, style=self.selected_style.get())

    def on_run(self):
        
        if sys.platform.startswith("win"):
            renpy_path = r".\renpy-8.5.2-sdk\renpy.exe"
        else:
            renpy_path = "renpy"
 
    #    renpy_path = create_config.get_or_select_renpy_path()
        current_dir = os.getcwd()

        if renpy_path:
            print(f"Pokretanje Ren'Pya s: {renpy_path}")
            subprocess.Popen([renpy_path, current_dir])
    #    else:
    #        messagebox.showerror("Greška", "RenPy nije odabran. Igra se neće pokrenuti.")
    
    def on_send(self):
        global api_key
        # Ask for key if needed
        if not api_key:
            api_key = OpenAIChat.ask_for_api_key(self)
            with open('config.json','w') as f: json.dump({'api_key':api_key}, f)

        prompt = None
        # If chat window exists, gather prompt; else create window then return
        if self.send_window and self.send_window.winfo_exists():
            prompt = self.text_input.get("1.0","end").strip()
        else:
            self._build_chat_window()
            return  # wait for next click

        if not prompt: return

        style = self.selected_style.get()
        styled_prompt = f"[Setting: {style}]\n{prompt}"

        chat = OpenAIChat(api_key, style=style)
        reply = chat.send_message(prompt)
        self._append_to_chat(prompt, reply)

    def _build_chat_window(self):
        main_w = self.winfo_width()
        main_h = self.winfo_height()
        self.send_window = tk.Toplevel(self)
        self.send_window.title("AI Assistant Chat")
        self.send_window.geometry(f"{main_w-150}x{main_h-150}")
        self.send_window.resizable(False, False)

        bg = Image.open("resursi_UI/OkvirOdgovor.webp")
        bg = bg.resize(((main_w-150), (main_h-150)), Image.LANCZOS)
        bg_photo = ImageTk.PhotoImage(bg)
        canvas = tk.Canvas(self.send_window, width=main_w, height=main_h, highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        canvas.create_image(0,0, image=bg_photo, anchor='nw')
        self.send_window.bg_photo = bg_photo

        margin = 350
        frame_w = main_w - margin -150
        frame_h = main_h - margin -120
        frame = ttk.Frame(canvas)
        canvas.create_window(main_w//2.2, main_h//2.3, window=frame, anchor='center', width=frame_w, height=frame_h)

        # Chat display area 
        resp_scroll = ttk.Scrollbar(frame)
        resp_scroll.pack(side='right', fill='y', pady=(6,0), padx=(0,4))
        chat_height = 14
        self.send_text_area = tk.Text(frame, height=chat_height, wrap='word', yscrollcommand=resp_scroll.set)
        self.send_text_area.pack(fill='both', expand=True, padx=6, pady=(6,0))
        resp_scroll.config(command=self.send_text_area.yview)
        self.send_text_area.tag_configure('bold', font=("TkDefaultFont",10,'bold'))

        # Bottom input and controls
        bottom = ttk.Frame(frame)
        bottom.pack(fill='x', pady=6, padx=6)

        # Input box 
        input_lines = 3
        self.text_input = tk.Text(bottom, height=input_lines, wrap='word')
        self.text_input.pack(side='left', fill='x', expand=True, pady=(0,4))

        send_btn = ttk.Button(bottom, text='Send', command=self.on_send, style='Custom.TButton')
        send_btn.pack(side='right', padx=(4,0), pady=(0,4))

        # History controls 
        hist_frame = ttk.Frame(frame)
        hist_frame.pack(side='bottom', fill='x', padx=6, pady=(0,6))
        ttk.Button(hist_frame, text='Load History', command=self.load_previous_conversation, style='Custom.TButton').pack(side='left')
        ttk.Button(hist_frame, text='Clear History', command=self._clear_history, style='Custom.TButton').pack(side='left', padx=(4,0))

    def _append_to_chat(self, prompt, reply):
        self.send_text_area.insert('end', f"\n\nUpit: {prompt}\n", 'bold')
        self.send_text_area.insert('end', reply)
        self.send_text_area.see('end')
        self.text_input.delete('1.0','end')
        with open("OpenAI/chat_povijest.txt","a",encoding='utf-8') as f:
            f.write(f"Upit: {prompt}\n{reply}\n{'-'*40}\n")

    def load_previous_conversation(self):
        if os.path.exists("OpenAI/chat_povijest.txt"):
            with open("OpenAI/chat_povijest.txt","r",encoding='utf-8') as f:
                data = f.read()
            self.send_text_area.delete('1.0','end')
            self.send_text_area.insert('1.0', data)
        else:
            messagebox.showinfo("Povijest", "Nema povijesti razgovora.")

    def _clear_history(self):
        open("OpenAI/chat_povijest.txt","w").close()
        self.send_text_area.delete('1.0','end')

    # Brisanje fajlova
    def remove_item_from_section(self, section_name, item_name):
        confirm = messagebox.askyesno("Potvrda brisanja", f"Jeste li sigurni da želite obrisati '{item_name}' iz sekcije '{section_name}'?")
        if not confirm:
            return
        if item_name in self.config_data[section_name]:
            self.config_data[section_name].remove(item_name)

            # Mape za fajlove
            section_paths = {
                "Characters": os.path.join("game", "images", "characters"),
                "NPCs": os.path.join("game", "images", "npcs"),
                "Backgrounds": os.path.join("game", "images", "locations"),
                "Sound effects": os.path.join("game", "audio", "soundeffects"),
                "Background music": os.path.join("game", "audio", "bcgsound")
            }

            if section_name in section_paths:
                directory = section_paths[section_name]
                extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".mp3", ".wav"]
                for ext in extensions:
                    file_path = os.path.join(directory, item_name + ext)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        break

            if section_name in ["Characters", "NPCs"]:
                if item_name in self.selected_show:
                    del self.selected_show[item_name]
                    
        self.refresh_ui()

# Run the application

def regenerate_config(overwrite=True, style="High Fantasy"):
    # Step 1: Create (or overwrite) the config file
    create_config.main(overwrite=overwrite)

    # Step 2: Parse the new config
    current_dir = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(current_dir, 'interface.conf')
    data = generate.parse_config(config_file_path)

    # Optional: Extract components (use them or return them)
    characters = data["Characters"]
    npcs = data["NPCs"]
    
    sound_effects = data["Sound effects"]
    backgrounds = data["Backgrounds"]
    bgms = data["Background music"]
    DEFAULT_LOCATION = backgrounds[0] if backgrounds else ""
    DEFAULT_BGM = bgms[0] if bgms else ""
    
    characters, npcs, sound_effects, backgrounds, bgms = data[ "Characters" ], data[ "NPCs" ], data[ "Sound effects" ], data[ "Backgrounds" ], data[ "Background music" ]
    
    generate.generate_script(characters, npcs, backgrounds, current_dir, True, style=style)

    return data

if __name__ == "__main__":
    config = regenerate_config(overwrite=True)
    app = Application(config)
    api_key = read_api_key()
    app.mainloop()
