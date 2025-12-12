// Simple Web Audio API wrapper for UI sounds
// This avoids the need for external asset files

const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();

const playTone = (freq: number, type: OscillatorType, duration: number, vol: number = 0.1) => {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

    gain.gain.setValueAtTime(vol, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + duration);
};

export const playSound = {
    hover: () => playTone(400, 'sine', 0.05, 0.02),
    click: () => playTone(600, 'sine', 0.1, 0.05),
    success: () => {
        playTone(800, 'sine', 0.1, 0.05);
        setTimeout(() => playTone(1200, 'sine', 0.2, 0.05), 100);
    },
    error: () => {
        playTone(300, 'sawtooth', 0.1, 0.05);
        setTimeout(() => playTone(200, 'sawtooth', 0.2, 0.05), 100);
    },
    notification: () => {
        playTone(1000, 'sine', 0.1, 0.03);
        setTimeout(() => playTone(1500, 'sine', 0.3, 0.03), 100);
    }
};
