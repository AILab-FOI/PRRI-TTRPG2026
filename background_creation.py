import tkinter as tk
from tkinter import ttk, messagebox
import os
import base64
import time
import threading
from PIL import Image, ImageTk
from openai import OpenAI
from character_creation import center_window


def open_create_background(app, get_api_key, regenerate_config):
    stub = tk.Toplevel(app)
    stub.title("Create Background")
    center_window(stub, 500, 320)
    stub.resizable(False, False)
    stub.transient(app)
    stub.grab_set()
    stub.configure(bg="#282d39")

    ttk.Label(stub, text="Create Background", style="Custom.TLabel", anchor="w").pack(fill="x", padx=20, pady=(16, 0))
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
        user_prompt = text_box.get("1.0", "end").strip()
        if not user_prompt:
            messagebox.showerror("Empty Prompt", "Please provide a description before generating.")
            return
        _generate_background_image(app, user_prompt, stub, get_api_key, regenerate_config)

    ttk.Button(foot, text="Create", command=on_create, style="Custom.TButton").pack(side="right")


def _generate_background_image(app, user_prompt, close_window, get_api_key, regenerate_config):
    api_key = get_api_key()
    if not api_key:
        messagebox.showerror("API Key Missing", "Please set your OpenAI API key first (click 'ASK DM ASSISTANT').")
        return

    base_dir  = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "game", "images", "locations")
    os.makedirs(output_dir, exist_ok=True)

    prompt = (
        f"A fantasy background scenery, no characters, wide cinematic landscape, "
        f"highly detailed environment art. {user_prompt}"
    )

    loading = tk.Toplevel(close_window)
    loading.title("Generating...")
    center_window(loading, 320, 80)
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
            image_bytes  = base64.b64decode(image_base64)
            filename     = f"background_{int(time.time())}.png"
            file_path    = os.path.join(output_dir, filename)
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
