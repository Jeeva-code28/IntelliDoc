import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';

function PulsingOrb() {
  const orbRef = useRef();

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    orbRef.current.scale.setScalar(1 + Math.sin(time * 3) * 0.1);
  });

  return (
    <Sphere ref={orbRef} args={[1, 64, 64]} scale={1}>
      <MeshDistortMaterial
        color="#4F46E5"
        attach="material"
        distort={0.4}
        speed={4}
        roughness={0.2}
      />
    </Sphere>
  );
}

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 p-3 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-xl rounded-tl-sm w-fit max-w-[85%]">
      <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0 border border-[var(--color-border-highlight)]">
        <Canvas camera={{ position: [0, 0, 3] }}>
          <ambientLight intensity={0.8} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <PulsingOrb />
        </Canvas>
      </div>
      <div className="text-[12px] text-[var(--color-text-secondary)] italic">
        Processing documents & generating answer...
      </div>
    </div>
  );
}
