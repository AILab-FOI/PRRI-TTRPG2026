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

# Initialize the pygame mixer
pygame.mixer.init()

# Default
DEFAULT_LOCATION = ''
DEFAULT_BGM = ''
api_key = ''

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
    img = Image.open("resursi_UI/trash.png")
    resized_img = img.resize((20, 20))
    photo["trash"] = ImageTk.PhotoImage(resized_img)

# Main GUI Application
class Application(tk.Tk):
    def __init__(self, config_data):
        super().__init__()
        self.title("TTRPG Game Master Assistant")
        self.config_data = config_data 
        
        self.minsize(1300, 800)

        # Bindovanje resize eventa
        self._resize_job = None
        self.bind("<Configure>", self._schedule_resize)

        # Glavni frame (bijeli prozor iznad pozadine)
        self.main_frame = tk.Frame(self, bg="white")
        self.main_frame.pack(fill="both", expand=True)

        # Varijable
        self.selected_scene = tk.StringVar()
        self.selected_show = {item: tk.BooleanVar() for item in config_data['NPCs'] + config_data['Characters']}
        self.selected_sound = ""
        self.selected_bgm = tk.StringVar()
        self.selected_style = tk.StringVar(value="High Fantasy")

        # Slanje poruka
        self.send_window = None
        self.send_text_area = None

        # Stil
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # UI elementi
        self.create_frames()

    def _schedule_resize(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, lambda: self._resize_background(event))

    def _resize_background(self, event):
        if self.bg_label.winfo_exists():
            new_width = event.width
            new_height = event.height

            # Resize slike
            resized = self.original_bg.resize((new_width, new_height), Image.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(resized)

            # Postavljanje nove slike
            self.bg_label.config(image=self.bg_image)
            self.bg_label.image = self.bg_image 

    def save_to_history(self, question, answer):
     with open("OpenAI/chat_povijest.txt", "a", encoding="utf-8") as f:
        f.write(f"Upit: {question} \n{answer}\n\n{'-'*50}\n\n")

    def refresh_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.create_frames()

    def convert_to_png(self, file_path):
        """Convert any image file to PNG using ffmpeg, returns new path."""
        base, ext = os.path.splitext(file_path)
        if ext.lower() == '.png':
            return file_path  # already PNG, nothing to do
        
        png_path = base + '.png'
        try:
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', file_path, png_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if result.returncode != 0:
                messagebox.showerror("Conversion Error", f"ffmpeg failed to convert:\n{file_path}")
                return None
            return png_path
        except FileNotFoundError:
            messagebox.showerror("ffmpeg Not Found", "ffmpeg is not installed or not in PATH.")
            return None
    
    def insert_file(self, section_name, type):

        image_sections = ["Characters", "NPCs", "Backgrounds"]
        if section_name in image_sections:
            filetypes = [
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif"),
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

    def create_frames(self):
        
        style = ttk.Style()
        style.theme_use('default')

        style.configure("Custom.TFrame", 
            background="#282d39")

        style.configure("Custom.TLabel", 
            background="#282d39", 
            foreground="#fbf9f5", 
            font=("Arial", 24, "bold"))
        
        style.configure("Custom.TButton",
            background="#91b8db",
            foreground="#282d39",
            font=("Arial", 10, 'bold'))
        
        style.configure("Image.TButton",
            background="#e15656",
            foreground="#fbf9f5",
            font=("Arial", 10, 'bold'))
        
        style.configure("Custom.TCheckbutton",
            background="#282d39",
            foreground="#fbf9f5",
            font=("Arial", 10, 'bold'))
        
        style.configure("Custom.TRadiobutton",
            background="#282d39",
            foreground="#fbf9f5",
            font=("Arial", 10, 'bold'))
        
        # Učitavanje pozadine
        self.original_bg = Image.open("resursi_UI/pozadina.png")
        self.bg_image = ImageTk.PhotoImage(self.original_bg)

        # Label za pozadinu
        self.bg_label = tk.Label(self, image=self.bg_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_label.image = self.bg_image
        
        padding_frame = ttk.Frame(self, style="Custom.TFrame", height=10, width=1)
        padding_frame.pack(side="top", pady=65)

        # Glavni frame koji drži sve
        main_frame = ttk.Frame(self, style="Custom.TFrame")
        main_frame.place(relx=0.1, rely=0.1, anchor="w")

        # Frame za tekst (naslov aplikacije)
        title_frame = ttk.Frame(main_frame, style="Custom.TFrame")
        title_frame.pack(side="left", padx=(0,0))

        # Dodaj tekst (naslov aplikacije)
        title_label = ttk.Label(title_frame, text="TTRPG Game Master Assistant", style="Custom.TLabel")
        title_label.pack()

        # Frame za gumbe
        button_frame1 = ttk.Frame(main_frame, style="Custom.TFrame")
        button_frame1.pack(side="right", padx=(400, 0))

        # Dodaj gumbe
        btn_ok = ttk.Button(button_frame1, text="OK", command=self.on_ok, style="Custom.TButton")
        btn_ok.pack(side="left", padx=5)

        btn_run = ttk.Button(button_frame1, text="Run game", command=self.on_run, style="Custom.TButton")
        btn_run.pack(side="left", padx=5)
        
        self.create_style_frame()
        self.create_option_frame("Backgrounds", self.selected_scene, self.config_data['Backgrounds'], "*.png")
        self.create_check_frame("Characters", self.selected_show, self.config_data['Characters'])
        self.create_check_frame("NPCs", self.selected_show, self.config_data['NPCs'])
        self.create_sound_effects_frame("Sound effects", self.config_data['Sound effects'])
        self.create_option_frame("Background music", self.selected_bgm, self.config_data['Background music'], "*.mp3")

        # AI assistent frame
        bottom_frame = ttk.Frame(self, style="Custom.TFrame")
        bottom_frame.pack(side="bottom", fill="x", padx=50, pady=(10, 110))

        label = ttk.Label(bottom_frame, text="Ask Dungeon Master Assistent", style="Custom.TLabel")
        label.pack(anchor="w", pady=(0, 5))

        send_button = ttk.Button(bottom_frame, text="Open Chat", command=self.on_send,  style="Custom.TButton")
        send_button.pack(side="left")

        # OK Button


    def create_style_frame(self):
        STYLES = ["High Fantasy", "Dark Fantasy", "Magitech", "Sword & Sorcery"]

        title_label = ttk.Label(self, text="Style / Setting", style="Custom.TLabel", anchor="w")
        title_label.pack(fill="x", padx=50, pady=(5, 0))

        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=50)

        frame = ttk.Frame(self, style="Custom.TFrame")
        frame.pack(fill='both', expand=True, padx=50, pady=(0, 5))

        for i, style in enumerate(STYLES):
            ttk.Radiobutton(
                frame,
                text=style,
                variable=self.selected_style,
                value=style,
                style="Custom.TRadiobutton"
            ).grid(row=0, column=i, sticky='w', padx=(0, 20))

    def create_check_frame(self, title, variable_dict, options):
        
        title_label = ttk.Label(self, text=title, style="Custom.TLabel", anchor="w")
        title_label.pack(fill="x", padx=50, pady=(5, 0))  # Only top padding
        
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=50)  # Padding bottom only
        
        frame = ttk.Frame(self, style="Custom.TFrame")
        frame.pack(fill='both', expand=True, padx=50, pady=(0, 5))

        for i, option in enumerate(options):
            # Modifikacije za brisanje uz svaku opciju
            row = i // 6
            col = (i % 6) * 2
            load_image()
            ttk.Checkbutton(frame, text=option, variable=variable_dict[option], style="Custom.TCheckbutton").grid(row=row, column=col, sticky='w')
            del_button = ttk.Button(frame, image=photo["trash"], command=lambda opt=option: self.remove_item_from_section(title, opt), style='Image.TButton')
            del_button.image = photo["trash"]
            del_button.grid(row=row, column=col + 1, sticky='w', padx=5)

        # Umetni gumb (nemojte ovo mjenjati bez da proučite kako funkcionira!)
        num_columns = 13
        type = "*.png"
        insert_button = ttk.Button(frame, text="Add", command=lambda: self.insert_file(title, type), style='Custom.TButton')
        insert_button.grid(row=0, column=num_columns - 1, sticky='e', padx=(40, 5))

    def create_option_frame(self, title, variable, options, type):
        
        title_label = ttk.Label(self, text=title, style="Custom.TLabel", anchor="w")
        title_label.pack(fill="x", padx=50, pady=(5, 0))  # Only top padding
        
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=50)  # Padding bottom only
        
        frame = ttk.Frame(self, style="Custom.TFrame")
        frame.pack(fill='both', expand=True, padx=50, pady=(0, 5))
        
        for i, option in enumerate(options):
            # Modifikacije za brisanje uz svaku opciju
            row = i // 6
            col = (i % 6) * 2
            load_image()
            ttk.Radiobutton(frame, text=option, variable=variable, value=option, style='Custom.TRadiobutton').grid(row=row, column=col, sticky='w')
            del_button = ttk.Button(frame, image=photo["trash"], command=lambda opt=option: self.remove_item_from_section(title, opt), style='Image.TButton')
            del_button.image = photo["trash"]
            del_button.grid(row=row, column=col + 1, sticky='w', padx=5)

        # Umetni gumb (nemojte ovo mjenjati bez da proučite kako funkcionira!)
        num_columns = 13
        #type = "*.png"
        insert_button = ttk.Button(frame, text="Add", command=lambda: self.insert_file(title, type), style='Custom.TButton')
        insert_button.grid(row=0, column=num_columns - 1, sticky='e', padx=(40, 5))

    def create_sound_effects_frame(self, title, options):
        
        title_label = ttk.Label(self, text=title, style="Custom.TLabel", anchor="w")
        title_label.pack(fill="x", padx=50, pady=(5, 0))  # Only top padding
        
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=50)  # Padding bottom only
        
        frame = ttk.Frame(self, style="Custom.TFrame")
        frame.pack(fill='both', expand=True, padx=50, pady=(0, 5))
        
        for i, option in enumerate(options):
            # Modificirano za brisanje
            row = i // 6
            col = (i % 6) * 2
            load_image()
            play_button = ttk.Button(frame, text=option, command=lambda opt=option: self.on_sound_button_click(opt), style="Custom.TButton")
            play_button.grid(row=row, column=col, sticky='w')
            del_button = ttk.Button(frame, image=photo["trash"], command=lambda opt=option: self.remove_item_from_section(title, opt), style="Image.TButton")
            del_button.image = photo["trash"]
            del_button.grid(row=row, column=col + 1, sticky='w', padx=5)

        
       # Umetni gumb (nemojte ovo mjenjati bez da proučite kako funkcionira!)
        num_columns = 13
        type = "*.mp3"
        insert_button = ttk.Button(frame, text="Add", command=lambda: self.insert_file(title, type), style="Custom.TButton")
        insert_button.grid(row=0, column=num_columns - 1, sticky='e', padx=(40, 5))

    def on_sound_button_click(self, sound_name):
        self.selected_sound = sound_name  # Update the selected_sound with the clicked sound's name
        play_sound(sound_name)  # Play the sound

    def on_ok(self):
        write_json(self.selected_scene, self.selected_show, self.selected_sound, self.selected_bgm, self.selected_style)
        regenerate_config(overwrite=True, style=self.selected_style.get())

    def on_run(self):
        
        if sys.platform.startswith("win"):
            #renpy_path = r".\renpy-8.5.2-sdk\renpy.exe"
            renpy_path=r"C:\Users\david\Downloads\renpy-8.3.7-sdk\renpy-8.3.7-sdk\renpy.exe"
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
    DEFAULT_LOCATION = backgrounds[ 0 ]
    DEFAULT_BGM = bgms[ 0 ]
    
    characters, npcs, sound_effects, backgrounds, bgms = data[ "Characters" ], data[ "NPCs" ], data[ "Sound effects" ], data[ "Backgrounds" ], data[ "Background music" ]
    
    generate.generate_script(characters, npcs, backgrounds, current_dir, True, style=style)

    return data

if __name__ == "__main__":
    config = regenerate_config(overwrite=True)
    app = Application(config)
    api_key = read_api_key()
    app.mainloop()
