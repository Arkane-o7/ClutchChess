/**
 * Clutch Chess - Particle System
 * Explosion effects when pieces are captured
 */

import * as THREE from 'three';

export class ParticleSystem {
    constructor(scene) {
        this.scene = scene;
        this.particles = [];

        // Particle geometry (reusable)
        this.geometry = new THREE.BoxGeometry(0.4, 0.4, 0.4);

        // Pre-create flash geometry (reusable)
        this.flashGeometry = new THREE.SphereGeometry(3, 6, 6); // Lower poly

        // Pre-create particle materials (reusable, cloned per particle for opacity)
        this.baseMaterials = {
            white: new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true }),
            cyan: new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true }),
            magenta: new THREE.MeshBasicMaterial({ color: 0xff0066, transparent: true }),
            orange: new THREE.MeshBasicMaterial({ color: 0xffaa00, transparent: true })
        };
    }

    spawnExplosion(position, color = 0xffaa00) {
        const count = 12; // Reduced from 20 for performance

        for (let i = 0; i < count; i++) {
            // Clone a base material instead of creating new
            const materialKey = Math.random() > 0.5 ? 'orange' : 'white';
            const material = this.baseMaterials[materialKey].clone();
            material.opacity = 1;

            const mesh = new THREE.Mesh(this.geometry, material);
            mesh.position.copy(position);

            // Random velocity
            const velocity = new THREE.Vector3(
                (Math.random() - 0.5) * 20, // Slightly reduced
                Math.random() * 20,
                (Math.random() - 0.5) * 20
            );

            this.scene.add(mesh);
            this.particles.push({
                mesh,
                velocity,
                life: 1.0,
                decay: 2.0 + Math.random() * 0.5 // Faster decay
            });
        }

        // Spawn a flash
        this.spawnFlash(position, color);
    }

    spawnFlash(position, color) {
        const flashMat = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.8
        });
        const flash = new THREE.Mesh(this.flashGeometry, flashMat);
        flash.position.copy(position);
        flash.position.y += 1;

        this.scene.add(flash);
        this.particles.push({
            mesh: flash,
            velocity: new THREE.Vector3(0, 0, 0),
            life: 0.2, // Shorter flash
            decay: 5,
            isFlash: true
        });
    }

    update(dt) {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];

            // Decrease life
            p.life -= dt * p.decay;

            if (p.life <= 0) {
                this.scene.remove(p.mesh);
                if (p.mesh.geometry !== this.geometry) {
                    p.mesh.geometry.dispose();
                }
                p.mesh.material.dispose();
                this.particles.splice(i, 1);
                continue;
            }

            if (p.isFlash) {
                // Flash expands and fades
                p.mesh.scale.setScalar(1 + (1 - p.life) * 3);
                p.mesh.material.opacity = p.life;
            } else {
                // Apply gravity
                p.velocity.y -= 50 * dt;

                // Move
                p.mesh.position.addScaledVector(p.velocity, dt);

                // Spin
                p.mesh.rotation.x += dt * 10;
                p.mesh.rotation.y += dt * 8;

                // Fade
                p.mesh.material.opacity = p.life;

                // Scale down
                const scale = 0.5 + p.life * 0.5;
                p.mesh.scale.setScalar(scale);
            }
        }
    }

    clear() {
        this.particles.forEach(p => {
            this.scene.remove(p.mesh);
            if (p.mesh.geometry !== this.geometry) {
                p.mesh.geometry.dispose();
            }
            p.mesh.material.dispose();
        });
        this.particles = [];
    }
}
