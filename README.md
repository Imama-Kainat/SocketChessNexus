# Multiplayer Chess Game

A multiplayer chess game built with Python, using Pygame for the GUI and socket programming for networking.

## Project Structure
- `server/`: Server-side code to manage game sessions and communication.
- `client/`: Client-side code with a GUI for playing the game.
- `common/`: Shared logic for chess rules, messaging, and constants.

## Folder Structure
📁 client
    ├── images/               # GUI assets like pieces
    ├── client.py             # Main client logic
    ├── gui.py                # UI logic (likely using Tkinter or PyGame)
    ├── utils.py              # Helper methods
📁 common
    ├── chess_logic.py        # Core chess rules
    ├── constants.py          # Configurable constants
    ├── message.py            # Common message formats or parsing
📁 server
    ├── server.py             # Socket server
    ├── game_session.py       # Individual game logic per pair
    ├── lobby.py              # Lobby management and matchmaking
    ├── utils.py              # Server-side helpers


## Requirements
- Python 3.8+
- pygame
- python-chess


# Documentation Link
https://docs.google.com/document/d/1lUAXp2R_7SiedBwF9k8MTPPfWv9EDPAtt2fK_3woCqc/edit?usp=sharing


## How to run
python -m server.server
python -m client.gui

Install dependencies:
```bash
pip install -r requirements.txt