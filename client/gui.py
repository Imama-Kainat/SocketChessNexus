from client import ChessClient
import tkinter as tk
from tkinter import messagebox, ttk
import chess
import os
import logging
from client.utils import is_valid_move, update_game_state, format_time
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessGUI:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.board = chess.Board()
        self.buttons = {}
        self.from_square = None
        self.images = {}
        self.is_spectator = False
        self.role = None
        self.move_history = []
        self.game_active = False
        
        # Initialize error tracking
        self._error_count = 0

        # Create a single empty image to use for empty squares
        self.empty_image = tk.PhotoImage(width=64, height=64)
        
        self.root.title("Chess Nexus")
        # Set larger window size to ensure all elements are visible
        self.root.geometry("1024x700")
        self.root.configure(bg="#2c3e50")
        
        # Center the window on screen
        self.center_window()

        # Load chess piece images - must be done before creating the board
        self.load_images()

        self.main_frame = tk.Frame(self.root, bg="#2c3e50")
        self.main_frame.pack(fill="both", expand=True)

        # Create all frames upfront
        self.create_login_frame()
        self.create_lobby_frame()
        self.create_game_frame()

        # Show login frame first
        self.show_login()

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def load_images(self):
        """Load chess piece images into memory."""
        # The pieces we need to load
        pieces = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king']
        colors = ['white', 'black']
        
        logger.info("Loading chess piece images...")
        
        # Get absolute path to the images directory
        images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "images"))
        logger.info(f"Images directory: {images_dir}")
        
        # Check if the directory exists
        if not os.path.exists(images_dir):
            logger.error(f"Images directory not found: {images_dir}")
            return
        
        # Load each image
        loaded_count = 0
        for color in colors:
            for piece in pieces:
                filename = f"{color}_{piece}.png"
                image_path = os.path.join(images_dir, filename)
                
                try:
                    if os.path.exists(image_path):
                        self.images[f"{color}_{piece}"] = tk.PhotoImage(file=image_path)
                        loaded_count += 1
                        logger.debug(f"Loaded image: {filename}")
                    else:
                        logger.error(f"Image file not found: {image_path}")
                except Exception as e:
                    logger.error(f"Error loading image {filename}: {e}")
        
        logger.info(f"Successfully loaded {loaded_count} out of 12 chess piece images")

    def get_image(self, piece):
        """Return the correct image for a piece or a blank image."""
        if not piece:
            return self.empty_image
            
        color = 'white' if piece.color == chess.WHITE else 'black'
        piece_type_map = {
            'p': 'pawn', 'r': 'rook', 'n': 'knight',
            'b': 'bishop', 'q': 'queen', 'k': 'king'
        }
        piece_type = piece_type_map.get(piece.symbol().lower())
        
        if not piece_type:
            logger.warning(f"Unknown piece symbol: {piece.symbol()}")
            return self.empty_image
            
        image_key = f"{color}_{piece_type}"
        
        # Return the image if we have it, otherwise return empty image
        return self.images.get(image_key, self.empty_image)

    def create_login_frame(self):
        """Create the login UI (first screen)."""
        self.login_frame = tk.Frame(self.main_frame, bg="#34495e", padx=20, pady=20)
        tk.Label(self.login_frame, text="Socket Chess Nexus", font=("Arial", 24, "bold"), fg="white", bg="#34495e").pack(pady=20)
        
        tk.Label(self.login_frame, text="Username", font=("Arial", 14), fg="white", bg="#34495e").pack()
        self.username_entry = tk.Entry(self.login_frame, font=("Arial", 14), width=20, bg="#4a6279", fg="white", insertbackground="white")
        self.username_entry.insert(0, "Enter your username")
        self.username_entry.pack(pady=10)
        
        tk.Button(self.login_frame, text="Enter Chess Lobby", font=("Arial", 14), bg="#3498db", fg="white",
                  command=self.enter_lobby).pack(pady=20)

    def create_lobby_frame(self):
        """Create the lobby UI (second screen)."""
        self.lobby_frame = tk.Frame(self.main_frame, bg="white")
        
        tk.Label(self.lobby_frame, text="Chess Nexus Lobby", font=("Arial", 18, "bold"), bg="white").pack(pady=5)
        
        tk.Button(self.lobby_frame, text="Create Game", font=("Arial", 12), bg="#3498db", fg="white",
                  command=self.create_game).pack(pady=5, anchor="ne", padx=10)
        
        tk.Label(self.lobby_frame, text="Available Games", font=("Arial", 14, "bold"), bg="white").pack(pady=5)
        self.games_frame = tk.Frame(self.lobby_frame, bg="white")
        self.games_frame.pack(fill="both", expand=True, padx=10)
        
        headers = ["Host", "Status", "Actions"]
        for i, header in enumerate(headers):
            tk.Label(self.games_frame, text=header, font=("Arial", 12, "bold"), bg="white").grid(row=0, column=i, padx=10, pady=5)
        
        # Add back the how to play section
        how_to_play = tk.Frame(self.lobby_frame, bg="white")
        how_to_play.pack(fill="x", pady=20, padx=10)
        tk.Label(how_to_play, text="How to Play", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")
        rules = [
            "Create a new game or join an existing one from the lobby.",
            "White always moves first, followed by Black.",
            "Each player has 5 minutes for all their moves.",
            "Click on a piece to select it, then click on a valid square to move.",
            "Capture opponent pieces by moving onto their square.",
            "The goal is to checkmate your opponent's king.",
            "You can spectate ongoing games without participating."
        ]
        for rule in rules:
            tk.Label(how_to_play, text=f"• {rule}", font=("Arial", 12), bg="white", wraplength=600, justify="left").pack(anchor="w")

    def update_games_table(self, games_data):
        """Update the available games table in the lobby."""
        for widget in self.games_frame.winfo_children()[3:]:
            widget.destroy()

        for row, (game_id, game_info) in enumerate(games_data.items(), start=1):
            host = game_info["players"][0] if game_info["players"] else "Unknown"
            status = game_info["status"]
            
            tk.Label(self.games_frame, text=host, font=("Arial", 12), bg="white").grid(row=row, column=0, padx=10, pady=2)
            tk.Label(self.games_frame, text=status.capitalize(), font=("Arial", 12), bg="white").grid(row=row, column=1, padx=10, pady=2)
            
            actions_frame = tk.Frame(self.games_frame, bg="white")
            actions_frame.grid(row=row, column=2, padx=10, pady=2)
            
            if status == "waiting":
                tk.Button(actions_frame, text="Join", font=("Arial", 10), bg="#3498db", fg="white",
                          command=lambda gid=game_id: self.join_game(gid)).pack(side="left", padx=5)
            tk.Button(actions_frame, text="Watch", font=("Arial", 10), bg="#95a5a6", fg="white",
                      command=lambda gid=game_id: self.spectate_game(gid)).pack(side="left", padx=5)

    def create_game_frame(self):
        """Create the game UI (third screen)."""
        self.game_frame = tk.Frame(self.main_frame, bg="white")
        
        # Create title with colored border
        title_frame = tk.Frame(self.game_frame, bg="#3498db")
        title_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            title_frame, 
            text="Chess Nexus", 
            font=("Arial", 20, "bold"), 
            bg="#3498db", 
            fg="white", 
            padx=10, 
            pady=5
        ).pack()
        
        # Create main content area with board and controls
        content_frame = tk.Frame(self.game_frame, bg="white")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        left_frame = tk.Frame(content_frame, bg="white")
        left_frame.pack(side="left", padx=10, pady=10)
        
        right_frame = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Create board frame with slight border
        board_container = tk.Frame(left_frame, bg="#2c3e50", bd=2, relief="solid")
        board_container.pack(padx=10, pady=10)
        
        self.board_frame = tk.Frame(board_container, bg="white")
        self.board_frame.pack(padx=2, pady=2)
        
        # Create the initial chessboard
        self.create_chessboard()
        
        # Add rank labels (1-8) on the left
        for row in range(8):
            rank_label = tk.Label(
                self.board_frame, 
                text=str(8-row), 
                font=("Arial", 12, "bold"), 
                bg="#2c3e50", 
                fg="white",
                width=1
            )
            rank_label.grid(row=row, column=8, padx=(5, 0))
            
        # Add file labels (a-h) on the bottom
        for col in range(8):
            file_label = tk.Label(
                self.board_frame, 
                text=chr(97+col), 
                font=("Arial", 12, "bold"), 
                bg="#2c3e50",
                fg="white"
            )
            file_label.grid(row=8, column=col, pady=(5, 0))
        
        # Create styled info section
        info_header = tk.Label(
            right_frame, 
            text="Game Information", 
            font=("Arial", 14, "bold"), 
            bg="#3498db", 
            fg="white",
            padx=10,
            pady=5
        )
        info_header.pack(fill="x")
        
        # Player information section - enhanced for better visibility
        player_frame = tk.Frame(right_frame, bg="white", padx=10, pady=10, bd=1, relief="solid")
        player_frame.pack(fill="x")
        
        # Create a clearer, more visually organized player info layout
        player_header = tk.Label(
            player_frame, 
            text="Players", 
            font=("Arial", 14, "bold"), 
            bg="#3498db", 
            fg="white",
            padx=5,
            pady=2
        )
        player_header.pack(fill="x", anchor="w")
        
        # Player role indicator - will be updated in update_from_server
        self.player_label = tk.Label(
            player_frame, 
            text="You: N/A", 
            font=("Arial", 12, "bold"), 
            bg="white",
            anchor="w",
            pady=5
        )
        self.player_label.pack(fill="x")
        
        # Opponent role indicator - will be updated in update_from_server
        self.opponent_label = tk.Label(
            player_frame, 
            text="Opponent: N/A", 
            font=("Arial", 12, "bold"), 
            bg="white",
            anchor="w", 
            pady=5
        )
        self.opponent_label.pack(fill="x")
        
        # Add a turn indicator that will be updated based on who's turn it is
        self.turn_indicator = tk.Label(
            player_frame,
            text="Waiting for game to start...",
            font=("Arial", 11, "italic"),
            bg="#f0f0f0",
            fg="#333333",
            pady=3,
            padx=5
        )
        self.turn_indicator.pack(fill="x", pady=(5, 0))
        
        # Timer section with styled appearance
        timer_frame = tk.Frame(right_frame, bg="#f5f5f5", padx=10, pady=10, bd=1, relief="solid")
        timer_frame.pack(fill="x", padx=10, pady=10)
        
        self.white_time_label = tk.Label(
            timer_frame, 
            text="White: 05:00", 
            font=("Arial", 12), 
            bg="#f5f5f5"
        )
        self.white_time_label.pack(anchor="w", pady=2)
        
        self.black_time_label = tk.Label(
            timer_frame, 
            text="Black: 05:00", 
            font=("Arial", 12), 
            bg="#f5f5f5"
        )
        self.black_time_label.pack(anchor="w", pady=2)
        
        # Move history section - make it shorter
        history_header = tk.Label(
            right_frame, 
            text="Move History", 
            font=("Arial", 14, "bold"), 
            bg="#3498db", 
            fg="white",
            padx=10,
            pady=5
        )
        history_header.pack(fill="x", pady=(10, 0))

        self.move_history_text = tk.Text(
            right_frame, 
            height=3,  # Reduced height to make more room for chat
            width=30, 
            state="disabled", 
            bg="#f5f5f5",
            font=("Courier New", 10)
        )
        self.move_history_text.pack(fill="x", padx=10, pady=5)

        # Chat section with improved layout
        chat_header = tk.Label(
            right_frame, 
            text="Chat", 
            font=("Arial", 14, "bold"), 
            bg="#3498db", 
            fg="white",
            padx=10,
            pady=5
        )
        chat_header.pack(fill="x", pady=(10, 0))

        chat_container = tk.Frame(right_frame, bg="#3498db", padx=2, pady=2)
        chat_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Use grid layout for chat_container
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_rowconfigure(1, weight=0)
        chat_container.grid_columnconfigure(0, weight=1)

        # Chat messages area (row 0)
        chat_display_frame = tk.Frame(chat_container, bg="white")
        chat_display_frame.grid(row=0, column=0, sticky="nsew")

        self.chat_text = tk.Text(
            chat_display_frame, 
            height=8,  # Set a reasonable max height
            width=30, 
            state="disabled", 
            bg="#f5f5f5",
            wrap="word",
            font=("Arial", 10)
        )
        chat_scroll = tk.Scrollbar(chat_display_frame, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scroll.set)
        self.chat_text.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        self.chat_text.config(state="normal")
        self.chat_text.insert(tk.END, "Chat messages will appear here.\n", "placeholder")
        self.chat_text.tag_configure("placeholder", foreground="#888888", font=("Arial", 10, "italic"))
        self.chat_text.config(state="disabled")

        # Chat input area (row 1, always at the bottom)
        chat_input_frame = tk.Frame(chat_container, bg="#f5f5f5", padx=2, pady=2)
        chat_input_frame.grid(row=1, column=0, sticky="ew")

        self.chat_entry = tk.Entry(
            chat_input_frame,
            font=("Consolas", 12),
            bg="white",
            fg="#222",
            bd=2,
            relief="groove",
            insertbackground="#3498db"
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(2, 0))
        self.chat_entry.bind("<Return>", self.send_chat_message)

        chat_send_button = tk.Button(
            chat_input_frame,
            text="Send",
            command=self.send_chat_message,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=2
        )
        chat_send_button.pack(side="right", padx=(5, 2))

        # Game control buttons
        controls_frame = tk.Frame(left_frame, bg="white", pady=10)
        controls_frame.pack(fill="x")
        
        # Store reference to controls frame
        self.controls_frame = controls_frame
        
        tk.Button(
            controls_frame, 
            text="Leave Game", 
            font=("Arial", 12), 
            bg="#e74c3c", 
            fg="white",
            padx=10,
            pady=5,
            command=self.leave_game
        ).pack(side="left", padx=5)
        
        tk.Button(
            controls_frame, 
            text="Offer Draw", 
            font=("Arial", 12), 
            bg="#f39c12", 
            fg="white",
            padx=10,
            pady=5,
            command=self.offer_draw
        ).pack(side="left", padx=5)
        
        tk.Button(
            controls_frame, 
            text="Resign", 
            font=("Arial", 12), 
            bg="#7f8c8d", 
            fg="white",
            padx=10,
            pady=5,
            command=self.resign
        ).pack(side="left", padx=5)

    def create_chessboard(self):
        """Create the initial chess board buttons."""
        try:
            # Clear any existing buttons
            for widget in self.board_frame.winfo_children():
                if isinstance(widget, tk.Button):
                    widget.destroy()
            
            # Reset buttons dictionary
            self.buttons = {}
            
            # Create new buttons for each square
            for row in range(8):
                for col in range(8):
                    square = chess.square(col, 7 - row)
                    piece = self.board.piece_at(square)
                    image = self.get_image(piece)
                    
                    # Alternating light and dark squares
                    is_light_square = (row + col) % 2 == 0
                    bg_color = "#f5f5dc" if is_light_square else "#b58863"  # Light beige and brown
                    
                    button = tk.Button(
                        self.board_frame, 
                        image=image,
                        width=64, height=64,
                        bg=bg_color, 
                        activebackground=bg_color
                    )
                    button.configure(command=lambda r=row, c=col: self.on_click(r, c))
                    button.grid(row=row, column=col)
                    self.buttons[(row, col)] = button
            
            logger.info("Chessboard created successfully")
        except Exception as e:
            logger.error(f"Error creating chessboard: {e}", exc_info=True)
            messagebox.showerror("Error", "Failed to create chessboard. Please restart the application.")
            
    def show_login(self):
        """Show the login UI."""
        self.lobby_frame.pack_forget()
        self.game_frame.pack_forget()
        self.login_frame.pack(expand=True)

    def show_lobby(self):
        """Show the lobby UI."""
        self.login_frame.pack_forget()
        self.game_frame.pack_forget()
        self.lobby_frame.pack(fill="both", expand=True)
        self.fetch_games()

    def show_game(self):
        """Show the game UI efficiently without transitions or old interfaces."""
        self.login_frame.pack_forget()
        self.lobby_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True)
        self.game_active = True
        if self.role == "white":
            self.board = chess.Board()
        try:
            self.create_chessboard()
        except Exception as e:
            logger.error(f"Error creating chessboard: {e}")
        self.update_timers()
        
        # Clear any previous chat messages
        self.chat_text.config(state="normal")
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.insert(tk.END, "Chat messages will appear here.\n", "placeholder")
        self.chat_text.config(state="disabled")
        
        # Function to recursively get all descendants of a widget
        def get_all_children(widget):
            children = widget.winfo_children()
            result = list(children)
            for child in children:
                result.extend(get_all_children(child))
            return result
        
        # Find and reconfigure chat send button for better visibility
        chat_send_button = None
        for widget in get_all_children(self.game_frame):
            if isinstance(widget, tk.Button) and widget.cget('text') == "Send":
                chat_send_button = widget
                break
        
        if self.is_spectator:
            self.root.title(f"Chess Nexus - Spectating Game")
            # Disable game control buttons for spectators
            for child in self.controls_frame.winfo_children():
                if child['text'] in ["Offer Draw", "Resign"]:
                    child.config(state="disabled")
            
            # Make sure chat is explicitly enabled for spectators
            self.chat_entry.config(state="normal")
            # Make the send button more visible for spectators
            if chat_send_button:
                chat_send_button.config(
                    text="Send (Spectator)",
                    bg="#9b59b6",  # Purple for spectators
                    fg="white",
                    font=("Arial", 10, "bold"),
                )
            
            # Add a special message for spectators
            self.chat_text.config(state="normal")
            self.chat_text.insert(tk.END, "You are in spectator mode. Your chat messages will be visible to all players and spectators.\n", "system")
            self.chat_text.tag_configure("system", foreground="#9b59b6", font=("Arial", 9, "italic"))
            self.chat_text.config(state="disabled")
        else:
            self.root.title(f"Chess Nexus - Playing as {self.role.capitalize()}")
            for child in self.controls_frame.winfo_children():
                child.config(state="normal")
            # Standard button for players
            if chat_send_button:
                chat_send_button.config(
                    text="Send",
                    bg="#3498db",  # Blue for players
                    fg="white",
                    font=("Arial", 10, "bold"),
                )
        
        # Focus the chat entry for quick typing
        self.root.update()
        self.focus_chat_entry()

    def enter_lobby(self):
        """Enter the lobby after username input."""
        username = self.username_entry.get().strip()
        if not username or username == "Enter your username":
            messagebox.showerror("Error", "Please enter a valid username.")
            return
        self.client.set_username(username)
        self.show_lobby()

    def fetch_games(self):
        """Fetch available games from the server."""
        self.client.request_games()

    def create_game(self):
        """Create a new game."""
        self.client.create_game()

    def join_game(self, game_id):
        """Join a game."""
        self.client.join_game(game_id)

    def spectate_game(self, game_id):
        """Spectate a game."""
        logger.info(f"Spectating game: {game_id}")
        self.client.spectate_game(game_id)
        self.is_spectator = True  # Set spectator flag
        
        # Show a message to the user
        messagebox.showinfo(
            "Spectator Mode", 
            "You are now spectating a game. You can observe moves and use the chat, but cannot make moves."
        )

    def leave_game(self):
        """Leave the current game and return to lobby."""
        self.client.leave_game()
        self.board = chess.Board()
        self.move_history = []
        self.move_history_text.config(state="normal")
        self.move_history_text.delete(1.0, tk.END)
        self.move_history_text.config(state="disabled")
        self.chat_text.config(state="normal")
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state="disabled")
        self.game_active = False
        self.show_lobby()

    def offer_draw(self):
        """Offer a draw (not fully implemented)."""
        messagebox.showinfo("Draw Offer", "Draw offer sent (not implemented).")

    def resign(self):
        """Resign from the game."""
        self.show_game_over("Resigned")
        self.leave_game()

    def on_click(self, row, col):
        """Handle a button click to make a move."""
        # Ignore clicks if spectating or game not active
        if not self.game_active:
            return

        # Special handling for spectators - show a message and return
        if self.is_spectator:
            messagebox.showinfo("Spectator Mode", "You are spectating this game and cannot make moves.")
            return

        # Get current turn and check if it's the player's turn
        current_turn = "white" if self.board.turn == chess.WHITE else "black"
        if self.role != current_turn:
            logger.debug(f"Not player's turn. Current turn: {current_turn}, Player role: {self.role}")
            messagebox.showinfo("Not Your Turn", f"It's {current_turn}'s turn to move.")
            return

        # Get the square and piece that was clicked
        square = chess.square(col, 7 - row)
        piece = self.board.piece_at(square)
        
        logger.debug(f"Clicked on square {chess.square_name(square)}, piece: {piece}")
        logger.debug(f"Current from_square: {chess.square_name(self.from_square) if self.from_square is not None else 'None'}")

        # First click - select a piece
        if self.from_square is None:
            # Can only select own pieces
            if piece and ((self.role == "white" and piece.color == chess.WHITE) or
                         (self.role == "black" and piece.color == chess.BLACK)):
                logger.debug(f"Selected piece at {chess.square_name(square)}")
                self.from_square = square
                
                # Reset colors first to ensure clean highlighting
                self.reset_board_colors()
                
                # Highlight selected piece
                self.buttons[(row, col)].config(bg="#ff9999")  # Red for selected piece
                
                # Highlight valid moves
                valid_move_count = 0
                for move in self.board.legal_moves:
                    if move.from_square == square:
                        valid_move_count += 1
                        to_row, to_col = 7 - chess.square_rank(move.to_square), chess.square_file(move.to_square)
                        self.buttons[(to_row, to_col)].config(bg="#aed6f1")  # Light blue for valid moves
                
                logger.debug(f"Highlighted {valid_move_count} valid moves for {chess.square_name(square)}")
            else:
                # Clicked on opponent's piece or empty square
                logger.debug(f"Cannot select {chess.square_name(square)} - not player's piece")
                messagebox.showinfo("Invalid Selection", "Please select one of your pieces.")
        
        # Second click - attempt to move
        else:
            # If clicking same square, deselect
            if self.from_square == square:
                logger.debug(f"Deselected piece at {chess.square_name(square)}")
                self.from_square = None
                self.reset_board_colors()
                return
                
            # Create move and check if valid
            move = chess.Move(self.from_square, square)
            
            # Try simple move first
            if move in self.board.legal_moves:
                # Valid move
                move_uci = move.uci()
                logger.debug(f"Valid move: {move_uci}")
                self.client.send_move(move_uci)
                # Reset selection
                self.from_square = None
                self.reset_board_colors()
            else:
                # Try checking for special moves (castling, en passant, promotion)
                found_move = False
                for legal_move in self.board.legal_moves:
                    if legal_move.from_square == self.from_square and legal_move.to_square == square:
                        move_uci = legal_move.uci()
                        logger.debug(f"Valid special move: {move_uci}")
                        self.client.send_move(move_uci)
                        found_move = True
                        # Reset selection
                        self.from_square = None
                        self.reset_board_colors()
                        break
                
                # If not a valid move, deselect current piece and try to select new one
                if not found_move:
                    logger.debug(f"Invalid move from {chess.square_name(self.from_square)} to {chess.square_name(square)}")
                    
                    if piece and ((self.role == "white" and piece.color == chess.WHITE) or
                                 (self.role == "black" and piece.color == chess.BLACK)):
                        # Switch selection to this piece
                        logger.debug(f"Switching selection to {chess.square_name(square)}")
                        self.from_square = square
                        self.reset_board_colors()
                        
                        # Highlight selected piece
                        self.buttons[(row, col)].config(bg="#ff9999")  # Red for new selection
                        
                        # Highlight valid moves for new selection
                        valid_move_count = 0
                        for move in self.board.legal_moves:
                            if move.from_square == square:
                                valid_move_count += 1
                                to_row, to_col = 7 - chess.square_rank(move.to_square), chess.square_file(move.to_square)
                                self.buttons[(to_row, to_col)].config(bg="#aed6f1")  # Light blue for valid moves
                        
                        logger.debug(f"Highlighted {valid_move_count} valid moves for {chess.square_name(square)}")
                    else:
                        # Invalid move and not a new selection, just reset
                        logger.debug("Invalid move and not a valid new selection")
                        messagebox.showinfo("Invalid Move", "That move is not allowed.")
                        self.from_square = None
                        self.reset_board_colors()

    def reset_board_colors(self):
        """Reset the board square colors."""
        logger.debug("Resetting board colors")
        try:
            for row in range(8):
                for col in range(8):
                    if (row, col) not in self.buttons:
                        logger.warning(f"Button at ({row}, {col}) not found during color reset")
                        continue
                    
                    is_light = (row + col) % 2 == 0
                    self.buttons[(row, col)].config(bg="#f5f5dc" if is_light else "#b58863")  # Light/dark colors
        except Exception as e:
            logger.error(f"Error resetting board colors: {e}")
            # Try to recreate the board if reset fails
            try:
                self.create_chessboard()
            except Exception as board_error:
                logger.error(f"Failed to recreate board after color reset error: {board_error}")

    def show_promotion_dialog(self):
        """Show a dialog for pawn promotion and return the chosen piece type."""
        promotion_window = tk.Toplevel(self.root)
        promotion_window.title("Promote Pawn")
        promotion_window.geometry("300x100")
        promotion_window.transient(self.root)
        promotion_window.grab_set()
        
        result = [None]  # Using a list to store the result as a mutable reference
        
        tk.Label(promotion_window, text="Choose piece for promotion:").pack(pady=5)
        
        buttons_frame = tk.Frame(promotion_window)
        buttons_frame.pack()
        
        pieces = [
            ("Queen", chess.QUEEN), 
            ("Rook", chess.ROOK), 
            ("Bishop", chess.BISHOP), 
            ("Knight", chess.KNIGHT)
        ]
        
        for name, piece_type in pieces:
            tk.Button(
                buttons_frame, 
                text=name, 
                command=lambda p=piece_type: [result.append(p), promotion_window.destroy()]
            ).pack(side=tk.LEFT, padx=5)
        
        # Wait for the window to be destroyed
        self.root.wait_window(promotion_window)
        
        return result[-1] if len(result) > 1 else None

    def update_gui(self, preserve_highlights=False):
        """Update the chessboard GUI."""
        try:
            for row in range(8):
                for col in range(8):
                    if (row, col) not in self.buttons:
                        logger.warning(f"Button at ({row}, {col}) not found")
                        continue
                        
                    square = chess.square(col, 7 - row)
                    piece = self.board.piece_at(square)
                    image = self.get_image(piece)
                    
                    # Preserve highlighted squares if requested
                    if preserve_highlights:
                        current_bg = self.buttons[(row, col)].cget("bg")
                        if current_bg in ["#d5f5e3", "#82e0aa", "#aed6f1", "#ff9999"]:
                            # Only update the image, not the background
                            self.buttons[(row, col)].config(image=image)
                            continue
                    
                    # Normal coloring for non-highlighted squares
                    is_light_square = (row + col) % 2 == 0
                    bg_color = "#f5f5dc" if is_light_square else "#b58863"  # Light beige and brown
                    
                    # Update both image and background color
                    self.buttons[(row, col)].config(image=image, bg=bg_color)
        except Exception as e:
            logger.error(f"Error updating GUI: {e}", exc_info=True)
            # Try to recreate the board if update fails
            try:
                self.create_chessboard()
            except Exception as board_error:
                logger.error(f"Failed to recreate board: {board_error}")
                
    def update_from_server(self, data):
        """Update the GUI based on server data."""
        try:
            # Update board state
            if "board_fen" in data:
                logger.debug(f"Received board update FEN: {data['board_fen']}")
                
                # Store old board state to detect changes
                old_board = self.board.copy()
                old_move_stack = self.board.move_stack.copy() if hasattr(self.board, 'move_stack') and self.board.move_stack else []
                
                # Update board
                self.board = update_game_state(self.board, data["board_fen"])
                
                # Reset any selection when board is updated from server
                self.from_square = None
                
                # Safely update the GUI
                try:
                    # Check if a new move was made
                    if hasattr(self.board, 'move_stack') and len(self.board.move_stack) > len(old_move_stack):
                        logger.debug("New move detected, highlighting last move")
                        try:
                            self.highlight_last_move()
                        except Exception as highlight_error:
                            logger.error(f"Error highlighting last move: {highlight_error}")
                            try:
                                self.reset_board_colors()
                                self.update_gui()
                            except Exception as update_error:
                                logger.error(f"Error updating GUI after highlight failure: {update_error}")
                    else:
                        # Just update the board normally
                        try:
                            self.reset_board_colors()
                            self.update_gui()
                        except Exception as update_error:
                            logger.error(f"Error updating GUI: {update_error}")
                except Exception as e:
                    logger.error(f"Error in board update logic: {e}")
            
            # Update player and opponent information - with improved visibility
            try:
                # Get player usernames (never show IDs)
                white_player = data.get("white_username") or data.get("white_player") or "Unknown"
                black_player = data.get("black_username") or data.get("black_player") or "Unknown"
                # Remove UUIDs if present
                if isinstance(white_player, str) and len(white_player) > 20 and '-' in white_player:
                    white_player = "Unknown"
                if isinstance(black_player, str) and len(black_player) > 20 and '-' in black_player:
                    black_player = "Unknown"
                if self.is_spectator:
                    self.player_label.config(
                        text=f"Spectating as: {self.client.username or 'Unknown'}",
                        font=("Arial", 12, "bold"),
                        bg="white", fg="#3498db"
                    )
                    self.opponent_label.config(
                        text=f"White: {white_player}   |   Black: {black_player}",
                        font=("Arial", 12, "bold"),
                        bg="#f0f0f0", fg="#333333",
                        padx=5, pady=5
                    )
                else:
                    role_color = "#3498db" if self.role == "white" else "#34495e"
                    self.player_label.config(
                        text=f"You: {self.client.username or 'Unknown'} ({self.role.capitalize()})",
                        font=("Arial", 12, "bold"),
                        bg="white", fg=role_color
                    )
                    opponent_role = "Black" if self.role == "white" else "White"
                    opponent_name = black_player if self.role == "white" else white_player
                    opponent_color = "#34495e" if self.role == "white" else "#3498db"
                    self.opponent_label.config(
                        text=f"Opponent: {opponent_name or 'Unknown'} ({opponent_role})",
                        font=("Arial", 12, "bold"),
                        bg="#f0f0f0", fg=opponent_color,
                        padx=5, pady=5
                    )
            except Exception as player_error:
                logger.error(f"Error updating player labels: {player_error}")
            
            # Update turn and time information
            try:
                if "turn" in data and "time_remaining" in data:
                    turn = data["turn"]
                    time_white = data["time_remaining"]["white"]
                    time_black = data["time_remaining"]["black"]
                    
                    # Update turn indicator with clear message about whose turn it is
                    if turn == "white":
                        white_name = data.get("white_player", "White")
                        self.turn_indicator.config(
                            text=f"Currently {white_name}'s turn (White)",
                            bg="#e3f2fd",  # Light blue background
                            fg="#0d47a1"   # Dark blue text
                        )
                    else:
                        black_name = data.get("black_player", "Black")
                        self.turn_indicator.config(
                            text=f"Currently {black_name}'s turn (Black)",
                            bg="#efebe9",  # Light brown background
                            fg="#3e2723"   # Dark brown text
                        )
                    
                    # Format time display more clearly with colored indicators for current turn
                    if turn == "white":
                        self.white_time_label.config(
                            text=f"White's turn: {format_time(time_white)}",
                            font=("Arial", 12, "bold"),
                            bg="white", fg="#3498db"
                        )
                        self.black_time_label.config(
                            text=f"Black: {format_time(time_black)}",
                            font=("Arial", 12),
                            bg="white", fg="#34495e"
                        )
                    else:
                        self.white_time_label.config(
                            text=f"White: {format_time(time_white)}",
                            font=("Arial", 12),
                            bg="white", fg="#3498db"
                        )
                        self.black_time_label.config(
                            text=f"Black's turn: {format_time(time_black)}",
                            font=("Arial", 12, "bold"),
                            bg="white", fg="#34495e"
                        )
            except Exception as time_error:
                logger.error(f"Error updating time labels: {time_error}")
            
            # Update move history if available
            try:
                if "move_history" in data and data["move_history"]:
                    self.move_history = data["move_history"]
                    self.update_move_history()
            except Exception as history_error:
                logger.error(f"Error updating move history: {history_error}")
            
            # Check if game is over
            if data.get("is_game_over", False):
                self.show_game_over(data["result"])
                
        except Exception as e:
            logger.error(f"Error updating from server: {e}")
            logger.error(f"Error details: {str(e)}", exc_info=True)  # Log traceback
            
            # Try to recover the board at least
            try:
                self.update_gui()
            except Exception as recover_error:
                logger.error(f"Error recovering board display: {recover_error}")
                
            # Only show error to user if we haven't already shown too many
            if not hasattr(self, '_error_count'):
                self._error_count = 0
            
            if self._error_count < 2:  # Limit error dialogs to prevent spamming
                self._error_count += 1
                self.show_error("Update Error", f"Game may not display correctly. Try leaving and rejoining.")

    def highlight_last_move(self):
        """Highlight the last move made on the board."""
        try:
            self.reset_board_colors()
            
            if hasattr(self.board, 'move_stack') and len(self.board.move_stack) > 0:
                last_move = self.board.move_stack[-1]
                logger.debug(f"Highlighting last move: {last_move.uci()}")
                
                from_square = last_move.from_square
                to_square = last_move.to_square
                
                # Convert chess squares to GUI coordinates
                from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
                to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)
                
                # Highlight source square with light green
                if (from_row, from_col) in self.buttons:
                    self.buttons[(from_row, from_col)].config(bg="#d5f5e3")  # Light green
                
                # Highlight destination square with slightly darker green
                if (to_row, to_col) in self.buttons:
                    self.buttons[(to_row, to_col)].config(bg="#82e0aa")  # Darker green
                
                logger.debug(f"Highlighted from {chess.square_name(from_square)} to {chess.square_name(to_square)}")
            
            self.update_gui(preserve_highlights=True)
        except Exception as e:
            logger.error(f"Error highlighting last move: {e}", exc_info=True)

    def update_timers(self):
        """Update timers every second (handled by server updates)."""
        if self.game_active:
            self.root.after(1000, self.update_timers)

    def update_move_history(self):
        """Update the move history display."""
        self.move_history_text.config(state="normal")
        self.move_history_text.delete(1.0, tk.END)
        if not self.move_history:
            self.move_history_text.insert(tk.END, "No moves yet")
        else:
            for i, move in enumerate(self.move_history, 1):
                self.move_history_text.insert(tk.END, f"{i}. {move}\n")
        self.move_history_text.config(state="disabled")

    def display_chat_message(self, sender_id, message):
        """Display a chat message with improved formatting."""
        logger.info(f"GUI DISPLAYING CHAT: sender='{sender_id}', message='{message}'")
        print(f"GUI DISPLAYING CHAT: sender='{sender_id}', message='{message}'")
        
        try:
            # Make sure we can write to the chat area
            if not hasattr(self, 'chat_text') or not self.chat_text:
                logger.error("Chat text widget not available")
                print("Chat text widget not available")
                return
                
            self.chat_text.config(state="normal")
            
            # Clear placeholder text if this is the first message
            current_text = self.chat_text.get(1.0, tk.END).strip()
            if "Chat messages will appear here" in current_text or "You are in spectator mode" in current_text:
                # Clear the chat window completely
                self.chat_text.delete(1.0, tk.END)
                logger.info("Cleared placeholder text from chat window")
                print("Cleared placeholder text from chat window")
            
            # Add timestamp
            timestamp = time.strftime("%H:%M", time.localtime())
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            
            # Determine sender type and format accordingly
            is_self = False
            role_tag = ""
            color = "#e74c3c"  # Default red color
            display_name = sender_id
            
            if isinstance(sender_id, str):
                # Extract username and role from sender ID
                if "[White]" in sender_id:
                    role_tag = "[White]"
                    display_name = sender_id.split("[")[0].strip()
                    color = "#3498db"  # Blue
                elif "[Black]" in sender_id:
                    role_tag = "[Black]"
                    display_name = sender_id.split("[")[0].strip() 
                    color = "#34495e"  # Dark gray
                elif "[Spectator]" in sender_id:
                    role_tag = "[Spectator]"
                    display_name = sender_id.split("[")[0].strip()
                    color = "#9b59b6"  # Purple
                    logger.info(f"Processing spectator message from {display_name}")
                    print(f"Processing spectator message from {display_name}")
                
                # Check if this is a message from the current user
                if self.client and display_name == self.client.username:
                    is_self = True
                    logger.debug(f"Identified message as from self: {display_name} == {self.client.username}")
                    print(f"Identified message as from self: {display_name} == {self.client.username}")
            
            # Format the message according to sender
            if is_self:
                self.chat_text.insert(tk.END, f"You {role_tag}: ", "self")
                logger.debug("Formatted as self message")
                print("Formatted as self message")
            else:
                self.chat_text.insert(tk.END, f"{display_name} {role_tag}: ", "other")
                logger.debug(f"Formatted as message from others: {display_name}")
                print(f"Formatted as message from others: {display_name}")
            
            # Add the actual message text
            self.chat_text.insert(tk.END, f"{message}\n", "message")
            
            # Configure text tags
            self.chat_text.tag_configure("timestamp", foreground="#7f8c8d", font=("Arial", 8))
            self.chat_text.tag_configure("self", foreground="#3498db", font=("Arial", 10, "bold"))
            self.chat_text.tag_configure("other", foreground=color, font=("Arial", 10, "bold"))
            self.chat_text.tag_configure("message", foreground="black", font=("Arial", 10))
            
            # Update display and ensure the new message is visible
            self.chat_text.config(state="disabled")
            self.chat_text.see(tk.END)
            
            logger.info("Chat message displayed successfully")
            print("Chat message displayed successfully")
            
            # Force GUI update to make sure the message is displayed immediately
            self.root.update_idletasks()
            
        except Exception as e:
            logger.error(f"Error displaying chat message: {e}", exc_info=True)
            print(f"Error displaying chat message: {e}")
            # Try to recover the chat display
            try:
                self.chat_text.config(state="disabled")
            except:
                pass

    def send_chat_message(self, event=None):
        """Send a chat message to the server and display it locally to ensure visibility."""
        message = self.chat_entry.get().strip()
        if message:
            # Log sending the message
            logger.info(f"Sending chat message: '{message}', is_spectator: {self.is_spectator}")
            print(f"Sending chat message: '{message}', is_spectator: {self.is_spectator}")
            
            # Send the message to the server
            self.client.send_chat(message)
            
            # For spectators, manually display the message locally
            # This ensures it appears even if the server broadcast fails
            if self.is_spectator:
                # Create a properly formatted spectator message
                display_name = f"{self.client.username} [Spectator]"
                logger.info(f"Locally displaying spectator message: {display_name}: {message}")
                print(f"Locally displaying spectator message: {display_name}: {message}")
                
                self.display_chat_message(display_name, message)
            
            # Clear the input field
            self.chat_entry.delete(0, tk.END)
            
            # Focus the entry field again for continued chatting
            self.chat_entry.focus_set()
        return 'break'

    def show_game_over(self, result):
        """Show the game over message."""
        self.game_active = False
        messagebox.showinfo("Game Over", f"Game Over! Result: {result}")
        self.leave_game()

    def show_error(self, title, message):
        """Show an error message."""
        messagebox.showerror(title, message)

    def focus_chat_entry(self):
        """Set focus to chat entry field."""
        try:
            if hasattr(self, 'chat_entry'):
                self.chat_entry.focus_set()
        except Exception as e:
            logger.error(f"Error focusing chat entry: {e}")

def main():
    root = tk.Tk()
    client = ChessClient("127.0.0.1", 5555)
    client.connect_to_server()
    gui = ChessGUI(root, client)
    client.set_gui(gui)
    root.mainloop()

if __name__ == "__main__":
    main()