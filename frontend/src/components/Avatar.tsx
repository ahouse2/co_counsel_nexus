import { Avatar as VisageAvatar, useVisage } from "@readyplayerme/visage";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { WaWaLipsync } from "wawa-lipsync";

const modelSrc = "https://models.readyplayer.me/65805362d72a7a816405eca3.glb";

export const Avatar = forwardRef((props, ref) => {
  const { visage } = useVisage();
  const [lipsync, setLipsync] = useState<WaWaLipsync | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (visage.head) {
      const newLipsync = new WaWaLipsync(visage.head);
      setLipsync(newLipsync);
    }
  }, [visage.head]);

  const speak = async (text: string) => {
    const audio = audioRef.current;

    if (audio) {
      const response = await fetch(
        "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "xi-api-key": process.env.REACT_APP_ELEVENLABS_API_KEY || "",
          },
          body: JSON.stringify({
            text,
            voice_settings: {
              stability: 0,
              similarity_boost: 0,
            },
          }),
        }
      );

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      audio.src = audioUrl;
      audio.play();

      if (lipsync) {
        lipsync.start(audio);
      }

      audio.onended = () => {
        if (lipsync) {
          lipsync.stop();
        }
      };
    }
  };

  useImperativeHandle(ref, () => ({
    speak,
  }));

  return (
    <div className="h-full w-full bg-transparent">
      <VisageAvatar modelSrc={modelSrc} />
      <audio ref={audioRef} hidden />
    </div>
  );
});