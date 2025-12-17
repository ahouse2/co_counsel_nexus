import React, { useEffect, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

interface Avatar3DProps {
    url: string;
    isSpeaking: boolean;
    analyser: AnalyserNode | null;
}

export const Avatar3D: React.FC<Avatar3DProps> = ({ url, isSpeaking, analyser }) => {
    const { scene } = useGLTF(url);
    const group = useRef<THREE.Group>(null);
    const dataArrayRef = useRef<Uint8Array | null>(null);

    // Blink state
    const [nextBlink, setNextBlink] = useState(Date.now() + 3000);
    const [isBlinking, setIsBlinking] = useState(false);

    // Setup Data Array
    useEffect(() => {
        if (analyser) {
            dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
        }
    }, [analyser]);

    // Animation Loop
    useFrame((state) => {
        if (!group.current) return;

        const time = state.clock.getElapsedTime();

        // 1. Head Sway (Idle Animation)
        group.current.rotation.y = Math.sin(time * 0.5) * 0.05;
        group.current.rotation.x = Math.sin(time * 0.3) * 0.02;

        // 2. Blinking Logic
        const now = Date.now();
        if (now > nextBlink) {
            setIsBlinking(true);
            setNextBlink(now + 2000 + Math.random() * 4000);
            setTimeout(() => setIsBlinking(false), 150);
        }

        // 3. Lip Sync & Facial Expression
        scene.traverse((child) => {
            if ((child as THREE.Mesh).isMesh && (child as THREE.Mesh).morphTargetDictionary) {
                const mesh = child as THREE.Mesh;
                const dict = mesh.morphTargetDictionary!;
                const influences = mesh.morphTargetInfluences!;

                // Reset mouth
                influences[dict['viseme_aa']] = 0;
                influences[dict['viseme_E']] = 0;
                influences[dict['viseme_O']] = 0;
                influences[dict['mouthOpen']] = 0;

                // Apply Blink
                const blinkIdx = dict['eyesClosed'];
                if (blinkIdx !== undefined) {
                    influences[blinkIdx] = THREE.MathUtils.lerp(influences[blinkIdx], isBlinking ? 1 : 0, 0.4);
                }

                // Apply Lip Sync if speaking
                if (isSpeaking && analyser && dataArrayRef.current) {
                    analyser.getByteFrequencyData(dataArrayRef.current as Uint8Array<ArrayBuffer>);

                    // Calculate average volume (energy)
                    let sum = 0;
                    for (let i = 0; i < dataArrayRef.current.length; i++) {
                        sum += dataArrayRef.current[i];
                    }
                    const average = sum / dataArrayRef.current.length;
                    const energy = Math.min(average / 50, 1.0); // Normalize 0-1

                    // Simple mapping: Energy drives mouth opening
                    // Advanced: Map frequency bands to vowels (Low -> O, Mid -> A, High -> E)

                    if (energy > 0.1) {
                        influences[dict['viseme_aa']] = energy * 0.8;
                        influences[dict['viseme_E']] = energy * 0.2;
                        influences[dict['mouthOpen']] = energy * 0.5;

                        // Add some randomness for realism
                        influences[dict['viseme_O']] = Math.sin(time * 10) * 0.2 * energy;
                    }
                }
            }
        });
    });

    return (
        <group ref={group} dispose={null} position={[0, -1.5, 0]}>
            <primitive object={scene} scale={1.8} />
            {/* Lighting for Realism */}
            <ambientLight intensity={0.7} />
            <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color="blue" />
        </group>
    );
};
