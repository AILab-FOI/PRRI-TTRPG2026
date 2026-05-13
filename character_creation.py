import tkinter as tk
from tkinter import ttk, messagebox
import os
import base64
import time
import threading
from PIL import Image, ImageTk
from openai import OpenAI

def center_window(win, w, h):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")


def open_create_character_selector(app, get_api_key, regenerate_config):
    selector = tk.Toplevel(app)
    selector.title("Create Character")
    center_window(selector, 400, 260)
    selector.resizable(False, False)
    selector.transient(app)
    selector.grab_set()
    selector.configure(bg="#282d39")

    ttk.Label(selector, text="Character Type", style="Custom.TLabel", anchor="center").pack(fill="x", padx=30, pady=(20, 0))
    ttk.Separator(selector, orient="horizontal").pack(fill="x", padx=30, pady=(4, 16))

    btn_cfg = [
        ("Playable Character", lambda: (selector.destroy(), _open_playable_character_dialog(app, get_api_key, regenerate_config))),
        ("NPC",                lambda: (selector.destroy(), _open_stub_dialog(app, "NPC", get_api_key, regenerate_config))),
        ("Background",         lambda: (selector.destroy(), _open_stub_dialog(app, "Background", get_api_key, regenerate_config))),
    ]

    for label, cmd in btn_cfg:
        ttk.Button(selector, text=label, command=cmd, style="Custom.TButton").pack(fill="x", padx=60, pady=6)


def _open_stub_dialog(app, kind, get_api_key, regenerate_config):
    stub = tk.Toplevel(app)
    stub.title(f"Create {kind}")
    center_window(stub, 500, 320)
    stub.resizable(False, False)
    stub.transient(app)
    stub.grab_set()
    stub.configure(bg="#282d39")

    ttk.Label(stub, text=f"Create {kind}", style="Custom.TLabel", anchor="w").pack(fill="x", padx=20, pady=(16, 0))
    ttk.Separator(stub, orient="horizontal").pack(fill="x", padx=20, pady=(4, 8))

    text_box = tk.Text(
        stub, wrap="word", height=10,
        bg="#1e2230", fg="#fbf9f5",
        font=("Arial", 10), relief="flat",
        insertbackground="#fbf9f5"
    )
    text_box.pack(fill="both", expand=True, padx=20)

    foot = tk.Frame(stub, bg="#282d39")
    foot.pack(fill="x", padx=20, pady=10)

    def on_create():
        if kind == "Background":
            user_prompt = text_box.get("1.0", "end").strip()
            if not user_prompt:
                messagebox.showerror("Empty Prompt", "Please provide a description before generating.")
                return
            _generate_background_image(app, user_prompt, stub, get_api_key, regenerate_config)
        else:
            stub.destroy()

    ttk.Button(foot, text="Create", command=on_create, style="Custom.TButton").pack(side="right")


