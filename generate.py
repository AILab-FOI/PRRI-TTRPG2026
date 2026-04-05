import os
import argparse
import re
from app import parse_config

STYLE_FLAVOUR = {
    "High Fantasy":  "A world of ancient magic, noble heroes, and epic quests.",
    "Dark Fantasy":  "A grim world where hope is scarce and shadows run deep.",
    "Magitech":      "A realm where arcane magic and clockwork technology intertwine.",
    "Sword & Sorcery": "A brutal world of wandering warriors and dangerous sorcery.",
}

def generate_script(characters, npcs, backgrounds, output_dir, overwrite=False, style="High Fantasy"):
    """ Generate the complete script.rpy file with all required sections. """
    output_file_path = os.path.join(output_dir, 'game', 'script.rpy')

    # Check if the file exists and handle the overwrite scenario
    if os.path.exists(output_file_path) and not overwrite:
        if input(f"The file {output_file_path} already exists. Overwrite? (y/n): ").lower() != 'y':
            print("Operation cancelled.")
            return

    flavour = STYLE_FLAVOUR.get(style, "")
    # Creating content for the script.rpy file
    cover_image = 'image cover = "images/cover.png"'
    character_definitions = '\n'.join([f'define {c[0]} = Character( "{c.title()}" )' for c in characters])
    character_images = '\n'.join([f'image {c} = "images/characters/{c}.png"' for c in characters])
    npc_images = '\n'.join([f'image {n} = "images/npcs/{n}.png"' for n in npcs])
    background_definitions = '\n'.join([f'image {b} = "images/locations/{b}.png"' for b in backgrounds])

    # Additional sections for labels and logic
    start_label = f"# Style: {style} — {flavour}\n\n# Sound effects\ndefine snd = \"\"\n\ninit python:\n    def play_sound_effect():\n        renpy.sound.play( snd )\n\nscreen custom_listener():\n    key \"K_z\" action [ Function( play_sound_effect ) ]\n\nlabel start:\n    show screen custom_listener\n    python:\n        import json\n        cscn = \" \"\n        cshw = [ \"\", \"\", \"\" ]\n        pos = 0\n    jump next\n"
    next_label = (
        "label next:\n    python:\n        import json\n\n        with renpy.open_file( 'next.json' ) as file:\n"
        "            data = json.load( file )\n\n        # Set the variables based on the JSON data\n"
        "        scn = data[ \"scene\" ]\n        shw = data[ \"show\" ]\n        bgm = \"audio/bcgsound/\" + data[ \"bgm\" ] + \".mp3\"\n        snd = \"audio/soundeffects/\" + data[ \"sound\" ] + \".mp3\"\n\n"
        "    # SOUND\n    play music bgm if_changed\n"
        "    # SCENES\n"
    )

    # Generating scene and character labels
    scene_labels = "\n".join([f"    if scn == \"{bg}\" and cscn != \"{bg}\":\n        jump {bg}" for bg in backgrounds]) + "\n\n"
    character_labels = "\n".join([f"    if \"{char}\" in shw and \"{char}\" not in cshw:\n        jump {char}" for char in characters + npcs]) + "\n\n"
    character_labels += "    $ renpy.pause ()\n\n"
    
    # Generating individual scene and character label sections
    scene_label_sections = "\n# SCENE LABELS\n\n" + "\n\n".join([f"label {bg}:\n    $ cscn = \"{bg}\"\n    $ pos = 0\n    $ cshw = [ \"\", \"\", \"\" ]\n    scene {bg}\n    jump next" for bg in backgrounds]) + "\n\n"
    character_label_sections = "\n# CHARACTER AND NPC LABELS\n\n" + "\n\n".join([f"label {char}:\n    $ cshw[ pos ] = \"{char}\"\n    if pos == 0:\n        show {char} with dissolve \n    elif pos == 2:\n        show {char} at left with moveinleft\n    elif pos == 1:\n        show {char} at right with moveinright\n    \n    $ pos += 1\n    jump next" for char in characters + npcs]) + "\n\n"

    end_label = "\n# END LABEL\n\nlabel end:\n    return"

    # Concatenating all parts to form the final content
    final_content = (
        f'# Cover image\n\n{cover_image}\n\n# Characters\n{character_definitions}\n{character_images}\n\n# NPCs\n{npc_images}\n\n'
        f'# Backgrounds\n{background_definitions}\n\n{start_label}\n{next_label}\n{scene_labels}{character_labels}{scene_label_sections}{character_label_sections}{end_label}'
    )

    # Write the final content to the file
    with open(output_file_path, 'w',encoding='utf-8-sig') as file:
        file.write(final_content)

    print(f"Script file generated at {output_file_path}")


# Updating the main function to include the new generation function
def main():
    parser = argparse.ArgumentParser(description='Generate a RenPy script.rpy file based on a configuration file.')
    parser.add_argument('config_file', nargs='?', default='interface.conf', type=str, help='Path to the configuration file.')
    parser.add_argument('-O', '--overwrite', action='store_true', help='Overwrite existing script.rpy file without asking.')
    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(current_dir, args.config_file)

    # Parse the config file
    data = parse_config( config_file_path )
    characters, npcs, sound_effects, backgrounds = data[ "Characters" ], data[ "NPCs" ], data[ "Sound effects" ], data[ "Backgrounds" ]

    # Generate the complete script.rpy file
    generate_script(characters, npcs, backgrounds, current_dir, args.overwrite)

if __name__ == "__main__":
    main()

