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
    }

    spawnExplosion(position, color = 0xffaa00) {
        const count = 20;

        for (let i = 0; i < count; i++) {
            const material = new THREE.MeshBasicMaterial({
                color: Math.random() > 0.5 ? color : 0xffffff,
                transparent: true,
                opacity: 1
            });

            const mesh = new THREE.Mesh(this.geometry, material);
            mesh.position.copy(position);

            // Random velocity
            const velocity = new THREE.Vector3(
                (Math.random() - 0.5) * 25,
                Math.random() * 25,
                (Math.random() - 0.5) * 25
            );

            this.scene.add(mesh);
            this.particles.push({
                mesh,
                velocity,
                life: 1.0,
                decay: 1.5 + Math.random() * 0.5
            });
        }

        // Spawn a flash
        this.spawnFlash(position, color);
    }

    spawnFlash(position, color) {
        const flashGeo = new THREE.SphereGeometry(3, 8, 8);
        const flashMat = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.8
        });
        const flash = new THREE.Mesh(flashGeo, flashMat);
        flash.position.copy(position);
        flash.position.y += 1;

        this.scene.add(flash);
        this.particles.push({
            mesh: flash,
            velocity: new THREE.Vector3(0, 0, 0),
            life: 0.3,
            decay: 3,
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
