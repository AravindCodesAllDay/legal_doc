import { Bot, User } from "lucide-react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { cn } from "../utils/cn";
import { useRef, useEffect } from "react";

export interface Message {
    role: "user" | "assistant" | "system";
    content: string;
}

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
}

export const ChatArea = ({ messages, isLoading }: ChatAreaProps) => {
    const endRef = useRef<HTMLDivElement>(null);
    // Show thinking dots if loading AND (no messages OR last message is not assistant OR last assistant msg is empty)
    const shouldShowThinkingDots = isLoading && (!messages.length || messages[messages.length - 1].role !== "assistant" || messages[messages.length - 1].content === "");

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar">
            {messages.length === 0 && !isLoading && (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 opacity-50">
                    <Bot size={64} className="mb-4" />
                    <p className="text-lg font-medium">Start a conversation</p>
                </div>
            )}

            {messages.map((msg, idx) => {
                if (msg.role === "system") {
                    return (
                        <div key={idx} className="text-center text-xs text-slate-500 italic max-w-4xl mx-auto my-2 opacity-70">
                            {msg.content}
                        </div>
                    );
                }

                return (
                    <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn(
                            "flex gap-4 max-w-4xl mx-auto",
                            msg.role === "user" ? "flex-row-reverse" : ""
                        )}
                    >
                        <div
                            className={cn(
                                "w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-lg",
                                msg.role === "assistant"
                                    ? "bg-gradient-to-br from-blue-500 to-cyan-500"
                                    : "bg-slate-700"
                            )}
                        >
                            {msg.role === "assistant" ? (
                                <Bot size={20} className="text-white" />
                            ) : (
                                <User size={20} className="text-slate-200" />
                            )}
                        </div>

                        <div
                            className={cn(
                                "group relative p-4 rounded-2xl shadow-sm max-w-[80%]",
                                msg.role === "assistant"
                                    ? "bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 text-slate-200 rounded-tl-none"
                                    : "bg-blue-600/90 text-white rounded-tr-none"
                            )}
                        >
                            <div className="prose prose-invert prose-sm max-w-none break-words">
                                <ReactMarkdown
                                    components={{
                                        code({ node, inline, className, children, ...props }: any) {
                                            const match = /language-(\w+)/.exec(className || '')
                                            return !inline && match ? (
                                                <div className="relative">
                                                    <div className="absolute top-0 right-0 px-2 py-1 text-xs text-slate-400 bg-slate-800 rounded-bl">
                                                        {match[1]}
                                                    </div>
                                                    <code className={className} {...props}>
                                                        {children}
                                                    </code>
                                                </div>
                                            ) : (
                                                <code className={className} {...props}>
                                                    {children}
                                                </code>
                                            )
                                        }
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </motion.div>
                );
            })}

            {/* Thinking / Loading Indicator */}
            {shouldShowThinkingDots && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex gap-4 max-w-4xl mx-auto"
                >
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shrink-0">
                        <Bot size={20} className="text-white" />
                    </div>
                    <div className="bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0s" }} />
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }} />
                    </div>
                </motion.div>
            )}

            <div ref={endRef} />
        </div>
    );
};