def _generate_background_image(app, user_prompt, close_window, get_api_key, regenerate_config):
    api_key = get_api_key()
    if not api_key:
        messagebox.showerror("API Key Missing", "Please set your OpenAI API key first (click 'ASK DM ASSISTANT').")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "game", "images", "locations")
    os.makedirs(output_dir, exist_ok=True)

    prompt = (
        f"A fantasy background scenery, no characters, wide cinematic landscape, "
        f"highly detailed environment art. {user_prompt}"
    )

    loading = tk.Toplevel(close_window)
    loading.title("Generating...")
    loading.geometry("320x80")
    loading.resizable(False, False)
    loading.transient(close_window)
    loading.grab_set()
    loading.configure(bg="#282d39")
    ttk.Label(loading, text="Generating background image, please wait…",
              style="Custom.TLabel", anchor="center").pack(expand=True)
    loading.update()

    def do_generate():
        try:
            client = OpenAI(api_key=api_key)
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1536x1024"
            )
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
            filename = f"background_{int(time.time())}.png"
            file_path = os.path.join(output_dir, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            img = Image.open(file_path).convert("RGB")
            img = img.resize((1280, 720), Image.LANCZOS)
            img.save(file_path, "PNG")
            app.after(0, lambda: on_done(file_path, None))
        except Exception as e:
            app.after(0, lambda err=e: on_done(None, str(err)))

    def on_done(file_path, error):
        try:
            loading.destroy()
        except Exception:
            pass
        if error:
            messagebox.showerror("Generation Failed", f"Image generation failed:\n{error}")
            return
        name = os.path.splitext(os.path.basename(file_path))[0]
        app.config_data.setdefault("Backgrounds", []).append(name)
        bg_list = app.config_data["Backgrounds"]
        app.bg_idx = bg_list.index(name)
        app.selected_scene.set(name)
        regenerate_config(overwrite=True)
        try:
            app.original_bg = Image.open(file_path)
            resized = app.original_bg.resize((app.winfo_width(), app.winfo_height()), Image.LANCZOS)
            app.bg_image = ImageTk.PhotoImage(resized)
            app.canvas.itemconfig(app.bg_img_item, image=app.bg_image)
        except Exception:
            pass
        app.refresh_ui()
        try:
            close_window.destroy()
        except Exception:
            pass
        messagebox.showinfo("Done", f"Background '{name}' created successfully.")

    threading.Thread(target=do_generate, daemon=True).start()


def _open_playable_character_dialog(app, get_api_key, regenerate_config):
    dialog = tk.Toplevel(app)
    dialog.title("Create Character")
    center_window(dialog, 800, 750)
    dialog.resizable(False, False)
    dialog.transient(app)
    dialog.grab_set()

    bg_path = "resursi_UI/kreiranje_likova/pozadina_kreiranje_karaktera.png"

    off = ImageTk.PhotoImage(Image.open("resursi_UI/kreiranje_likova/gumb2.png").resize((15, 15)))
    on  = ImageTk.PhotoImage(Image.open("resursi_UI/kreiranje_likova/gumb1.png").resize((15, 15)))
    dialog.radio_off = off
    dialog.radio_on  = on

    create_btn_img = ImageTk.PhotoImage(Image.open("resursi_UI/kreiranje_likova/CreateBtn.png").resize((120, 40), Image.LANCZOS))
    custom_btn_img = ImageTk.PhotoImage(Image.open("resursi_UI/kreiranje_likova/CustomBtn.png").resize((120, 40), Image.LANCZOS))
    dialog.create_btn_img = create_btn_img
    dialog.custom_btn_img = custom_btn_img

    canvas = tk.Canvas(dialog, width=800, height=750, highlightthickness=0)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)

    try:
        bg_img = Image.open(bg_path).resize((800, 750), Image.LANCZOS)
        bg_photo = ImageTk.PhotoImage(bg_img)
        canvas.create_image(0, 0, image=bg_photo, anchor="nw")
        dialog.bg_photo = bg_photo
    except Exception:
        pass

    RACES = ["Human", "Elf", "Dwarf", "Halfling", "Dragonborn", "Tiefling", "Gnome"]
    selected_race = tk.StringVar(value="Human")

    CLASSES = {
        "Martial":        ["Fighter", "Barbarian", "Monk"],
        "Divine":         ["Cleric", "Paladin", "Druid"],
        "Arcane":         ["Wizard", "Sorcerer", "Warlock"],
        "Hybrid/Support": ["Bard", "Ranger", "Artificer"],
    }
    selected_class = tk.StringVar(value="Fighter")

    BACKGROUNDS = {
        "Acolyte":     "You spent your formative years in service to a temple, shrine, monastery, or religious order. Faith guides your actions, whether through prayer, ritual, or devotion to a higher power. You may still serve your deity—or seek your own path beyond doctrine.",
        "Criminal":    "You survived by breaking the law. Thief, smuggler, fence, burglar, assassin, or gang enforcer—life in the shadows taught you to lie, steal, and disappear when trouble came. You know the underworld's codes, contacts, and dangers better than most.",
        "Folk Hero":   "You rose from common roots and earned the love of ordinary people through courage, sacrifice, or rebellion. Perhaps you stood against tyranny, defended your village, or survived impossible odds. To the people, you are a legend.",
        "Noble":       "Born into privilege, wealth, or aristocracy, you were raised among courts, politics, and expectation. You know the customs of high society and the burdens of status. Whether beloved heir, disgraced scion, or runaway noble, your name still carries weight.",
        "Sage":        "Your life was devoted to study, learning, and the pursuit of hidden truths. Libraries, ancient tomes, and forgotten ruins are your domain. Whether scholar, researcher, wizard's apprentice, or historian, your knowledge often surpasses your wisdom.",
        "Soldier":     "You trained for war, serving in a militia, army, mercenary company, or knightly order. Discipline, strategy, and survival were drilled into you through blood and steel. Whether you fought for king, coin, or cause, battle shaped who you are—and the scars you carry prove it.",
        "Outlander":   "The wild places of the world were your home. You grew among untamed forests, mountains, deserts, or tundra far from civilization. Survival, tracking, hunting, and reading nature came easier to you than understanding city folk.",
        "Charlatan":   "Deception is your trade. You forged identities, sold lies as truth, and conned the gullible for profit or survival. Whether swindler, fake noble, fortune teller, or master manipulator, you know how to wear any mask convincingly.",
        "Entertainer": "You lived to perform. Musician, actor, dancer, storyteller, gladiator, jester, or acrobat—your talents captivated crowds and earned your living. You understand the thrill of applause and the power of performance.",
        "Artisan":     "You mastered a craft through years of dedication and labor. Blacksmith, carpenter, alchemist, tailor, mason, jeweler, or other skilled maker—your hands create what others only imagine. Pride in your work defines you.",
        "Hermit":      "You lived in seclusion, removed from society for years or decades. Isolation gave you time for reflection, meditation, or dark obsession. During your solitude, you may have discovered a profound truth—or something better left unknown.",
    }
    selected_background = tk.StringVar(value="Acolyte")

    W, H  = 800, 750
    PAD   = 35
    CW    = W - PAD * 2
    TOP   = 15
    BOT   = 690
    UH    = BOT - TOP

    Y_RACE  = TOP
    Y_CLASS = TOP + int(UH * 0.10)
    Y_HIST  = TOP + int(UH * 0.40)
    Y_DESC  = TOP + int(UH * 0.80)
    TH      = 22

    DF_TITLE = ("Baskervville SC", 13, "bold")
    DF_ITEM  = ("Baskervville SC", 10)
    DF_GROUP = ("Baskervville SC", 10, "bold")

    def sec_title(text, y):
        canvas.create_text(PAD, y, text=text, font=DF_TITLE, fill="white", anchor="nw", tags="dlg")
        canvas.create_line(PAD, y + TH - 2, W - PAD, y + TH - 2, fill="white", tags="dlg")

    def draw_race():
        canvas.delete("race_sec")
        sec_title("Race", Y_RACE)
        sp   = 90
        rb_y = Y_RACE + TH + 4
        for i, race in enumerate(RACES):
            x   = PAD + sp * i + sp // 2
            img = on if selected_race.get() == race else off
            tag = f"rr_{race}"
            canvas.create_image(x, rb_y, image=img, anchor="n", tags=("race_sec", tag))
            canvas.create_text(x, rb_y + 18, text=race, font=DF_ITEM, fill="white",
                               anchor="n", tags=("race_sec", f"rl_{race}"))

            def _sel(e, r=race):
                selected_race.set(r)
                draw_race()

            for t in (tag, f"rl_{race}"):
                canvas.tag_bind(t, "<Button-1>", _sel)
                canvas.tag_bind(t, "<Enter>", lambda e: canvas.config(cursor="hand2"))
                canvas.tag_bind(t, "<Leave>", lambda e: canvas.config(cursor=""))

    draw_race()

    def draw_class():
        canvas.delete("class_sec")
        sec_title("Class", Y_CLASS)
        col_w = CW // 4
        for ci, (group, subs) in enumerate(CLASSES.items()):
            xc = PAD + col_w * ci + 10
            canvas.create_text(xc, Y_CLASS + TH + 4, text=group, font=DF_GROUP,
                               fill="white", anchor="nw", tags="class_sec")
            for ri, sub in enumerate(subs):
                ys  = Y_CLASS + TH + 53 + ri * 46
                img = on if selected_class.get() == sub else off
                tag = f"cr_{sub}"
                canvas.create_image(xc, ys, image=img, anchor="w", tags=("class_sec", tag))
                canvas.create_text(xc + 20, ys, text=sub, font=DF_ITEM,
                                   fill="white", anchor="w", tags=("class_sec", f"cl_{sub}"))

                def _sel(e, s=sub):
                    selected_class.set(s)
                    draw_class()

                for t in (tag, f"cl_{sub}"):
                    canvas.tag_bind(t, "<Button-1>", _sel)
                    canvas.tag_bind(t, "<Enter>", lambda e: canvas.config(cursor="hand2"))
                    canvas.tag_bind(t, "<Leave>", lambda e: canvas.config(cursor=""))

    draw_class()

    h_h     = int(UH * 0.40)
    LEFT_W  = 155
    RIGHT_X = PAD + LEFT_W + 8
    RIGHT_W = CW - LEFT_W - 8
    panel_y = Y_HIST + TH + 4
    panel_h = h_h - TH - 8

    sec_title("Background / History", Y_HIST)

    desc_text = tk.Text(canvas, wrap="word", bg="#0d0a08", fg="white", font=DF_ITEM,
                        relief="flat", state="disabled", cursor="arrow",
                        insertbackground="white", highlightthickness=1, highlightbackground="white")
    canvas.create_window(RIGHT_X + 4, panel_y + 4, window=desc_text,
                         anchor="nw", width=RIGHT_W - 8, height=panel_h - 8, tags="dlg")

    def update_desc(*_):
        desc_text.config(state="normal")
        desc_text.delete("1.0", "end")
        desc_text.insert("1.0", BACKGROUNDS.get(selected_background.get(), ""))
        desc_text.config(state="disabled")

    selected_background.trace_add("write", update_desc)

    def draw_history():
        canvas.delete("hist_sec")
        item_h = panel_h // len(BACKGROUNDS)
        for i, bg_name in enumerate(BACKGROUNDS):
            y_btn = panel_y + i * item_h + item_h // 2
            img   = on if selected_background.get() == bg_name else off
            tag   = f"hr_{bg_name}"
            canvas.create_image(PAD, y_btn, image=img, anchor="w",
                                tags=("hist_sec", tag))
            canvas.create_text(PAD + 20, y_btn, text=bg_name, font=DF_ITEM,
                               fill="white", anchor="w", tags=("hist_sec", f"hl_{bg_name}"))

            def _sel(e, b=bg_name):
                selected_background.set(b)
                draw_history()

            for t in (tag, f"hl_{bg_name}"):
                canvas.tag_bind(t, "<Button-1>", _sel)
                canvas.tag_bind(t, "<Enter>", lambda e: canvas.config(cursor="hand2"))
                canvas.tag_bind(t, "<Leave>", lambda e: canvas.config(cursor=""))

    draw_history()
    update_desc()

    d_h  = int(UH * 0.20)
    op_y = Y_DESC + TH + 4
    op_h = d_h - TH - 8

    sec_title("Optional Additional Description", Y_DESC)

    extra_text = tk.Text(canvas, wrap="word", bg="#0d0a08", fg="white", font=DF_ITEM,
                         relief="flat", insertbackground="white",
                         highlightthickness=1, highlightbackground="white")
    canvas.create_window(PAD + 4, op_y + 4, window=extra_text,
                         anchor="nw", width=CW - 8, height=op_h - 8, tags="dlg")

    def open_custom_input():
        custom_win = tk.Toplevel(dialog)
        custom_win.title("Custom Character Description")
        center_window(custom_win, 500, 300)
        custom_win.resizable(False, False)
        custom_win.transient(dialog)
        custom_win.grab_set()
        custom_win.configure(bg="#282d39")

        ttk.Label(custom_win, text="Custom Description", style="Custom.TLabel", anchor="w").pack(fill="x", padx=20, pady=(16, 0))
        ttk.Separator(custom_win, orient="horizontal").pack(fill="x", padx=20, pady=(4, 8))

        text_box = tk.Text(
            custom_win, wrap="word", height=10,
            bg="#1e2230", fg="#fbf9f5",
            font=("Arial", 10), relief="flat",
            insertbackground="#fbf9f5"
        )
        text_box.pack(fill="both", expand=True, padx=20)

        foot = tk.Frame(custom_win, bg="#282d39")
        foot.pack(fill="x", padx=20, pady=10)

        def on_custom_confirm():
            custom_prompt = text_box.get("1.0", "end").strip()
            if not custom_prompt:
                messagebox.showerror("Empty Prompt", "Please provide a description before generating.")
                return
            create_image_openai(custom_prompt=custom_prompt, close_window=custom_win)

        ttk.Button(foot, text="Confirm", command=on_custom_confirm, style="Custom.TButton").pack(side="right")

    def create_image_openai(custom_prompt=None, close_window=None):
        api_key = get_api_key()
        if not api_key:
            messagebox.showerror("API Key Missing", "Please set your OpenAI API key first (click 'ASK DM ASSISTANT').")
            return

        base_dir   = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "game", "images", "characters")
        os.makedirs(output_dir, exist_ok=True)

        if custom_prompt:
            prompt = custom_prompt
        else:
            extra        = extra_text.get("1.0", "end").strip()
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
        center_window(loading, 320, 80)
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
                image_bytes  = base64.b64decode(image_base64)
                filename     = f"character_{int(time.time())}.png"
                file_path    = os.path.join(output_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                img = Image.open(file_path).convert("RGBA")
                img = img.resize((500, 500), Image.LANCZOS)
                img.save(file_path, "PNG")
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
            app.config_data.setdefault("Characters", []).append(name)
            app.selected_show[name] = tk.BooleanVar(value=True)
            regenerate_config(overwrite=True)
            app.refresh_ui()
            if close_window is not None:
                try:
                    close_window.destroy()
                except Exception:
                    pass
            dialog.destroy()
            messagebox.showinfo("Done", f"Character '{name}' created successfully.")

        threading.Thread(target=do_generate, daemon=True).start()

    create_b = tk.Button(canvas, image=create_btn_img, command=create_image_openai,
                         bd=0, relief="flat", bg="#1a1008", activebackground="#1a1008", cursor="hand2")
    custom_b = tk.Button(canvas, image=custom_btn_img, command=open_custom_input,
                         bd=0, relief="flat", bg="#1a1008", activebackground="#1a1008", cursor="hand2")

    canvas.create_window(W // 2 - 70, H - 15, window=create_b, anchor="s", tags="dlg")
    canvas.create_window(W // 2 + 70, H - 15, window=custom_b, anchor="s", tags="dlg")
