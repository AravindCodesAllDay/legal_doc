import { Paperclip, Send } from "lucide-react";
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type FormEvent } from "react";
import { motion } from "framer-motion";
import { cn } from "../utils/cn";

interface MessageInputProps {
    onSendMessage: (message: string) => void;
    onFileUpload: (files: FileList) => void;
    isLoading: boolean;
    isUploading: boolean;
    uploadProgress?: string;
}

export const MessageInput = ({ onSendMessage, onFileUpload, isLoading, isUploading, uploadProgress }: MessageInputProps) => {
    const [message, setMessage] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
        setMessage(e.target.value);
        // Auto-resize
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleSubmit = (e?: FormEvent) => {
        e?.preventDefault();
        if (message.trim() && !isLoading) {
            onSendMessage(message);
            setMessage("");
            if (textareaRef.current) {
                textareaRef.current.style.height = "auto";
            }
        }
    };

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            onFileUpload(e.target.files);
        }
        // Reset input
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    return (
        <div className="relative w-full max-w-4xl mx-auto">
            <div className="relative flex items-end gap-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-2 shadow-2xl">
                {/* Upload Button or Progress */}
                {isUploading ? (
                    <div className="flex items-center gap-2 p-3">
                        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        {uploadProgress && <span className="text-xs text-blue-400 whitespace-nowrap hidden md:block">{uploadProgress}</span>}
                    </div>
                ) : (
                    <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => fileInputRef.current?.click()}
                        className="p-3 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-xl transition-all disabled:opacity-50 group"
                        title="Upload Documents"
                    >
                        <Paperclip size={20} className="group-hover:-rotate-45 transition-transform" />
                    </button>
                )}

                <input
                    type="file"
                    multiple
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                    accept=".pdf,.txt,.docx"
                />

                <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything about your documents..."
                    rows={1}
                    className="w-full bg-transparent text-white placeholder-slate-400 text-base p-3 focus:outline-none resize-none max-h-48 scrollbar-hide"
                    disabled={isLoading}
                />

                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleSubmit()}
                    disabled={!message.trim() || isLoading}
                    className={cn(
                        "p-3 rounded-xl transition-all duration-200",
                        message.trim() && !isLoading
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                            : "bg-slate-700/50 text-slate-500 cursor-not-allowed"
                    )}
                >
                    <Send size={20} />
                </motion.button>
            </div>
        </div>
    );
};
