import chess
import logging

logger = logging.getLogger(__name__)

def is_valid_move(board, move_uci):
    """Check if the move is valid using chess logic."""
    try:
        # Handle promotion moves
        if len(move_uci) == 5:  # e.g. e7e8q for promotion
            from_square = chess.parse_square(move_uci[0:2])
            to_square = chess.parse_square(move_uci[2:4])
            promotion_piece = move_uci[4]
            move = chess.Move(from_square, to_square, promotion={"q": chess.QUEEN, "r": chess.ROOK, 
                                                              "b": chess.BISHOP, "n": chess.KNIGHT}[promotion_piece])
        else:
            # Regular move
            from_square = chess.parse_square(move_uci[0:2])
            to_square = chess.parse_square(move_uci[2:4])
            move = chess.Move(from_square, to_square)
        
        # Check if the move is in the list of legal moves
        is_legal = move in board.legal_moves
        
        if not is_legal:
            logger.debug(f"Move {move_uci} is not legal on board: {board.fen()}")
            legal_moves = [m.uci() for m in board.legal_moves]
            logger.debug(f"Legal moves: {legal_moves}")
            
        return is_legal
        
    except Exception as e:
        logger.error(f"Error validating move {move_uci}: {str(e)}")
        return False

def update_game_state(board, fen):
    """Update the game state from FEN string."""
    try:
        board.set_fen(fen)
    except Exception as e:
        logger.error(f"Error updating board state: {str(e)}")
    return board

def format_time(seconds):
    """Format time in seconds to MM:SS."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"