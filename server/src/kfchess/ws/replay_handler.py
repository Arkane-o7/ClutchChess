"""WebSocket handler for replay playback.

TODO (Distributed/Multi-Server):
--------------------------------
In a distributed deployment, replay sessions may need to migrate between servers:

1. Session Resume Protocol:
   - Client reconnects with: {"type": "resume", "tick": N, "was_playing": bool}
   - Server loads replay from DB, seeks to tick N, optionally resumes playback
   - This allows seamless handoff when server goes down or load balancer reassigns

2. Keyframe Caching:
   - Store GameState snapshots in Redis every 100 ticks during first playback
   - On session resume, load nearest keyframe to reduce seek cost from O(n) to O(n/100)
   - Key format: "replay:{game_id}:keyframe:{tick}"
   - Consider TTL for cache eviction (e.g., 24 hours)

3. Session State in Redis:
   - Optionally store session state (current_tick, is_playing) in Redis
   - Allows any server to resume a session without client providing tick
   - Key format: "replay:{game_id}:session:{session_id}"
"""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from kfchess.db.repositories.replays import ReplayRepository
from kfchess.db.session import async_session_factory
from kfchess.replay.session import ReplaySession
from kfchess.utils.display_name import resolve_player_info

logger = logging.getLogger(__name__)


async def _send_error_and_close(websocket: WebSocket, message: str) -> None:
    """Send an error message and close the WebSocket connection.

    Handles the case where the WebSocket may have disconnected before we
    can send the error message.

    Args:
        websocket: The WebSocket connection
        message: Error message to send
    """
    try:
        await websocket.send_json(
            {
                "type": "error",
                "message": message,
            }
        )
    except Exception:
        # Client already disconnected, ignore
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            # Already closed, ignore
            pass


async def handle_replay_websocket(websocket: WebSocket, game_id: str) -> None:
    """Handle a WebSocket connection for replay playback.

    Args:
        websocket: The WebSocket connection
        game_id: The game ID to load replay for

    Protocol:
    1. Client connects to /ws/replay/{game_id}
    2. Server sends replay_info message with metadata
    3. Server sends initial state message at tick 0
    4. Client sends control messages: play, pause, seek
    5. Server streams state messages during playback
    6. Server sends game_over when replay reaches the end
    """
    logger.info(f"Replay WebSocket connection attempt: game_id={game_id}")

    await websocket.accept()

    # Load replay from database and resolve player names
    replay = None
    resolved_players = None
    try:
        async with async_session_factory() as db_session:
            repository = ReplayRepository(db_session)
            replay = await repository.get_by_id(game_id)

            if replay is not None:
                # Resolve player display names while we have the session
                resolved_players = await resolve_player_info(db_session, replay.players)
    except Exception as e:
        logger.exception(f"Failed to load replay {game_id}: {e}")
        await _send_error_and_close(websocket, "Failed to load replay")
        return

    if replay is None:
        logger.warning(f"Replay {game_id} not found")
        await _send_error_and_close(websocket, "Replay not found")
        return

    logger.info(f"Loaded replay {game_id}: {len(replay.moves)} moves, {replay.total_ticks} ticks")

    # Create session and start
    session = ReplaySession(replay, websocket, game_id, resolved_players)

    try:
        await session.start()
    except Exception as e:
        logger.warning(f"Failed to start replay session {game_id}: {e}")
        await session.close()
        return

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info(f"Replay client disconnected: {game_id}")
                break

            # Parse message
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid JSON",
                        }
                    )
                except Exception:
                    # Client disconnected during error send
                    break
                continue

            # Handle message
            # TODO (Distributed): Add support for "resume" message type:
            #   {"type": "resume", "tick": N, "was_playing": bool}
            # This would call session.seek(tick) then optionally session.play()
            try:
                await session.handle_message(message)
            except Exception as e:
                logger.warning(f"Error handling message for {game_id}: {e}")
                # Don't break - allow session to continue if possible

    except Exception as e:
        logger.exception(f"Error in replay WebSocket handler for {game_id}: {e}")
    finally:
        await session.close()
