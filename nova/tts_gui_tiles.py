#===============================================================================
# NOVA GUI Tiles for Pocket TTS Quick Access
#===============================================================================

"""
Desktop tiles / menu items for rapid TTS interaction.
"""

import json, pathlib
from datetime import datetime


def create_tile_files():
    """Create desktop shortcut and config files."""
    
    tile_dir = pathlib.Path.home() / "Desktop"
    tile_dir.mkdir(exist_ok=True)
    
    # 1. Quick Access Batch File
    batch_path = tile_dir / "NOVA_TTS_QuickAccess.bat"
    with open(batch_path, 'w') as f:
        f.write('''@echo off
title NOVA Pocket TTS Quick Access
cd C:\\Users\\wuchy\\Documents\\NOVA\\NOVA_fieldkit_v1_4
python.exe -c "from nova.tts_tool import speak; speak('Hello, I am Nova. How may I assist you today?', seat='brief')"
pause
''')
    
    # 2. Voice Selection Tool
    voice_path = tile_dir / "NOVA_TTS_VoiceSelect.bat"
    with open(voice_path, 'w') as f:
        f.write('''@echo off
title NOVA TTS Voice Select
set /p text="Enter text to speak:"
python -c "from nova.tts_tool import speak; seat=%1; speak('" + "%text%" + "', seat='" + "%seat%")" % brief,hearth,tutor,deleo,sentinel,chronicler,reviewer
pause
''')
    
    print(f"GUI Tiles created in: {tile_dir}")
    print(f"  - NOVA_TTS_QuickAccess.bat")
    print(f"  - NOVA_TTS_VoiceSelect.bat")


def create_menu_items():
    """Create Windows Start Menu items (in user's app data)."""
    
    menu_dir = pathlib.Path.home() / "AppData" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "NOVA_TTS"
    menu_dir.mkdir(parents=True, exist_ok=True)
    
    # Main launcher
    main_path = menu_dir / "Pocket TTS Launcher.lnk"
    with open(main_path.parent / "Pocket TTS Launcher.lnk", 'w') as f:
        f.write(f'@echo off\ncd {"C:\\Users\\wuchy\\Documents\\NOVA\\NOVA_fieldkit_v1_4"}\npython.exe -m nova.tts_tool\npause\n')
    
    print(f"Menu items created in: {menu_dir}")


def create_config():
    """Create TTS configuration file for future use."""
    
    config = {
        "name": "NOVA Pocket TTS Tiles",
        "version": "1.0",
        "tiles": {
            "quick_access": {
                "label": "NOVA TTS Quick Access",
                "command": "C:\\Users\\wuchy\\Desktop\\NOVA_TTS_QuickAccess.bat"
            },
            "voice_select": {
                "label": "Select Voice & Speak",
                "command": "C:\\Users\\wuchy\\Desktop\\NOVA_TTS_VoiceSelect.bat"
            }
        },
        "seats_available": list(__import__('nova.pocket').pocket.SEATS.keys())
    }
    
    config_path = pathlib.Path.home() / ".openclaw" / "config" / "nova-tts-tiles.json"
    pathlib.Path(config_path.parent).mkdir(exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Config created: {config_path}")


if __name__ == "__main__":
    create_tile_files()
    # create_menu_items()  # Optional Windows menu integration
    create_config()
    print("\nGUI Tiles integration complete!")
