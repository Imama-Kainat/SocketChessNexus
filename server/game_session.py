import logging
import time
import threading
from typing import Dict, Set, Optional, List, Tuple
import socket
import chess
from common.message import Message
from common.constants import (
    WHITE, BLACK, SPECTATOR, MSG_MOVE, MSG_CHAT, MSG_GAME_OVER,
    MSG_UPDATE, MSG_ERROR, DEFAULT_TIME_CONTROL, TIME_INCREMENT
)
from server.utils import send_data

logger = logging.getLogger('game_session')

class GameSession:
    def __init__(self, game_id: str, player1_id: str = None, player2_id: str = None):
        self.game_id = game_id
        self.chess_game = chess.Board()
        self.player_roles: Dict[str, str] = {}
        if player1_id:
            self.player_roles[player1_id] = WHITE
        if player2_id:
            self.player_roles[player2_id] = BLACK
        self.spectators: Set[str] = set()
        self.client_sockets: Dict[str, socket.socket] = {}
        self.time_remaining: Dict[str, float] = {
            WHITE: DEFAULT_TIME_CONTROL,
            BLACK: DEFAULT_TIME_CONTROL
        }
        self.last_move_time: Optional[float] = None
        self.chat_history: List[Tuple[str, str]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.running = True

    def start_game(self):
        self.start_time = time.time()
        self.last_move_time = self.start_time
        logger.info(f"Game {self.game_id} started")
        self.broadcast_state()
        threading.Thread(target=self.time_control_loop, daemon=True).start()

    def time_control_loop(self):
        """Update the game time every 100ms for smooth timer updates."""
        try:
            update_interval = 0.1  # Update 10 times per second for smoother timer display
            last_broadcast_time = time.time()
            broadcast_interval = 1.0  # Broadcast state every 1 second to avoid too much network traffic
            
            while self.running and not self.end_time:
                try:
                    current_time = time.time()
                    
                    # Only continue if the game has started
                    if not self.start_time:
                        time.sleep(update_interval)
                        continue
                        
                    # Update the time for the current player
                    current_turn = "white" if self.chess_game.turn == chess.WHITE else "black"
                    color = WHITE if current_turn == "white" else BLACK
                    
                    time_since_last_update = current_time - self.last_move_time
                    self.time_remaining[color] = max(0, self.time_remaining[color] - time_since_last_update)
                    self.last_move_time = current_time
                    
                    # Check for timeout
                    if self.time_remaining[color] <= 0:
                        self.time_remaining[color] = 0
                        self.end_time = current_time
                        logger.info(f"Game {self.game_id} over: {color} timeout")
                        self.broadcast_game_over()
                        break
                    
                    # Broadcast the state periodically to update timers
                    time_since_last_broadcast = current_time - last_broadcast_time
                    if time_since_last_broadcast >= broadcast_interval:
                        self.broadcast_state()
                        last_broadcast_time = current_time
                        
                    time.sleep(update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in time control loop: {e}")
                    time.sleep(update_interval)
        except Exception as e:
            logger.error(f"Fatal error in time control loop: {e}")

    def add_player(self, player_id: str, client_socket: socket.socket) -> str:
        if player_id not in self.player_roles:
            if WHITE not in self.player_roles.values():
                self.player_roles[player_id] = WHITE
            elif BLACK not in self.player_roles.values():
                self.player_roles[player_id] = BLACK
            else:
                logger.warning(f"Cannot add player {player_id} to game {self.game_id}: Both roles assigned")
                return ""
        self.client_sockets[player_id] = client_socket
        logger.info(f"Player {player_id} added to game {self.game_id} as {self.player_roles[player_id]}")
        return self.player_roles[player_id]

    def add_spectator(self, spectator_id: str, client_socket: socket.socket):
        """
        Add a spectator to the game session.
        
        Args:
            spectator_id: The ID of the spectator
            client_socket: The socket connection to the spectator
        """
        # Add to spectators set
        self.spectators.add(spectator_id)
        
        # Store the socket connection
        self.client_sockets[spectator_id] = client_socket
        
        # Log the action with detailed information
        logger.info(f"Spectator {spectator_id} added to game {self.game_id}")
        print(f"GAME SESSION: Added spectator {spectator_id} to game {self.game_id}")
        print(f"Current spectators: {self.spectators}")
        print(f"Current client sockets: {list(self.client_sockets.keys())}")
        
        # Broadcast a welcome message to all clients
        welcome_msg = f"{spectator_id} joined as a spectator"
        self.broadcast_chat("System", welcome_msg)

    def remove_client(self, client_id: str):
        if client_id in self.player_roles:
            del self.player_roles[client_id]
        if client_id in self.spectators:
            self.spectators.remove(client_id)
        if client_id in self.client_sockets:
            del self.client_sockets[client_id]
        logger.info(f"Client {client_id} removed from game {self.game_id}")
        if len(self.player_roles) == 0:
            self.running = False
            logger.info(f"Game {self.game_id} ended due to no remaining players")

    def process_move(self, player_id: str, move_uci: str) -> bool:
        """Process a move from a player."""
        try:
            if player_id not in self.player_roles:
                logger.warning(f"Player {player_id} not in game {self.game_id}")
                self.send_error(player_id, "You are not a player in this game")
                return False
        
            current_turn = "white" if self.chess_game.turn == chess.WHITE else "black"
            player_role = self.player_roles[player_id]
                
            if (current_turn == "white" and player_role != WHITE) or \
               (current_turn == "black" and player_role != BLACK):
                logger.warning(f"Not {player_id}'s turn in game {self.game_id}")
                self.send_error(player_id, "It's not your turn")
                return False
                
            # Handle promotion moves
            if len(move_uci) == 5:  # e.g. e7e8q for promotion
                from_square = chess.parse_square(move_uci[0:2])
                to_square = chess.parse_square(move_uci[2:4])
                promotion_piece = move_uci[4]
                
                # Map promotion character to chess piece type
                promotion_map = {
                    'q': chess.QUEEN,
                    'r': chess.ROOK,
                    'b': chess.BISHOP,
                    'n': chess.KNIGHT
                }
                
                if promotion_piece not in promotion_map:
                    logger.warning(f"Invalid promotion piece {promotion_piece} in move {move_uci}")
                    self.send_error(player_id, f"Invalid promotion piece: {promotion_piece}")
                    return False
                    
                move = chess.Move(from_square, to_square, promotion=promotion_map[promotion_piece])
            else:
                try:
                    # Regular move
                    move = chess.Move.from_uci(move_uci)
                except ValueError:
                    logger.warning(f"Invalid move format: {move_uci}")
                    self.send_error(player_id, "Invalid move format")
                    return False
                
            # Check if the move is legal
            if move not in self.chess_game.legal_moves:
                logger.warning(f"Illegal move {move_uci} by {player_id} in game {self.game_id}")
                legal_moves = [m.uci() for m in self.chess_game.legal_moves]
                logger.debug(f"Legal moves: {legal_moves}")
                self.send_error(player_id, "That move is not legal")
                return False
            
            # Record current time before making the move
            current_time = time.time()
            time_spent = current_time - self.last_move_time if self.last_move_time else 0
                
            # Update the timer for the player who made the move (before changing turns)
            self.time_remaining[player_role] = max(0, self.time_remaining[player_role] - time_spent)
                
            # Add time increment for making a move
            self.time_remaining[player_role] += TIME_INCREMENT
                
            # Update the last move time
            self.last_move_time = current_time
                
            # Make the move
            self.chess_game.push(move)
                
            logger.info(f"Move {move_uci} by {player_id} in game {self.game_id}")
                
            # Check if the game is over
            if self.chess_game.is_game_over():
                self.end_time = current_time
                logger.info(f"Game {self.game_id} over: {self.get_result()}")
                self.broadcast_game_over()
            
            # Broadcast the new state to all clients
            self.broadcast_state()
            return True
            
        except Exception as e:
            logger.error(f"Error processing move {move_uci}: {e}")
            self.send_error(player_id, f"Server error processing move: {str(e)}")
            return False

    def add_chat_message(self, sender_id: str, message: str):
        self.chat_history.append((sender_id, message))

    def broadcast_state(self):
        try:
            fen = self.chess_game.fen()
            logger.debug(f"Broadcasting state for game {self.game_id} with board_fen: {fen}")
                
            # Get the player IDs or "Unknown" if not available
            white_player_id = next((pid for pid, role in self.player_roles.items() if role == WHITE), None)
            black_player_id = next((pid for pid, role in self.player_roles.items() if role == BLACK), None)
                
            game_state = {
                'board_fen': fen,
                'turn': "white" if self.chess_game.turn == chess.WHITE else "black",
                'is_check': self.chess_game.is_check(),
                'is_checkmate': self.chess_game.is_checkmate(),
                'is_stalemate': self.chess_game.is_stalemate(),
                'is_game_over': self.chess_game.is_game_over(),
                'result': self.get_result(),
                'time_remaining': self.time_remaining,
                'move_history': [move.uci() for move in self.chess_game.move_stack],
                'white_player': white_player_id,
                'black_player': black_player_id
            }
                
            update_msg = Message(MSG_UPDATE, game_state).to_json()
            success_count = 0
                
            # Create a copy of client_sockets to avoid modification during iteration
            clients_to_update = dict(self.client_sockets)
                
            for client_id, client_socket in clients_to_update.items():
                try:
                    if send_data(client_socket, update_msg):
                        success_count += 1
                    else:
                        logger.error(f"Failed to broadcast state to {client_id}")
                except Exception as e:
                    logger.error(f"Error broadcasting state to {client_id}: {e}")
                    
            if success_count > 0:
                logger.info(f"Broadcasted state to {success_count} clients")
            else:
                logger.warning(f"Failed to broadcast state to any clients")
        except Exception as e:
            logger.error(f"Error preparing game state broadcast: {e}")

    def broadcast_chat(self, sender_id: str, message: str, player_role: str = None):
        """
        Broadcast a chat message to all clients in the game session.
        
        Args:
            sender_id: The username of the sender
            message: The message content
            player_role: Optional role of the player (WHITE, BLACK, or None for spectator)
        """
        # Emergency debug message
        print(f"!!! CHAT MESSAGE !!! - From: {sender_id}, Content: {message}, Role: {player_role}")
        
        # Log the raw incoming message details
        logger.info(f"CHAT PROCESSING - sender: {sender_id}, message: {message}, role: {player_role}")
        
        # Determine display name based on role
        if player_role == WHITE:
            display_name = f"{sender_id} [White]"
        elif player_role == BLACK:
            display_name = f"{sender_id} [Black]"
        else:
            # This is a spectator message
            display_name = f"{sender_id} [Spectator]"
            logger.info(f"SPECTATOR CHAT - processing message from: {sender_id}")
            print(f"!!! SPECTATOR CHAT !!! - From: {sender_id}")
            
            # Check if sender is actually in spectators list (by username lookup)
            found = False
            for spec_id in self.spectators:
                # This is just a debug check
                logger.info(f"Checking spectator ID: {spec_id}")
                print(f"Checking spectator ID: {spec_id}")
            
            logger.info(f"Total spectators: {len(self.spectators)}, Total clients: {len(self.client_sockets)}")
        
        # Creating message data to broadcast
        self.add_chat_message(display_name, message)
        chat_data = {'sender': display_name, 'message': message, 'timestamp': time.time()}
        chat_msg = Message(MSG_CHAT, chat_data).to_json()
        logger.info(f"Broadcasting chat to {len(self.client_sockets)} clients from {display_name}: {message}")
        
        # Debug: print all client IDs we're broadcasting to
        print(f"Client sockets to broadcast to: {list(self.client_sockets.keys())}")
        
        # Send to all clients
        success_count = 0
        failed_count = 0
        for client_id, client_socket in list(self.client_sockets.items()):
            try:
                print(f"Sending chat to client: {client_id}")
                if send_data(client_socket, chat_msg):
                    success_count += 1
                    logger.debug(f"Successfully sent chat to {client_id}")
                    print(f"Successfully sent chat to {client_id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send chat message to {client_id}")
                    print(f"Failed to send chat message to {client_id}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending chat message to {client_id}: {e}")
                print(f"Error sending chat message to {client_id}: {e}")
        
        print(f"Chat broadcast results: Success: {success_count}, Failed: {failed_count}")
        logger.info(f"Chat broadcast results: Success: {success_count}, Failed: {failed_count}")
        return success_count > 0

    def broadcast_game_over(self):
        try:
            result = self.get_result()
            game_over_msg = Message(
                MSG_GAME_OVER, {
                    'result': result,
                    'white_player': next((pid for pid, role in self.player_roles.items() if role == WHITE), None),
                    'black_player': next((pid for pid, role in self.player_roles.items() if role == BLACK), None),
                    'end_time': self.end_time
                }
            ).to_json()
                
            # Create a copy of client_sockets to avoid modification during iteration
            clients_to_update = dict(self.client_sockets)
                
            for client_id, client_socket in clients_to_update.items():
                try:
                    if send_data(client_socket, game_over_msg):
                        logger.info(f"Sent game over message to {client_id}")
                    else:
                        logger.error(f"Failed to send game over message to {client_id}")
                except Exception as e:
                    logger.error(f"Error sending game over message to {client_id}: {e}")
        except Exception as e:
            logger.error(f"Error preparing game over broadcast: {e}")

    def send_error(self, client_id: str, error_message: str):
        if client_id not in self.client_sockets:
            logger.warning(f"Cannot send error to unknown client {client_id}")
            return
        error_msg = Message(MSG_ERROR, {'message': error_message}).to_json()
        send_data(self.client_sockets[client_id], error_msg)

    def check_time_control(self):
        """No longer needed as time_control_loop handles everything."""
        pass  # This method is deprecated - time_control_loop does all the work now

    def get_result(self):
        if self.chess_game.is_checkmate():
            return "1-0" if self.chess_game.turn == chess.BLACK else "0-1"
        if self.chess_game.is_stalemate() or self.chess_game.is_insufficient_material():
            return "1/2-1/2"
        if self.time_remaining[WHITE] <= 0:
            return "0-1"
        if self.time_remaining[BLACK] <= 0:
            return "1-0"
        return "1/2-1/2"