import socket
import threading
import json
import logging
import chess

from common.message import Message
from common.constants import (
    MSG_MOVE, MSG_CHAT, MSG_CREATE_GAME, MSG_JOIN_GAME, MSG_SPECTATE, MSG_LEAVE,
    MSG_UPDATE, MSG_GAME_STARTED, MSG_ERROR, MSG_GAME_OVER, MSG_GET_GAMES, MSG_LOBBY_UPDATE
)
from client.utils import update_game_state

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_state = chess.Board()
        self.username = ""
        self.gui = None
        self.client_id = None
        self.game_id = None
        self.role = None
        self.is_spectator = False
        self.opponent = None
        self.running = True

    def connect_to_server(self):
        """Connect to the server."""
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            logger.info("Connected to the server")
            # Set a default username if none is provided
            if not self.username:
                self.username = f"Guest_{self.client_id[:6]}" if self.client_id else "Guest"
            self.send_message("SET_USERNAME", {"username": self.username})
            self.receive_game_updates()
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            if self.gui:
                self.gui.show_error("Connection Failed", "Could not connect to the server.")

    def send_message(self, msg_type, data=None):
        """Send a message to the server."""
        if data is None:
            data = {}
        message = Message(msg_type, data)
        try:
            message_json = message.to_json()
            message_bytes = message_json.encode('utf-8')
            length_prefix = len(message_bytes).to_bytes(4, byteorder='big')
            self.client_socket.sendall(length_prefix + message_bytes)
            logger.debug(f"Sent message: {message_json}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.handle_connection_error()
            return False

    def send_move(self, move):
        """Send a move to the server (in UCI format)."""
        logger.info(f"Sending move to server: {move}")
        self.send_message(MSG_MOVE, {"move": move})

    def send_chat(self, message):
        """Send a chat message to the server."""
        logger.info(f"Sending chat message to server: '{message}', is_spectator: {self.is_spectator}")
        self.send_message(MSG_CHAT, {"message": message})

    def create_game(self):
        """Request to create a new game."""
        self.game_id = None
        self.send_message(MSG_CREATE_GAME, {})

    def join_game(self, game_id=None):
        """Request to join a game."""
        self.game_id = game_id if game_id else None
        self.send_message(MSG_JOIN_GAME, {"game_id": game_id} if game_id else {})

    def spectate_game(self, game_id):
        """Request to spectate a game."""
        self.game_id = game_id
        self.is_spectator = True  # Set spectator flag explicitly
        logger.info(f"Setting spectator mode for game {game_id}")
        self.send_message(MSG_SPECTATE, {"game_id": game_id})

    def leave_game(self):
        """Request to leave the current game."""
        self.send_message(MSG_LEAVE, {})
        self.game_id = None
        self.role = None
        self.is_spectator = False
        self.opponent = None

    def request_games(self):
        """Request the list of available games from the server."""
        self.send_message(MSG_GET_GAMES, {})

    def receive_game_updates(self):
        """Receive game updates from the server in a separate thread."""
        def listen_for_updates():
            while self.running:
                try:
                    # Read message length (4 bytes)
                    length_bytes = self.client_socket.recv(4)
                    if not length_bytes or len(length_bytes) != 4:
                        logger.info("Connection closed by server")
                        if self.gui:
                            self.gui.show_error("Connection Lost", "Disconnected from server.")
                        break
                    
                    # Get message length
                    message_length = int.from_bytes(length_bytes, byteorder='big')
                    
                    # Read the full message
                    data = b""
                    while len(data) < message_length:
                        chunk = self.client_socket.recv(min(4096, message_length - len(data)))
                        if not chunk:
                            logger.info("Connection closed while reading message")
                            break
                        data += chunk
                    
                    if not data:
                        continue
                        
                    # Decode and parse the message
                    message_json = data.decode('utf-8')
                    message = Message.from_json(message_json)
                    logger.debug(f"Received message: {message.msg_type}")
                    self.handle_server_message(message)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON format: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Connection error: {str(e)}")
                    if self.gui and "closed" in str(e).lower():
                        self.gui.show_error("Connection Error", "Disconnected from server.")
                    break
            self.running = False

        threading.Thread(target=listen_for_updates, daemon=True).start()

    def handle_server_message(self, message):
        """Handle messages received from the server."""
        msg_type = message.msg_type
        data = message.data

        # Always log the basic message details for debugging
        logger.debug(f"Received message type: {msg_type} with data: {data}")

        if msg_type == "WELCOME":
            self.client_id = data.get("client_id")
            logger.info(f"Received client ID: {self.client_id}")
            if self.username:
                self.send_message("SET_USERNAME", {"username": self.username})
        elif msg_type == "SET_USERNAME_ACK":
            logger.info(f"Username {self.username} set for client {self.client_id}")
        elif msg_type == MSG_UPDATE and self.gui:
            if "board_fen" not in data:
                logger.error(f"Missing board_fen in MSG_UPDATE: {data}")
                if self.gui:
                    self.gui.show_error("Server Error", f"Invalid game state received: {data}")
                return
            logger.info(f"Received game update: turn={data.get('turn')}, white_time={data.get('time_remaining', {}).get('white')}, black_time={data.get('time_remaining', {}).get('black')}")
            self.game_state = update_game_state(self.game_state, data["board_fen"])
            self.opponent = data.get('white_player' if self.role == 'black' else 'black_player', 'N/A')
            if self.gui:
                self.gui.update_from_server(data)
        elif msg_type == MSG_CHAT:
            # Enhanced chat message logging
            sender = data.get('sender', 'Unknown')
            message_text = data.get('message', '')
            logger.info(f"CHAT RECEIVED: From={sender}, Message='{message_text}'")
            print(f"CHAT RECEIVED: From={sender}, Message='{message_text}'")
            
            if self.gui:
                logger.debug(f"Displaying chat message in GUI from {sender}")
                try:
                    self.gui.display_chat_message(sender, message_text)
                    logger.info(f"Successfully displayed chat message in GUI")
                    print(f"Successfully displayed chat message in GUI")
                except Exception as e:
                    logger.error(f"Error displaying chat message in GUI: {e}", exc_info=True)
                    print(f"Error displaying chat message in GUI: {e}")
            else:
                logger.error("GUI not available to display chat message")
                print("GUI not available to display chat message")
        elif msg_type == MSG_ERROR:
            logger.error(f"Error from server: {data['message']}")
            if self.gui:
                self.gui.show_error("Game Error", data["message"])
        elif msg_type == MSG_GAME_STARTED:
            logger.info(f"Game started: {data}")
            if self.gui:
                self.gui.show_game()
                self.gui.update_from_server(data)
        elif msg_type == MSG_CREATE_GAME:
            self.game_id = data["game_id"]
            self.role = data["role"]
            logger.info(f"Created game: {self.game_id}, Role: {self.role}")
            if self.gui:
                self.gui.role = self.role
                self.gui.is_spectator = False
                self.gui.root.after(1, self.gui.show_game)
        elif msg_type == MSG_JOIN_GAME:
            self.game_id = data["game_id"]
            self.role = data["role"]
            logger.info(f"Joined game: {self.game_id}, Role: {self.role}")
            if self.gui:
                self.gui.role = self.role
                self.gui.is_spectator = False
                self.gui.root.after(1, self.gui.show_game)
        elif msg_type == MSG_SPECTATE:
            self.game_id = data["game_id"]
            self.is_spectator = True
            logger.info(f"Spectating game: {self.game_id}")
            if self.gui:
                self.gui.is_spectator = True
                self.gui.root.after(1, self.gui.show_game)
        elif msg_type == MSG_LOBBY_UPDATE and self.gui:
            logger.info(f"Received lobby update: {len(data.get('games', {}))} games available")
            self.gui.update_games_table(data["games"])
        elif msg_type == MSG_GAME_OVER:
            logger.info(f"Game over: {data['result']}")
            if self.gui:
                self.gui.show_game_over(data["result"])
        else:
            logger.warning(f"Unhandled message type: {msg_type}")

    def set_gui(self, gui):
        """Link GUI instance to the client."""
        self.gui = gui

    def set_username(self, username):
        """Set the client's username."""
        self.username = username
        if self.client_id:
            self.send_message("SET_USERNAME", {"username": username})

    def close_connection(self):
        """Close the client connection."""
        self.running = False
        self.client_socket.close()
        logger.info("Client connection closed")

    def handle_connection_error(self):
        """Handle connection errors."""
        if self.gui:
            self.gui.show_error("Connection Error", "Lost connection to the server.")
        self.close_connection()