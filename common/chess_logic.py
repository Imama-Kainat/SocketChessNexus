import chess

class ChessGame:
    """Class to manage a chess game."""
    
    def __init__(self):
        """Initialize a new chess game."""
        self.board = chess.Board()
        self.move_history = []

    def get_turn(self):
        """Get the current turn ('white' or 'black')."""
        return "white" if self.board.turn == chess.WHITE else "black"

    def make_move(self, move_uci):
        """Make a move on the board."""
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in self.board.legal_moves:
                return False
            self.board.push(move)
            self.move_history.append(move_uci)
            return True
        except:
            return False

    def get_board_fen(self):
        """Get the current board state in FEN notation."""
        return self.board.fen()

    def get_board_representation(self):
        """Get a string representation of the board."""
        return str(self.board)

    def is_check(self):
        """Check if the current position is in check."""
        return self.board.is_check()

    def is_checkmate(self):
        """Check if the current position is checkmate."""
        return self.board.is_checkmate()

    def is_stalemate(self):
        """Check if the current position is stalemate."""
        return self.board.is_stalemate()

    def is_game_over(self):
        """Check if the game is over."""
        return self.board.is_game_over()

    def get_result(self):
        """Get the game result."""
        if not self.is_game_over():
            return "Game in progress"
        if self.board.is_checkmate():
            winner = "Black" if self.get_turn() == "white" else "White"
            return f"Checkmate - {winner} wins"
        if self.board.is_stalemate():
            return "Draw - Stalemate"
        if self.board.is_insufficient_material():
            return "Draw - Insufficient material"
        if self.board.is_fifty_moves():
            return "Draw - 50-move rule"
        if self.board.is_repetition():
            return "Draw - Threefold repetition"
        return "Game ended"