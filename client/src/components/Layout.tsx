import { type ReactNode, useState } from "react";
import { Sidebar, type ChatSession } from "./Sidebar";
import { Menu } from "lucide-react";

interface LayoutProps {
    children: ReactNode;
    sessions: ChatSession[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    onDeleteSession: (id: string) => void;
    onRenameSession: (id: string, newTitle: string) => void;
}

export const Layout = ({
    children,
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onDeleteSession,
    onRenameSession,
}: LayoutProps) => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    return (
        <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
            <Sidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
                sessions={sessions}
                currentSessionId={currentSessionId}
                onSelectSession={(id) => {
                    onSelectSession(id);
                    setIsSidebarOpen(false); // Close on selection for mobile
                }}
                onNewChat={() => {
                    onNewChat();
                    setIsSidebarOpen(false);
                }}
                onDeleteSession={onDeleteSession}
                onRenameSession={onRenameSession}
            />

            <main className="flex-1 flex flex-col min-w-0 relative">
                {/* Mobile Header */}
                <div className="md:hidden flex items-center p-4 border-b border-slate-800 bg-slate-900/95 backdrop-blur-xl">
                    <button
                        onClick={() => setIsSidebarOpen(true)}
                        className="p-2 -ml-2 text-slate-400 hover:text-white"
                    >
                        <Menu size={24} />
                    </button>
                    <span className="ml-2 font-bold text-lg bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                        Legal Doc RAG
                    </span>
                </div>

                {children}
            </main>
        </div>
    );
};
