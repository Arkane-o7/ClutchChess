# Claude Code Project Context

## Project Overview
Kung Fu Chess - a real-time chess variant where pieces move simultaneously with cooldowns and collision-based captures.

## Project Structure
```
kfchess-cc/
├── docs/                    # Documentation
│   └── ARCHITECTURE.md      # Full architecture reference
├── KFCHESS_ORIGINAL_IMPLEMENTATION.md  # Legacy implementation details
├── server/                  # Python backend (FastAPI)
│   ├── src/kfchess/        # Source code
│   │   ├── game/           # Game engine (engine.py, board.py, moves.py, collision.py, state.py)
│   │   ├── api/            # HTTP API routes
│   │   ├── ws/             # WebSocket handlers
│   │   ├── ai/             # AI system (MCTS)
│   │   └── db/             # Database layer
│   ├── tests/              # pytest tests
│   ├── alembic/            # Database migrations
│   └── pyproject.toml
├── client/                  # TypeScript frontend (React + Vite + PixiJS)
│   ├── src/
│   └── package.json
└── docker-compose.yml       # Dev infrastructure (PostgreSQL, Redis)
```

## Development Commands

### Backend (server/)
```bash
# Use uv for all Python operations
uv sync                      # Install dependencies
uv run alembic upgrade head  # Run migrations
uv run uvicorn kfchess.main:app --reload --port 8000  # Dev server

# Tests
.venv/bin/pytest tests/ -v   # Run all tests
.venv/bin/pytest tests/unit/game/ -v  # Run game engine tests only

# Linting
uv run ruff check src/
uv run ruff format src/
```

### Frontend (client/)
```bash
npm install                  # Install dependencies
npm run dev                  # Dev server (Vite)
npm run build               # Production build
npm test                    # Run tests (Vitest)
```

### Infrastructure
```bash
docker-compose up -d postgres redis  # Start dev databases
```

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Redis, PostgreSQL
- **Frontend**: React 18, TypeScript 5, Vite, Zustand, PixiJS
- **Package Manager**: uv (Python), npm (TypeScript)
- **Linting**: Ruff (Python)
- **Testing**: pytest + pytest-asyncio (Python), Vitest (TypeScript)

## Game Engine Key Concepts
- **Tick-based**: 10 ticks/second (100ms tick period)
- **Mutable state**: Engine functions mutate state in place for performance. Use `GameState.copy()` if you need to preserve state (e.g., for AI lookahead)
- **Speed configs**: Standard (1s/square, 10s cooldown) and Lightning (0.2s/square, 2s cooldown)
- **Collision detection**: Pieces capture when within 0.4 squares distance
- **Knight mechanics**: Airborne (invisible) for 85% of move, can capture at 85%+
- **Castling**: King move includes extra_move for the rook

## Key Files for Game Logic
- `server/src/kfchess/game/engine.py` - Core game logic, tick processing
- `server/src/kfchess/game/moves.py` - Move validation, path computation
- `server/src/kfchess/game/collision.py` - Collision detection, capture logic
- `server/src/kfchess/game/state.py` - GameState dataclass, serialization
- `server/src/kfchess/game/board.py` - Board representation
- `server/src/kfchess/game/pieces.py` - Piece types and definitions

## Environment
- Copy `server/.env.example` to `server/.env`
- DEV_MODE=true bypasses authentication
