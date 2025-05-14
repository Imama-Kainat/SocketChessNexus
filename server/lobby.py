import logging
from typing import Dict, List, Set, Optional, Tuple
from common.constants import WAITING, PLAYING, FINISHED
from server.utils import generate_unique_id

logger = logging.getLogger('lobby')

class GameLobby:
    """Game lobby for matchmaking."""
    
    def __init__(self):
        """Initialize a game lobby."""
        self.games: Dict[str, Tuple[str, List[str], Set[str]]] = {}
        self.player_game_map: Dict[str, str] = {}
        self.spectator_game_map: Dict[str, str] = {}
        self.waiting_players: List[str] = []
        self.spectators: Dict[str, Set[str]] = {}
        self.client_game_map: Dict[str, str] = {}

    def create_game(self, player_id: str) -> str:
        """Create a new game and add the player to it."""
        game_id = generate_unique_id()
        self.games[game_id] = (WAITING, [player_id], set())
        self.player_game_map[player_id] = game_id
        logger.info(f"Player {player_id} created game {game_id}")
        return game_id

    def join_game(self, game_id: str, player_id: str) -> bool:
        """Join an existing game."""
        if game_id not in self.games:
            logger.warning(f"Game {game_id} not found")
            return False
        game_state, players, spectators = self.games[game_id]
        if game_state != WAITING:
            logger.warning(f"Game {game_id} is not in waiting state")
            return False
        if len(players) >= 2:
            logger.warning(f"Game {game_id} is full")
            return False
        players.append(player_id)
        self.player_game_map[player_id] = game_id
        if len(players) == 2:
            self.games[game_id] = (PLAYING, players, spectators)
            logger.info(f"Game {game_id} started with players {players}")
        logger.info(f"Player {player_id} joined game {game_id}")
        return True

    def join_random_game(self, player_id: str) -> Optional[str]:
        """Join a random game that is waiting for players."""
        for game_id, (game_state, players, _) in self.games.items():
            if game_state == WAITING and len(players) < 2:
                if self.join_game(game_id, player_id):
                    return game_id
        return self.create_game(player_id)

    def leave_game(self, client_id: str) -> None:
        """
        Leave a game.
        
        Args:
            client_id: The ID of the client leaving the game
        """
        # First check if this is a player
        if client_id in self.player_game_map:
            game_id = self.player_game_map[client_id]
            game_state, players, spectators = self.games[game_id]
            players.remove(client_id)
            del self.player_game_map[client_id]
            if not players:
                # No more players, remove the game
                del self.games[game_id]
                logger.info(f"Game {game_id} removed (no players)")
            elif len(players) == 1 and game_state == PLAYING:
                # One player left, mark the game as finished
                self.games[game_id] = (FINISHED, players, spectators)
                logger.info(f"Game {game_id} finished (forfeit)")
            logger.info(f"Player {client_id} left game {game_id}")
            return
            
        # Check if this is a spectator
        if client_id in self.client_game_map:
            game_id = self.client_game_map[client_id]
            if game_id in self.spectators and client_id in self.spectators[game_id]:
                self.spectators[game_id].remove(client_id)
                logger.info(f"Spectator {client_id} removed from game {game_id}")
            del self.client_game_map[client_id]
            logger.info(f"Spectator {client_id} left game {game_id}")
            return
            
        # Legacy spectator handling
        if client_id in self.spectator_game_map:
            game_id = self.spectator_game_map[client_id]
            game_state, players, spectators = self.games[game_id]
            spectators.remove(client_id)
            del self.spectator_game_map[client_id]
            self.games[game_id] = (game_state, players, spectators)
            logger.info(f"Legacy spectator {client_id} left game {game_id}")
            return
            
        logger.warning(f"Client {client_id} not found in any game")
        return

    def spectate_game(self, game_id: str, spectator_id: str) -> bool:
        """
        Add a spectator to a game.
        
        Args:
            game_id: The ID of the game to spectate
            spectator_id: The ID of the client who wants to spectate
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if the game exists
        if game_id not in self.games:
            logger.warning(f"Game {game_id} not found for spectating")
            return False
        
        # Add to spectators set
        if game_id not in self.spectators:
            self.spectators[game_id] = set()
        
        # Add the spectator to the spectators set for this game
        self.spectators[game_id].add(spectator_id)
        
        # Add client to the client-to-game mapping
        self.client_game_map[spectator_id] = game_id
        
        logger.info(f"Added spectator {spectator_id} to game {game_id}")
        logger.info(f"Game {game_id} now has {len(self.spectators.get(game_id, set()))} spectators")
        
        return True

    def stop_spectating(self, spectator_id: str) -> None:
        """Stop spectating a game."""
        if spectator_id not in self.spectator_game_map:
            logger.warning(f"Spectator {spectator_id} not spectating any game")
            return
        game_id = self.spectator_game_map[spectator_id]
        game_state, players, spectators = self.games[game_id]
        spectators.remove(spectator_id)
        del self.spectator_game_map[spectator_id]
        self.games[game_id] = (game_state, players, spectators)
        logger.info(f"Spectator {spectator_id} stopped spectating game {game_id}")

    def get_game_state(self, game_id: str) -> Optional[str]:
        """Get the state of a game."""
        if game_id not in self.games:
            return None
        return self.games[game_id][0]

    def get_players(self, game_id: str) -> Optional[List[str]]:
        """Get the players in a game."""
        if game_id not in self.games:
            return None
        return self.games[game_id][1]

    def get_spectators(self, game_id: str) -> Optional[Set[str]]:
        """Get the spectators in a game."""
        if game_id not in self.games:
            return None
        return self.games[game_id][2]

    def get_game_id(self, client_id: str) -> Optional[str]:
        """
        Get the game ID for a client.
        
        Args:
            client_id: The ID of the client
            
        Returns:
            The ID of the game the client is in, or None if not in a game
        """
        # Check if they are a player
        game_id = self.player_game_map.get(client_id)
        if game_id:
            return game_id
            
        # Check if they are a spectator
        game_id = self.client_game_map.get(client_id)
        if game_id:
            logger.info(f"Found client {client_id} as spectator in game {game_id}")
            return game_id
            
        # Check legacy spectator map (for backward compatibility)
        game_id = self.spectator_game_map.get(client_id)
        if game_id:
            logger.info(f"Found client {client_id} in legacy spectator map for game {game_id}")
            return game_id
            
        logger.warning(f"Client {client_id} not found in any game")
        return None

    def get_opponent(self, player_id: str) -> Optional[str]:
        """Get the opponent of a player."""
        game_id = self.player_game_map.get(player_id)
        if not game_id:
            return None
        players = self.games[game_id][1]
        if len(players) < 2:
            return None
        return players[0] if players[1] == player_id else players[1]

    def get_game_ids(self) -> List[str]:
        """Get all game IDs."""
        return list(self.games.keys())

    def get_active_games(self) -> List[str]:
        """Get all active game IDs."""
        return [game_id for game_id, (state, _, _) in self.games.items() if state == PLAYING]

    def get_waiting_games(self) -> List[str]:
        """Get all waiting game IDs."""
        return [game_id for game_id, (state, _, _) in self.games.items() if state == WAITING]