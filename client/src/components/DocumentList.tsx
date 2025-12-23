import { FileText, Trash2, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface DocumentMetadata {
    filename: string;
    size: number;
    uploaded_at: string;
}

interface DocumentListProps {
    sessionId: string | null;
    documents: DocumentMetadata[];
    onDeleteDocument: (filename: string) => void;
    isOpen: boolean;
    onClose: () => void;
    onPreview: (url: string) => void;
}

export const DocumentList = ({ sessionId, documents, onDeleteDocument, isOpen, onClose, onPreview }: DocumentListProps) => {
    const API_BASE_URL = "http://localhost:8000"; // Should come from config

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Mobile Overlay */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                    />

                    <motion.div
                        initial={{ x: "100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "100%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 200 }}
                        className="fixed inset-y-0 right-0 z-50 w-80 bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 shadow-2xl flex flex-col"
                    >
                        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                            <h2 className="font-semibold text-lg text-white">Documents</h2>
                            <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                            {documents.length === 0 ? (
                                <div className="text-center text-slate-500 py-10">
                                    <FileText size={40} className="mx-auto mb-3 opacity-20" />
                                    <p>No documents uploaded.</p>
                                </div>
                            ) : (
                                documents.map((doc) => (
                                    <div
                                        key={doc.filename}
                                        className="group bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-xl p-3 flex items-start gap-3 transition-all"
                                    >
                                        <div className="mt-1 p-2 bg-blue-500/10 rounded-lg">
                                            <FileText size={16} className="text-blue-400" />
                                        </div>
                                        <div className="flex-1 overflow-hidden">
                                            <button
                                                onClick={() => onPreview(`${API_BASE_URL}/chats/${sessionId}/documents/${doc.filename}`)}
                                                className="font-medium text-sm text-slate-200 truncate hover:text-blue-400 hover:underline cursor-pointer block text-left"
                                                title={`Preview ${doc.filename}`}
                                            >
                                                {doc.filename}
                                            </button>
                                            <p className="text-xs text-slate-500 mt-1">
                                                {(doc.size / 1024).toFixed(1)} KB
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => onDeleteDocument(doc.filename)}
                                            className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                                            title="Delete Document"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="p-4 border-t border-slate-800 bg-slate-900/50">
                            <p className="text-xs text-slate-500 text-center">
                                Documents are used as context for AI responses.
                            </p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};
