/**
 * Clutch Chess - Piece Factory
 * Creates 3D chess piece meshes with materials
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

export class PieceFactory {
    constructor(scale) {
        this.scale = scale;
        this.loader = new GLTFLoader();
        this.templates = {}; // Stores loaded GLTF scenes

        // Materials
        this.materials = {
            white: new THREE.MeshStandardMaterial({
                color: 0x00f0ff,
                emissive: 0x00f0ff,
                emissiveIntensity: 0.4,
                roughness: 0.2,
                metalness: 0.5
            }),
            black: new THREE.MeshStandardMaterial({
                color: 0xff0066,
                emissive: 0xff0066,
                emissiveIntensity: 0.4,
                roughness: 0.2,
                metalness: 0.5
            }),
            selected: new THREE.MeshStandardMaterial({
                color: 0xffffff,
                emissive: 0xffffff,
                emissiveIntensity: 0.8,
                roughness: 0.1,
                metalness: 0.8
            })
        };
    }

    async loadModels() {
        const models = {
            'p': 'pawn.glb',
            'r': 'rook.glb',
            'n': 'knight.glb',
            'b': 'bishop.glb',
            'q': 'queen.glb',
            'k': 'king.glb'
        };

        const promises = Object.entries(models).map(([type, file]) => {
            return new Promise((resolve, reject) => {
                this.loader.load(`/models/${file}`, (gltf) => {
                    const model = gltf.scene;

                    // Normalize model
                    model.traverse((child) => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                        }
                    });

                    this.templates[type] = model;
                    resolve();
                }, undefined, (error) => {
                    console.error(`Failed to load model ${file}:`, error);
                    // Start empty if fail, or maybe reject?
                    // We'll just log and continue, aiming to fallback or empty group
                    resolve();
                });
            });
        });

        await Promise.all(promises);
        console.log('✅ All 3D models loaded');
    }

    create(type, isWhite) {
        const material = isWhite ? this.materials.white : this.materials.black;
        const group = new THREE.Group();

        if (this.templates[type]) {
            // Clone the template
            const model = this.templates[type].clone();

            // Apply materials
            model.traverse((child) => {
                if (child.isMesh) {
                    child.material = material;
                }
            });

            // Adjust scale/position
            model.scale.set(1.5, 1.5, 1.5);

            // Fix rotation for Knights if needed
            // if (type === 'n') model.rotation.y = Math.PI / 2;

            group.add(model);
        } else {
            // Fallback geometry
            const geo = new THREE.BoxGeometry(2, 4, 2);
            const mesh = new THREE.Mesh(geo, material);
            mesh.position.y = 2;
            group.add(mesh);
        }

        // Add glow light
        const color = isWhite ? 0x00f0ff : 0xff0066;
        const light = new THREE.PointLight(color, 0.8, 15);
        light.position.y = 2;
        group.add(light);

        return group;
    }

    setSelected(mesh, selected, isWhite) {
        if (selected) {
            mesh.traverse(child => {
                if (child.isMesh && child.material) {
                    // Store original if not already stored (handles re-selection safely)
                    if (!child.userData.originalMaterial) {
                        child.userData.originalMaterial = child.material;
                    }
                    child.material = this.materials.selected;
                }
            });
        } else {
            // Revert
            mesh.traverse(child => {
                if (child.isMesh) {
                    // Restore original
                    if (child.userData.originalMaterial) {
                        child.material = child.userData.originalMaterial;
                        delete child.userData.originalMaterial;
                    } else {
                        // Fallback just in case
                        child.material = isWhite ? this.materials.white : this.materials.black;
                    }
                }
            });
        }
    }
}
