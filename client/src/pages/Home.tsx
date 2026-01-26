import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLobbyStore } from '../stores/lobby';

type BoardType = 'standard' | 'four_player';

function Home() {
  const navigate = useNavigate();
  const createLobby = useLobbyStore((s) => s.createLobby);
  const connect = useLobbyStore((s) => s.connect);

  const [isCreating, setIsCreating] = useState(false);
  const [selectedBoardType, setSelectedBoardType] = useState<BoardType>('standard');
  const [showBoardTypeModal, setShowBoardTypeModal] = useState(false);
  const [showCreateLobbyModal, setShowCreateLobbyModal] = useState(false);
  const [isCreatingLobby, setIsCreatingLobby] = useState(false);
  const [addAiToLobby, setAddAiToLobby] = useState(false);

  const handlePlayVsAI = () => {
    setShowBoardTypeModal(true);
  };

  const handleStartGame = async () => {
    if (isCreating) return;
    setIsCreating(true);

    try {
      // Create a private lobby with AI filling the slots
      const playerCount = selectedBoardType === 'four_player' ? 4 : 2;
      const code = await createLobby(
        {
          isPublic: false,
          speed: 'standard',
          playerCount,
          isRanked: false,
        },
        true // Add AI to fill slots
      );

      const state = useLobbyStore.getState();
      if (state.playerKey) {
        connect(code, state.playerKey);
      }
      navigate(`/lobby/${code}`);
    } catch (error) {
      console.error('Failed to create game:', error);
      alert('Failed to create game. Please try again.');
    } finally {
      setIsCreating(false);
      setShowBoardTypeModal(false);
    }
  };

  const handleBrowseLobbies = () => {
    navigate('/lobbies');
  };

  const handleCreateLobby = () => {
    setShowCreateLobbyModal(true);
  };

  const handleCreateLobbySubmit = useCallback(async () => {
    if (isCreatingLobby) return;
    setIsCreatingLobby(true);

    try {
      const code = await createLobby(
        {
          isPublic: false,
          speed: 'standard',
          playerCount: 2,
          isRanked: false,
        },
        addAiToLobby
      );

      const state = useLobbyStore.getState();
      if (state.playerKey) {
        connect(code, state.playerKey);
      }
      navigate(`/lobby/${code}`);
    } catch (error) {
      console.error('Failed to create lobby:', error);
      alert('Failed to create lobby. Please try again.');
    } finally {
      setIsCreatingLobby(false);
      setShowCreateLobbyModal(false);
      setAddAiToLobby(false);
    }
  }, [createLobby, connect, navigate, addAiToLobby, isCreatingLobby]);

  return (
    <div className="home-page">
      <h1>Kung Fu Chess</h1>
      <p className="tagline">Real-time chess where both players move simultaneously</p>

      <div className="play-options">
        <div className="play-option">
          <h2>Quick Play</h2>
          <p>Jump into a game against an AI opponent</p>
          <button className="btn btn-primary" onClick={handlePlayVsAI} disabled={isCreating}>
            {isCreating ? 'Creating...' : 'Play vs AI'}
          </button>
        </div>

        <div className="play-option">
          <h2>Multiplayer</h2>
          <p>Find an opponent or create a lobby</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button className="btn btn-primary" onClick={handleBrowseLobbies}>
              Browse Lobbies
            </button>
            <button className="btn btn-secondary" onClick={handleCreateLobby}>
              Create Lobby
            </button>
          </div>
        </div>

        <div className="play-option">
          <h2>Campaign</h2>
          <p>Progress through 64 levels and earn belts</p>
          <button className="btn btn-secondary" disabled>Start Campaign</button>
        </div>
      </div>

      {/* Board Type Selection Modal */}
      {showBoardTypeModal && (
        <div className="modal-overlay" onClick={() => setShowBoardTypeModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Select Board Type</h2>
            <div className="board-type-options">
              <label className={`board-type-option ${selectedBoardType === 'standard' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="boardType"
                  value="standard"
                  checked={selectedBoardType === 'standard'}
                  onChange={() => setSelectedBoardType('standard')}
                />
                <div className="board-type-info">
                  <h3>Standard (8x8)</h3>
                  <p>Classic 2-player chess board</p>
                </div>
              </label>
              <label className={`board-type-option ${selectedBoardType === 'four_player' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="boardType"
                  value="four_player"
                  checked={selectedBoardType === 'four_player'}
                  onChange={() => setSelectedBoardType('four_player')}
                />
                <div className="board-type-info">
                  <h3>4-Player (12x12)</h3>
                  <p>Larger board with cut corners</p>
                </div>
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowBoardTypeModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleStartGame} disabled={isCreating}>
                {isCreating ? 'Creating...' : 'Start Game'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Lobby Modal */}
      {showCreateLobbyModal && (
        <div className="modal-overlay" onClick={() => setShowCreateLobbyModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Lobby</h2>
            <div className="board-type-options">
              <label className={`board-type-option ${!addAiToLobby ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="lobbyType"
                  checked={!addAiToLobby}
                  onChange={() => setAddAiToLobby(false)}
                />
                <div className="board-type-info">
                  <h3>Wait for Player</h3>
                  <p>Create a lobby and wait for someone to join</p>
                </div>
              </label>
              <label className={`board-type-option ${addAiToLobby ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="lobbyType"
                  checked={addAiToLobby}
                  onChange={() => setAddAiToLobby(true)}
                />
                <div className="board-type-info">
                  <h3>Play vs AI</h3>
                  <p>Create a lobby with an AI opponent</p>
                </div>
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCreateLobbyModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleCreateLobbySubmit} disabled={isCreatingLobby}>
                {isCreatingLobby ? 'Creating...' : 'Create Lobby'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Home;
