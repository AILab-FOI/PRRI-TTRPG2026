# Cover image

image cover = "images/cover.png"

# Characters
define t = Character( "Test_Character" )
image test_character = "images/characters/test_character.png"

# NPCs
image _empty = "images/npcs/_empty.png"
image _empty2 = "images/npcs/_empty2.png"
image test_npc = "images/npcs/test_npc.png"

# Backgrounds
image test_location = "images/locations/test_location.png"

# Style: {style} — {flavour}

Sound effects
define snd = ""

init python:
    def play_sound_effect():
        renpy.sound.play( snd )

screen custom_listener():
    key "K_z" action [ Function( play_sound_effect ) ]

label start:
    show screen custom_listener
    python:
        import json
        cscn = " "
        cshw = [ "", "", "" ]
        pos = 0
    jump next

label next:
    python:
        import json

        with renpy.open_file( 'next.json' ) as file:
            data = json.load( file )

        # Set the variables based on the JSON data
        scn = data[ "scene" ]
        shw = data[ "show" ]
        bgm = "audio/bcgsound/" + data[ "bgm" ] + ".mp3"
        snd = "audio/soundeffects/" + data[ "sound" ] + ".mp3"

    # SOUND
    play music bgm if_changed
    # SCENES

    if scn == "test_location" and cscn != "test_location":
        jump test_location

    if "test_character" in shw and "test_character" not in cshw:
        jump test_character
    if "_empty" in shw and "_empty" not in cshw:
        jump _empty
    if "_empty2" in shw and "_empty2" not in cshw:
        jump _empty2
    if "test_npc" in shw and "test_npc" not in cshw:
        jump test_npc

    $ renpy.pause ()


# SCENE LABELS

label test_location:
    $ cscn = "test_location"
    $ pos = 0
    $ cshw = [ "", "", "" ]
    scene test_location
    jump next


# CHARACTER AND NPC LABELS

label test_character:
    $ cshw[ pos ] = "test_character"
    if pos == 0:
        show test_character with dissolve 
    elif pos == 2:
        show test_character at left with moveinleft
    elif pos == 1:
        show test_character at right with moveinright
    
    $ pos += 1
    jump next

label _empty:
    $ cshw[ pos ] = "_empty"
    if pos == 0:
        show _empty with dissolve 
    elif pos == 2:
        show _empty at left with moveinleft
    elif pos == 1:
        show _empty at right with moveinright
    
    $ pos += 1
    jump next

label _empty2:
    $ cshw[ pos ] = "_empty2"
    if pos == 0:
        show _empty2 with dissolve 
    elif pos == 2:
        show _empty2 at left with moveinleft
    elif pos == 1:
        show _empty2 at right with moveinright
    
    $ pos += 1
    jump next

label test_npc:
    $ cshw[ pos ] = "test_npc"
    if pos == 0:
        show test_npc with dissolve 
    elif pos == 2:
        show test_npc at left with moveinleft
    elif pos == 1:
        show test_npc at right with moveinright
    
    $ pos += 1
    jump next


# END LABEL

label end:
    return