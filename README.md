# Hyper Chess - Real-Time Battle Chess

![Hyper Chess Gameplay](./client/public/gameplay_header.png)

**Hyper Chess** abandons the turn-based structure of classical chess for a chaotic, real-time battlefield. Commands are issued in real-time, gated only by your **Mana**, and combat is determined by **physics-based collisions**.

---

## 🎮 The Core Rules

### 1. No Turns, Just Time
*   **Real-Time Action**: You do not wait for your opponent. If you have Mana, you move.
*   **Simultaneous Command**: Multiple pieces can move at once.
*   **The Clock**: The game only stops when a King dies.

### 2. The Mana System
*   **Starting Mana**: 4
*   **Cost**: 1 Mana per move.
*   **Regen**: Recharges slowly. Spamming moves leaves you defenseless!

### 3. Combat & Physics
*   **The Ram**: Moving vs Stationary = Stationary destroyed.
*   **The Crash**: Moving vs Moving = **BOTH DESTROYED**.
*   **FRIENDLY FIRE IS ON**: Collisions do not check sides. You can destroy your own pieces to clear a path (The "ICBM Gambit").

### 4. Special Mechanics
*   **♟️ Pawn (The Missile)**: 
    *   **Turbo Charge**: Moving diagonally (attack vector) creates a speed boost (2x Speed).
*   **♞ Knight (The Jumper)**:
    *   **Aerial Ace**: Knights fly over the board. They are invincible while airborne and only interact upon landing.
*   **Sliders (Rook, Bishop, Queen)**:
    *   Vulnerable to interception. A pawn can step in front of a sliding Queen to destroy both ("The Interceptor").

## 🛠️ Tech Stack
*   **Three.js**: 3D Rendering & Animation
*   **Node.js/Socket.io**: Real-time multiplayer synchronization
*   **Vanilla JS**: Custom Game Engine & Physics

## 🚀 Getting Started

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Run Development Server**:
    ```bash
    npm run dev
    ```

3.  **Open in Browser**:
    Navigate to `http://localhost:5173`.

---

*Built with ❤️ by Arkane*
