/**
 * Clutch Chess - Game Engine
 * Main game loop, state management, and 3D scene orchestration
 */

import * as THREE from 'three';
import { EventEmitter } from '../utils/EventEmitter.js';
import { Board } from './Board.js';
import { PieceFactory } from './Piece.js';
import { MoveValidator } from './MoveValidator.js';
import { CollisionSystem } from './CollisionSystem.js';
import { ParticleSystem } from './ParticleSystem.js';
import { AIController } from './AIController.js';
import { GAME_CONFIG, PIECE_TYPES } from '../../../shared/constants.js';

export class GameEngine extends EventEmitter {
    constructor(container) {
        super();

        this.container = container;
        this.isRunning = false;
        this.isPlaying = false;
        this.vsAI = false;
        this.playerColor = 'white';

        // Game state
        this.pieces = [];
        this.whiteMana = GAME_CONFIG.MANA_START;
        this.blackMana = GAME_CONFIG.MANA_START;
        this.selectedPiece = null;
        this.validMoves = [];
        this.gameTime = 0;
        this.captures = { white: 0, black: 0 };

        // Three.js components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        // Game systems
        this.board = null;
        this.pieceFactory = null;
        this.moveValidator = null;
        this.collisionSystem = null;
        this.particleSystem = null;
        this.ai = null;

        // Camera animation
        this.cameraMode = 'menu'; // 'menu' | 'game'
        this.menuAngle = 0;

        // Clock for delta time
        this.clock = new THREE.Clock();
        this.lastTime = 0;

        this.init();
    }

    init() {
        this.setupScene();
        this.setupLights();
        this.setupCamera();
        this.setupRenderer();
        this.setupSystems();
        this.setupEventListeners();

        // Load models then create initial board
        this.pieceFactory.loadModels().then(() => {
            this.board.create();
            this.setupInitialPieces();
            console.log('✅ Game Engine Ready');
        });
    }

    setupScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a1a);
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.008);
    }

    setupLights() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambient);

        // Main directional light
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(20, 50, 20);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 1024;
        dirLight.shadow.mapSize.height = 1024;
        dirLight.shadow.camera.near = 1;
        dirLight.shadow.camera.far = 100;
        dirLight.shadow.camera.left = -40;
        dirLight.shadow.camera.right = 40;
        dirLight.shadow.camera.top = 40;
        dirLight.shadow.camera.bottom = -40;
        this.scene.add(dirLight);

        // Cyan rim light
        const cyanLight = new THREE.PointLight(0x00f0ff, 1, 100);
        cyanLight.position.set(-30, 20, -30);
        this.scene.add(cyanLight);

        // Magenta rim light
        const magentaLight = new THREE.PointLight(0xff0066, 1, 100);
        magentaLight.position.set(30, 20, 30);
        this.scene.add(magentaLight);
    }

    setupCamera() {
        this.camera = new THREE.PerspectiveCamera(
            45,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        // Initial menu position
        this.camera.position.set(60, 40, 60);
        this.camera.lookAt(0, 0, 0);
    }

    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.container.appendChild(this.renderer.domElement);
    }

    setupSystems() {
        const scale = 0.1;
        const boardOffset = -(GAME_CONFIG.LOGIC_SIZE * scale) / 2;

        this.board = new Board(this.scene, {
            tileSize: GAME_CONFIG.TILE_SIZE,
            scale: scale,
            offset: boardOffset
        });

        this.pieceFactory = new PieceFactory(scale);
        this.moveValidator = new MoveValidator(GAME_CONFIG);
        this.collisionSystem = new CollisionSystem(GAME_CONFIG);
        this.particleSystem = new ParticleSystem(this.scene);
        this.ai = new AIController(this.moveValidator, GAME_CONFIG);

        // Click plane for move detection
        const planeGeo = new THREE.PlaneGeometry(
            GAME_CONFIG.LOGIC_SIZE * scale,
            GAME_CONFIG.LOGIC_SIZE * scale
        );
        this.clickPlane = new THREE.Mesh(
            planeGeo,
            new THREE.MeshBasicMaterial({ visible: false })
        );
        this.clickPlane.rotation.x = -Math.PI / 2;
        this.scene.add(this.clickPlane);
    }

    setupInitialPieces() {
        const layout = [
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        ];

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const char = layout[row][col];
                if (char) {
                    const isWhite = char === char.toUpperCase();
                    // Match Server ID generation: type-row-col
                    const id = `${char.toLowerCase()}-${row}-${col}`;
                    const piece = this.createPiece(char.toLowerCase(), isWhite, col, row, id);
                    this.pieces.push(piece);
                }
            }
        }
    }

    createPiece(type, isWhite, col, row, id) {
        const x = col * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;
        const y = row * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;

        const piece = {
            id: id || crypto.randomUUID(),
            type,
            isWhite,
            x,
            y,
            col,
            row,
            targetX: null,
            targetY: null,
            startX: null,
            startY: null,
            hasMoved: false,
            isMoving: false,
            isAirborne: false,
            mesh: this.pieceFactory.create(type, isWhite)
        };

        const worldPos = this.board.logicToWorld(x, y);
        piece.mesh.position.set(worldPos.x, 0, worldPos.z);
        if (!isWhite) piece.mesh.rotation.y = Math.PI;

        this.scene.add(piece.mesh);
        return piece;
    }

    setupEventListeners() {
        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousedown', (e) => this.onMouseDown(e));
    }

    onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    onMouseDown(event) {
        if (!this.isPlaying) return;

        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);

        if (!this.selectedPiece) {
            this.trySelectPiece();
        } else {
            this.tryMovePiece();
        }
    }

    trySelectPiece() {
        const playerPieces = this.pieces.filter(p =>
            p.isWhite === (this.playerColor === 'white') && !p.isMoving
        );
        const meshes = playerPieces.map(p => p.mesh);
        const intersects = this.raycaster.intersectObjects(meshes, true);

        if (intersects.length > 0) {
            // Find which piece was clicked
            let hitObject = intersects[0].object;
            while (hitObject.parent && !meshes.includes(hitObject)) {
                hitObject = hitObject.parent;
            }

            const piece = playerPieces.find(p => p.mesh === hitObject);
            if (piece) {
                this.selectPiece(piece);
            }
        }
    }

    selectPiece(piece) {
        // Deselect previous
        if (this.selectedPiece) {
            this.pieceFactory.setSelected(this.selectedPiece.mesh, false, this.selectedPiece.isWhite);
        }

        this.selectedPiece = piece;
        this.validMoves = this.moveValidator.getValidMoves(piece, this.pieces);

        // Highlight selected piece
        this.pieceFactory.setSelected(piece.mesh, true, piece.isWhite);

        // Show valid move indicators
        this.board.showValidMoves(this.validMoves);
    }

    deselectPiece() {
        if (this.selectedPiece) {
            this.pieceFactory.setSelected(this.selectedPiece.mesh, false, this.selectedPiece.isWhite);
            this.selectedPiece = null;
            this.validMoves = [];
            this.board.hideValidMoves();
        }
    }

    tryMovePiece() {
        const intersects = this.raycaster.intersectObject(this.clickPlane);
        if (intersects.length === 0) {
            this.deselectPiece();
            return;
        }

        const point = intersects[0].point;
        const logicPos = this.board.worldToLogic(point.x, point.z);
        const col = Math.floor(logicPos.x / GAME_CONFIG.TILE_SIZE);
        const row = Math.floor(logicPos.y / GAME_CONFIG.TILE_SIZE);

        const validMove = this.validMoves.find(m => m.col === col && m.row === row);

        // Check mana
        const mana = this.playerColor === 'white' ? this.whiteMana : this.blackMana;

        if (validMove && mana >= GAME_CONFIG.MANA_COST_PER_MOVE) {
            this.movePiece(this.selectedPiece, validMove);
            this.deselectPiece();
        } else {
            this.deselectPiece();
        }
    }

    movePiece(piece, target) {
        // Deduct mana
        if (piece.isWhite) {
            this.whiteMana -= GAME_CONFIG.MANA_COST_PER_MOVE;
        } else {
            this.blackMana -= GAME_CONFIG.MANA_COST_PER_MOVE;
        }

        // Set up movement
        piece.startX = piece.x;
        piece.startY = piece.y;
        piece.targetX = target.col * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;
        piece.targetY = target.row * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;
        piece.isMoving = true;
        piece.hasMoved = true;
        piece.isAirborne = piece.type === 'n';

        // Emit for network sync
        this.emit('movePiece', {
            pieceId: piece.id,
            from: { col: piece.col, row: piece.row },
            to: target
        });
    }

    applyOpponentMove(data) {
        const piece = this.pieces.find(p => p.id === data.pieceId);
        if (piece) {
            this.movePiece(piece, data.to);
        }
    }

    // --- Game State ---

    startGame(options) {
        this.vsAI = options.vsAI || false;
        this.playerColor = options.playerColor || 'white';

        // Reset state
        this.reset();

        // Set up pieces
        this.setupInitialPieces();

        // Switch to game camera
        this.cameraMode = 'game';

        // Start game loop
        this.isPlaying = true;
        this.gameTime = 0;
        this.captures = { white: 0, black: 0 };
    }

    reset() {
        // Clear pieces
        this.pieces.forEach(p => this.scene.remove(p.mesh));
        this.pieces = [];

        // Reset mana
        this.whiteMana = GAME_CONFIG.MANA_START;
        this.blackMana = GAME_CONFIG.MANA_START;

        // Reset selection
        this.deselectPiece();

        // Clear particles
        this.particleSystem.clear();

        // Reset AI
        if (this.ai) this.ai.reset();

        this.isPlaying = false;
    }

    // --- Update Loop ---

    startRenderLoop() {
        this.isRunning = true;
        this.animate();
    }

    animate() {
        if (!this.isRunning) return;
        requestAnimationFrame(() => this.animate());

        const dt = this.clock.getDelta();

        this.updateCamera(dt);

        if (this.isPlaying) {
            this.updateGame(dt);
        }

        this.particleSystem.update(dt);
        this.renderer.render(this.scene, this.camera);
    }

    updateCamera(dt) {
        if (this.cameraMode === 'menu') {
            // Orbit around board
            this.menuAngle += dt * 0.1;
            const dist = 70;
            this.camera.position.x = Math.sin(this.menuAngle) * dist;
            this.camera.position.z = Math.cos(this.menuAngle) * dist;
            this.camera.position.y = 50;
            this.camera.lookAt(0, 0, 0);
        } else {
            // Lerp to game position based on color
            // White: (0, 75, 50), Black: (0, 75, -50)
            const zPos = this.playerColor === 'white' ? 50 : -50;
            const targetPos = new THREE.Vector3(0, 75, zPos);

            this.camera.position.lerp(targetPos, dt * 2);
            this.camera.lookAt(0, 0, 0);
        }
    }

    updateGame(dt) {
        this.gameTime += dt;

        // A. Economy Update
        // Max cap check
        this.whiteMana = Math.min(
            GAME_CONFIG.MANA_MAX,
            this.whiteMana + GAME_CONFIG.MANA_REGEN_PER_SECOND * dt
        );
        this.blackMana = Math.min(
            GAME_CONFIG.MANA_MAX,
            this.blackMana + GAME_CONFIG.MANA_REGEN_PER_SECOND * dt
        );

        // Emit mana update for UI
        this.emit('manaUpdate', {
            white: this.whiteMana / GAME_CONFIG.MANA_MAX,
            black: this.blackMana / GAME_CONFIG.MANA_MAX
        });

        // B. Movement Physics
        this.updatePieceMovements(dt);

        // C. Collision Detection (Combat)
        this.checkCollisions();

        // AI moves
        if (this.vsAI) {
            this.updateAI(dt);
        }
    }

    updatePieceMovements(dt) {
        this.pieces.forEach(piece => {
            if (!piece.isMoving) {
                // Smooth rotation reset
                piece.mesh.rotation.z *= 0.9;
                piece.mesh.rotation.x *= 0.9;
                if (!piece.isWhite) piece.mesh.rotation.y = Math.PI;
                return;
            }

            const dx = piece.targetX - piece.x;
            const dy = piece.targetY - piece.y;
            const dist = Math.hypot(dx, dy);

            // Velocity Determination
            let speed = GAME_CONFIG.MOVE_SPEED;
            if (piece.type === 'p') {
                const startCol = Math.round(piece.startX / GAME_CONFIG.TILE_SIZE);
                const targetCol = Math.floor(piece.targetX / GAME_CONFIG.TILE_SIZE);

                // "Turbo Charge" - Attack moves (diagonal) are Double Speed
                // Note: startX is where the move STARTED for the piece, not the start of the game.
                // We need to ensure piece.startX is set correctly when move starts.
                if (startCol !== targetCol) {
                    speed = GAME_CONFIG.PAWN_ATTACK_SPEED;
                }
            }

            const step = speed * dt;

            if (dist <= step) {
                // Arrived
                piece.x = piece.targetX;
                piece.y = piece.targetY;
                piece.col = Math.floor(piece.x / GAME_CONFIG.TILE_SIZE);
                piece.row = Math.floor(piece.y / GAME_CONFIG.TILE_SIZE);
                piece.isMoving = false;
                piece.isAirborne = false;
            } else {
                // Move towards target
                piece.x += (dx / dist) * step;
                piece.y += (dy / dist) * step;
            }

            // Update mesh position
            const worldPos = this.board.logicToWorld(piece.x, piece.y);
            piece.mesh.position.x = worldPos.x;
            piece.mesh.position.z = worldPos.z;

            // Jump arc for knights - "Aerial Ace"
            if (piece.isAirborne) {
                const totalDist = Math.hypot(
                    piece.targetX - piece.startX,
                    piece.targetY - piece.startY
                );
                const currentDist = Math.hypot(
                    piece.x - piece.startX,
                    piece.y - piece.startY
                );

                // Parabolic arc
                if (totalDist > 0) {
                    const progress = currentDist / totalDist;
                    // Inverted parabolic: 4 * p * (1-p) maps 0->0, 0.5->1, 1->0
                    piece.mesh.position.y = GAME_CONFIG.KNIGHT_JUMP_HEIGHT * 4 * progress * (1 - progress);
                }
            } else {
                piece.mesh.position.y = 0;
            }

            // Tilt effect
            if (!piece.isAirborne) {
                piece.mesh.rotation.z = (dx / dist) * 0.2;
                piece.mesh.rotation.x = -(dy / dist) * 0.2;
            } else {
                piece.mesh.rotation.x += dt * 5;
            }
        });
    }

    checkCollisions() {
        const result = this.collisionSystem.check(this.pieces);

        // Handle Destroyed
        result.destroyed.forEach(piece => {
            this.particleSystem.spawnExplosion(piece.mesh.position.clone());

            if (piece.isWhite) this.captures.black++;
            else this.captures.white++;

            this.scene.remove(piece.mesh);
        });

        this.pieces = this.pieces.filter(p => !result.destroyed.includes(p));

        // Note: 'stopped' is unused in new spec, collisions result in destruction or ignore.

        // D. Win Condition
        const whiteKing = this.pieces.find(p => p.type === 'k' && p.isWhite);
        const blackKing = this.pieces.find(p => p.type === 'k' && !p.isWhite);

        if (!whiteKing || !blackKing) {
            this.isPlaying = false;
            this.emit('gameOver', {
                winner: !whiteKing ? 'black' : 'white',
                duration: Math.floor(this.gameTime),
                captures: `White: ${this.captures.white}, Black: ${this.captures.black}`
            });
        }
    }

    updateAI(dt) {
        const aiColor = this.playerColor === 'white' ? 'black' : 'white';
        const mana = aiColor === 'white' ? this.whiteMana : this.blackMana;

        const move = this.ai.getMove(this.pieces, aiColor, mana, dt);
        if (move) {
            this.movePiece(move.piece, move.target);
        }
    }
}
