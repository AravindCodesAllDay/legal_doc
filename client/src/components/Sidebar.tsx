import { MessageSquare, Plus, Trash2, X, Edit2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils/cn";
import { format } from "date-fns";
import { useState, useRef, useEffect } from "react";

export interface ChatSession {
    id: string; // Using string to match backend uuid
    title: string;
    updated_at: string;
}

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    sessions: ChatSession[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    onDeleteSession: (id: string) => void;
    onRenameSession: (id: string, newTitle: string) => void;
}

export const Sidebar = ({
    isOpen,
    onClose,
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onDeleteSession,
    onRenameSession,
}: SidebarProps) => {
    const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const editInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (editingSessionId && editInputRef.current) {
            editInputRef.current.focus();
        }
    }, [editingSessionId]);

    const startEditing = (session: ChatSession, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingSessionId(session.id);
        setEditTitle(session.title);
    };

    const submitRename = () => {
        if (editingSessionId) {
            if (editTitle.trim()) {
                onRenameSession(editingSessionId, editTitle.trim());
            }
            setEditingSessionId(null);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            submitRename();
        } else if (e.key === "Escape") {
            setEditingSessionId(null);
        }
    };

    return (
        <>
            {/* Mobile Overlay */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar Container */}
            <motion.aside
                className={cn(
                    "fixed md:static inset-y-0 left-0 z-50 w-72 bg-slate-900/95 backdrop-blur-xl border-r border-slate-800 flex flex-col transition-transform duration-300 ease-in-out",
                    isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
                )}
            >
                {/* Header */}
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                        Legal Doc RAG
                    </h1>
                    <button onClick={onClose} className="md:hidden text-slate-400">
                        <X size={20} />
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-4">
                    <button
                        onClick={onNewChat}
                        className="w-full flex items-center gap-3 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all shadow-lg shadow-blue-600/20 group"
                    >
                        <Plus size={20} className="group-hover:rotate-90 transition-transform" />
                        <span className="font-medium">New Chat</span>
                    </button>
                </div>

                {/* Sessions List */}
                <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 custom-scrollbar">
                    {sessions.map((session) => (
                        <div
                            key={session.id}
                            className="group relative flex items-center"
                        >
                            <div
                                onClick={() => onSelectSession(session.id)}
                                className={cn(
                                    "w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-colors cursor-pointer",
                                    currentSessionId === session.id
                                        ? "bg-slate-800 text-white"
                                        : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                                )}
                            >
                                <MessageSquare size={18} className="shrink-0" />

                                {editingSessionId === session.id ? (
                                    <input
                                        ref={editInputRef}
                                        value={editTitle}
                                        onChange={(e) => setEditTitle(e.target.value)}
                                        onBlur={() => submitRename()}
                                        onKeyDown={handleKeyDown}
                                        onClick={(e) => e.stopPropagation()}
                                        className="flex-1 bg-slate-950 border border-blue-500 rounded px-1 py-0.5 text-sm text-white focus:outline-none"
                                    />
                                ) : (
                                    <div className="flex-1 min-w-0 pr-12">
                                        <p className="truncate font-medium text-sm">{session.title}</p>
                                        <p className="text-xs text-slate-500 mt-0.5">
                                            {format(new Date(session.updated_at || new Date()), "MMM d, h:mm a")}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Actions Group (Edit + Delete) */}
                            {editingSessionId !== session.id && (
                                <div className="absolute right-2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800/80 rounded-md backdrop-blur-sm">
                                    <button
                                        onClick={(e) => startEditing(session, e)}
                                        className="p-1.5 text-slate-400 hover:text-blue-400 transition-colors"
                                        title="Rename"
                                    >
                                        <Edit2 size={14} />
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onDeleteSession(session.id);
                                        }}
                                        className="p-1.5 text-slate-400 hover:text-red-400 transition-colors"
                                        title="Delete Chat"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}

                    {sessions.length === 0 && (
                        <div className="text-center text-slate-500 py-10 px-4">
                            <p>No chat history.</p>
                            <p className="text-sm mt-2">Start a new conversation!</p>
                        </div>
                    )}
                </div>

                {/* User / Settings Footer (Optional) */}
                <div className="p-4 border-t border-slate-800">
                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500" />
                        <span>User Account</span>
                    </div>
                </div>
            </motion.aside>
        </>
    );
};
