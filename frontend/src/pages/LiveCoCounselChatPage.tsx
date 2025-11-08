import { LiveCoCounselChat } from '@/components/LiveCoCounselChat';
import { Avatar } from '@/components/Avatar';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useRef } from 'react';

export default function LiveCoCounselChatPage() {
  const avatarRef = useRef<{ speak: (text: string) => void }>(null);

  return (
    <div className="bg-background-canvas text-text-primary h-screen relative">
      <div className="absolute inset-0 bg-black/20 [mask-image:radial-gradient(ellipse_at_center,transparent_20%,black)]" />
      <PanelGroup direction="horizontal">
        <Panel>
          <Avatar ref={avatarRef} />
        </Panel>
        <PanelResizeHandle className="w-2 bg-border hover:bg-accent-cyan-500/50 transition-colors duration-medium" />
        <Panel>
          <div className="p-4 h-full">
            <LiveCoCounselChat speak={(text) => avatarRef.current?.speak(text)} />
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
}
