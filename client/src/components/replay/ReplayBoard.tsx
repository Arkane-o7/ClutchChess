/**
 * ReplayBoard Component
 *
 * Read-only board that renders replay state from the server.
 * Uses PixiJS GameRenderer but doesn't handle any user interaction.
 */

import { useEffect, useRef, useState } from 'react';
import { useReplayStore } from '../../stores/replay';
import { GameRenderer, type BoardType, TIMING } from '../../game';

interface ReplayBoardProps {
  boardType: BoardType;
  squareSize?: number;
}

export function ReplayBoard({ boardType, squareSize = 64 }: ReplayBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<GameRenderer | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Get state from replay store
  const pieces = useReplayStore((s) => s.pieces);
  const activeMoves = useReplayStore((s) => s.activeMoves);
  const cooldowns = useReplayStore((s) => s.cooldowns);
  const currentTick = useReplayStore((s) => s.currentTick);
  const isPlaying = useReplayStore((s) => s.isPlaying);
  const speed = useReplayStore((s) => s.speed);

  // Track last tick time for interpolation
  const lastTickTimeRef = useRef<number>(performance.now());
  const lastTickRef = useRef<number>(currentTick);

  // Update tick tracking when tick changes
  useEffect(() => {
    if (currentTick !== lastTickRef.current) {
      lastTickTimeRef.current = performance.now();
      lastTickRef.current = currentTick;
    }
  }, [currentTick]);

  // Initialize renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new GameRenderer({
      canvas,
      boardType,
      playerNumber: 1, // View from player 1's perspective
      squareSize,
      // No interaction handlers - replay is read-only
      onSquareClick: () => {},
      onPieceClick: () => {},
    });

    renderer
      .init(canvas)
      .then(() => {
        rendererRef.current = renderer;
        setIsReady(true);
      })
      .catch((error) => {
        console.error('Failed to initialize replay renderer:', error);
      });

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      renderer.destroy();
      rendererRef.current = null;
      setIsReady(false);
    };
  }, [boardType, squareSize]);

  // Render loop with visual tick interpolation
  useEffect(() => {
    if (!isReady || !rendererRef.current) return;

    // Get timing constants based on speed
    const ticksPerSquare = speed === 'lightning'
      ? TIMING.LIGHTNING_TICKS_PER_SQUARE
      : TIMING.STANDARD_TICKS_PER_SQUARE;

    const render = () => {
      const renderer = rendererRef.current;
      if (!renderer) return;

      // Calculate visual tick for smooth animation
      // Only interpolate if playing
      let visualTick = currentTick;
      if (isPlaying) {
        const now = performance.now();
        const timeSinceLastTick = now - lastTickTimeRef.current;
        const tickFraction = Math.min(timeSinceLastTick / TIMING.TICK_PERIOD_MS, 1.0);
        visualTick = currentTick + tickFraction;
      }

      // Convert pieces to renderer format
      const rendererPieces = pieces.map((p) => ({
        id: p.id,
        type: p.type,
        player: p.player,
        row: p.row,
        col: p.col,
        captured: p.captured,
        moving: p.moving,
        onCooldown: p.onCooldown,
      }));

      // Convert active moves
      const rendererMoves = activeMoves.map((m) => ({
        pieceId: m.pieceId,
        path: m.path,
        startTick: m.startTick,
      }));

      // Convert cooldowns
      const rendererCooldowns = cooldowns.map((c) => ({
        pieceId: c.pieceId,
        remainingTicks: c.remainingTicks,
      }));

      // Render pieces
      renderer.renderPieces(
        rendererPieces,
        rendererMoves,
        rendererCooldowns,
        visualTick,
        ticksPerSquare
      );

      // No selection highlighting in replay mode
      renderer.highlightSelection(null, [], undefined, undefined);

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isReady, pieces, activeMoves, cooldowns, currentTick, isPlaying, speed]);

  // Calculate canvas dimensions
  const boardDims = boardType === 'four_player' ? { width: 12, height: 12 } : { width: 8, height: 8 };
  const canvasWidth = boardDims.width * squareSize;
  const canvasHeight = boardDims.height * squareSize;

  return (
    <div className="replay-board-container" style={{ width: canvasWidth, height: canvasHeight }}>
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        style={{
          display: 'block',
          width: canvasWidth,
          height: canvasHeight,
        }}
      />
      {!isReady && (
        <div
          className="replay-board-loading"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: canvasWidth,
            height: canvasHeight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            color: 'white',
          }}
        >
          Loading...
        </div>
      )}
    </div>
  );
}
