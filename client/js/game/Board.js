/**
 * Clutch Chess - Board Renderer
 * Handles 3D board tiles and valid move highlighting
 */

import * as THREE from 'three';

export class Board {
    constructor(scene, options) {
        this.scene = scene;
        this.tileSize = options.tileSize;
        this.scale = options.scale;
        this.offset = options.offset;

        this.tiles = [];
        this.highlights = [];

        // Materials
        this.materials = {
            tileDark: new THREE.MeshStandardMaterial({
                color: 0x111122,
                roughness: 0.8,
                metalness: 0.2
            }),
            tileLight: new THREE.MeshStandardMaterial({
                color: 0x1a1a2e,
                roughness: 0.8,
                metalness: 0.2
            }),
            validMove: new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.3,
                side: THREE.DoubleSide
            }),
            attackMove: new THREE.MeshBasicMaterial({
                color: 0xff0066,
                transparent: true,
                opacity: 0.4,
                side: THREE.DoubleSide
            })
        };
    }

    create() {
        const tileGeo = new THREE.BoxGeometry(
            this.tileSize * this.scale * 0.95,
            0.5,
            this.tileSize * this.scale * 0.95
        );

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const isDark = (row + col) % 2 === 1;
                const tile = new THREE.Mesh(
                    tileGeo,
                    isDark ? this.materials.tileDark : this.materials.tileLight
                );

                tile.position.set(
                    col * this.tileSize * this.scale + this.offset + (this.tileSize * this.scale / 2),
                    -0.25,
                    row * this.tileSize * this.scale + this.offset + (this.tileSize * this.scale / 2)
                );
                tile.receiveShadow = true;

                this.scene.add(tile);
                this.tiles.push(tile);
            }
        }

        // Create board border/frame
        this.createBorder();

        // Pre-create highlight meshes (reusable)
        this.createHighlights();
    }

    createBorder() {
        const borderSize = this.tileSize * this.scale * 8 + 2;
        const borderGeo = new THREE.BoxGeometry(borderSize, 0.8, borderSize);
        const borderMat = new THREE.MeshStandardMaterial({
            color: 0x0a0a1a,
            roughness: 0.9
        });

        const border = new THREE.Mesh(borderGeo, borderMat);
        border.position.y = -0.6;
        border.receiveShadow = true;
        this.scene.add(border);

        // Edge glow lines
        const edgeGeo = new THREE.BoxGeometry(borderSize + 0.2, 0.1, 0.1);
        const edgeMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });

        const edges = [
            { x: 0, z: -borderSize / 2 },
            { x: 0, z: borderSize / 2 },
        ];

        edges.forEach(pos => {
            const edge = new THREE.Mesh(edgeGeo, edgeMat);
            edge.position.set(pos.x, 0, pos.z);
            this.scene.add(edge);
        });

        const edgeGeoSide = new THREE.BoxGeometry(0.1, 0.1, borderSize + 0.2);
        [{ x: -borderSize / 2 }, { x: borderSize / 2 }].forEach(pos => {
            const edge = new THREE.Mesh(edgeGeoSide, edgeMat);
            edge.position.set(pos.x, 0, 0);
            this.scene.add(edge);
        });
    }

    createHighlights() {
        const highlightGeo = new THREE.PlaneGeometry(
            this.tileSize * this.scale * 0.8,
            this.tileSize * this.scale * 0.8
        );

        for (let i = 0; i < 32; i++) {
            const highlight = new THREE.Mesh(highlightGeo, this.materials.validMove.clone());
            highlight.rotation.x = -Math.PI / 2;
            highlight.position.y = 0.1;
            highlight.visible = false;
            this.scene.add(highlight);
            this.highlights.push(highlight);
        }
    }

    showValidMoves(moves) {
        this.hideValidMoves();

        moves.forEach((move, i) => {
            if (i >= this.highlights.length) return;

            const highlight = this.highlights[i];
            highlight.position.set(
                move.col * this.tileSize * this.scale + this.offset + (this.tileSize * this.scale / 2),
                0.1,
                move.row * this.tileSize * this.scale + this.offset + (this.tileSize * this.scale / 2)
            );

            // Use attack color if there's an enemy piece
            if (move.isAttack) {
                highlight.material = this.materials.attackMove;
            } else {
                highlight.material = this.materials.validMove;
            }

            highlight.visible = true;
        });
    }

    hideValidMoves() {
        this.highlights.forEach(h => h.visible = false);
    }

    logicToWorld(lx, ly) {
        return {
            x: lx * this.scale + this.offset,
            z: ly * this.scale + this.offset
        };
    }

    worldToLogic(wx, wz) {
        return {
            x: (wx - this.offset) / this.scale,
            y: (wz - this.offset) / this.scale
        };
    }
}
