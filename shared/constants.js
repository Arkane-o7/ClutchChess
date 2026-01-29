// Shared constants between client and server
export const GAME_CONFIG = {
    // Board dimensions
    BOARD_SIZE: 8,
    TILE_SIZE: 75,
    LOGIC_SIZE: 600,

    // Mana system
    MANA_MAX: 6,
    MANA_START: 4,
    MANA_REGEN_PER_SECOND: 0.8,
    MANA_COST_PER_MOVE: 1,

    // Movement
    MOVE_SPEED: 250,
    PAWN_ATTACK_SPEED: 500,
    KNIGHT_JUMP_HEIGHT: 8,

    // Collision
    COLLISION_RADIUS: 20,

    // Server
    TICK_RATE: 60,
    SYNC_RATE: 20
};

export const PIECE_TYPES = {
    PAWN: 'p',
    ROOK: 'r',
    KNIGHT: 'n',
    BISHOP: 'b',
    QUEEN: 'q',
    KING: 'k'
};

export const GAME_STATES = {
    WAITING: 'waiting',
    PLAYING: 'playing',
    GAME_OVER: 'game_over'
};

export const SOCKET_EVENTS = {
    // Connection
    CONNECT: 'connect',
    DISCONNECT: 'disconnect',

    // Matchmaking
    FIND_MATCH: 'find_match',
    CANCEL_MATCH: 'cancel_match',
    MATCH_FOUND: 'match_found',

    // Lobby
    CREATE_ROOM: 'create_room',
    JOIN_ROOM: 'join_room',
    ROOM_CREATED: 'room_created',
    ROOM_JOINED: 'room_joined',
    ROOM_ERROR: 'room_error',

    // Game
    GAME_START: 'game_start',
    MOVE_PIECE: 'move_piece',
    GAME_STATE: 'game_state',
    PIECE_MOVED: 'piece_moved',
    PIECE_CAPTURED: 'piece_captured',
    GAME_OVER: 'game_over',

    // Player
    PLAYER_JOINED: 'player_joined',
    PLAYER_LEFT: 'player_left'
};
