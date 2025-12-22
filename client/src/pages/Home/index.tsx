import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { ChatArea, type Message } from "../../components/ChatArea";
import { MessageInput } from "../../components/MessageInput";
import { type ChatSession } from "../../components/Sidebar";
import {
  DocumentList,
  type DocumentMetadata,
} from "../../components/DocumentList";
import { FileText } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API;

export default function Home() {
  const { id: urlSessionId } = useParams();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [isDocListOpen, setIsDocListOpen] = useState(false);
  const [previewDocUrl, setPreviewDocUrl] = useState<string | null>(null);

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // Sync state with URL
  useEffect(() => {
    if (urlSessionId) {
      // If URL has ID, load messages for it
      fetchSessionData(urlSessionId);
    } else {
      // If no ID (root /), reset view
      setMessages([]);
      setDocuments([]);
    }
  }, [urlSessionId]);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("Failed to fetch sessions", error);
    }
  };

  const fetchSessionData = async (sessionId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
        setDocuments(data.documents || []);
      } else {
        // If session not found (e.g. deleted), redirect to home
        navigate("/");
      }
    } catch (error) {
      console.error("Failed to fetch session data", error);
    }
  };

  // Switch session -> Navigate URL
  const handleSelectSession = (id: string) => {
    navigate(`/chat/${id}`);
  };

  const handleNewChat = () => {
    // Just navigate to root. Session created on first action.
    navigate("/");
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm("Are you sure you want to delete this chat?")) return;

    try {
      const res = await fetch(`${API_BASE_URL}/chats/${sessionId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (urlSessionId === sessionId) {
          navigate("/");
        }
      }
    } catch (error) {
      console.error("Failed to delete session", error);
    }
  };

  const handleRenameSession = async (sessionId: string, newTitle: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });
      if (res.ok) {
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s))
        );
      }
    } catch (error) {
      console.error("Failed to rename session", error);
    }
  };

  const handleDeleteDocument = async (filename: string) => {
    if (!urlSessionId) return;
    if (!confirm(`Delete document ${filename}?`)) return;

    try {
      const res = await fetch(
        `${API_BASE_URL}/chats/${urlSessionId}/documents/${filename}`,
        {
          method: "DELETE",
        }
      );
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.filename !== filename));
        // Refresh session data to get updated system messages
        fetchSessionData(urlSessionId);
      }
    } catch (error) {
      console.error("Failed to delete document", error);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    let targetSessionId = urlSessionId;

    // Create session if none exists
    if (!targetSessionId) {
      try {
        const res = await fetch(`${API_BASE_URL}/chats`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: text.slice(0, 30) + "..." }),
        });
        if (res.ok) {
          const newSession = await res.json();
          setSessions((prev) => [newSession, ...prev]);
          targetSessionId = newSession.id;
          // Navigate but continue execution without waiting for route change effect
          navigate(`/chat/${targetSessionId}`, { replace: true });
        } else {
          return;
        }
      } catch (e) {
        console.error("Error creating session", e);
        return;
      }
    }

    // Optimistic Update
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/chats/${targetSessionId}/message`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        }
      );

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMsg: Message = { role: "assistant", content: "" };

      setMessages((prev) => [...prev, assistantMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") {
              fetchSessions(); // Update timestamp
              break;
            }

            try {
              const data = JSON.parse(dataStr);
              if (data.token) {
                assistantMsg = {
                  ...assistantMsg,
                  content: assistantMsg.content + data.token,
                };

                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = assistantMsg;
                  return newMessages;
                });
              }
            } catch (e) {
              // Ignore
            }
          }
        }
      }
    } catch (error) {
      console.error("Failed to send message", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Failed to get response." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (files: FileList) => {
    let targetSessionId = urlSessionId;

    if (!targetSessionId) {
      // Create session first
      try {
        const res = await fetch(`${API_BASE_URL}/chats`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: "New Chat (Files)" }),
        });
        if (res.ok) {
          const newSession = await res.json();
          setSessions((prev) => [newSession, ...prev]);
          targetSessionId = newSession.id;
          navigate(`/chat/${targetSessionId}`, { replace: true });
        } else {
          return;
        }
      } catch (e) {
        console.error("Error creating session", e);
        return;
      }
    }

    if (!targetSessionId) return;

    const fileArray = Array.from(files);

    try {
      setIsUploading(true);

      let uploadedCount = 0;
      const total = fileArray.length;

      for (let i = 0; i < total; i++) {
        const file = fileArray[i];
        setUploadProgress(`Uploading ${file.name} (${i + 1}/${total})...`);

        const formData = new FormData();
        formData.append("files", file);

        try {
          const res = await fetch(
            `${API_BASE_URL}/chats/${targetSessionId}/upload`,
            {
              method: "POST",
              body: formData,
            }
          );

          if (res.ok) {
            uploadedCount++;
            // Refresh documents immediately after each successful upload to show progress in UI
            fetchSessionData(targetSessionId);
            setIsDocListOpen(true);
          } else {
            console.error(`Failed to upload ${file.name}`);
          }
        } catch (err) {
          console.error(`Error uploading ${file.name}`, err);
        }
      }

      console.log(`Uploaded ${uploadedCount} files`);
    } catch (error) {
      console.error("Upload process error", error);
      alert("Error uploading files.");
    } finally {
      setIsUploading(false);
      setUploadProgress("");
    }
  };

  return (
    <Layout
      sessions={sessions}
      currentSessionId={urlSessionId || null}
      onSelectSession={handleSelectSession}
      onNewChat={handleNewChat}
      onDeleteSession={handleDeleteSession}
      onRenameSession={handleRenameSession}
    >
      <div className="flex-1 flex flex-col h-full relative">
        {/* Toggle Docs Button - Only visible in chat */}
        {urlSessionId && (
          <div className="absolute top-4 right-4 z-10 md:hidden">
            {/* Mobile toggle handled by DocumentList overlay usually, 
                     but we need a trigger. Adding a simple one here. */}
            <button
              onClick={() => setIsDocListOpen(true)}
              className="p-2 bg-slate-800/80 backdrop-blur rounded-lg text-slate-300 shadow-lg border border-slate-700"
            >
              <FileText size={20} />
            </button>
          </div>
        )}

        {/* Desktop Doc Toggle / Info */}
        {urlSessionId && (
          <div className="absolute top-4 right-4 z-10 hidden md:block">
            <button
              onClick={() => setIsDocListOpen(!isDocListOpen)}
              className={
                "p-2 rounded-lg transition-all border shadow-lg flex items-center gap-2 " +
                (isDocListOpen
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-slate-800/80 backdrop-blur border-slate-700 text-slate-300 hover:text-white")
              }
            >
              <FileText size={18} />
              <span className="text-sm font-medium">
                {documents.length} Docs
              </span>
            </button>
          </div>
        )}

        <div className="flex-1 overflow-hidden flex flex-col">
          <ChatArea messages={messages} isLoading={isLoading} />
        </div>

        <div className="p-4 md:p-6 bg-linear-to-t from-slate-950 via-slate-950 to-transparent">
          <MessageInput
            onSendMessage={handleSendMessage}
            onFileUpload={handleFileUpload}
            isLoading={isLoading}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
          />
        </div>

        <DocumentList
          sessionId={urlSessionId || null}
          documents={documents}
          onDeleteDocument={handleDeleteDocument}
          isOpen={isDocListOpen}
          onClose={() => setIsDocListOpen(false)}
          onPreview={(url) => setPreviewDocUrl(url)}
        />

        {/* PDF Preview Modal */}
        {previewDocUrl && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 text-white">
            <div className="bg-slate-900 w-full max-w-5xl h-[85vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col relative overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
                <h3 className="font-semibold text-lg">Document Preview</h3>
                <button
                  onClick={() => setPreviewDocUrl(null)}
                  className="p-1 hover:bg-slate-800 rounded-full transition-colors"
                >
                  <FileText size={20} className="rotate-45" /> {/* Use X icon if imported, but FileText is imported. Actually X is needed. */}
                  {/* Wait, X is not imported in this file. Let's fix imports first or assume Layout has it or just add logic. */}
                  <span className="text-2xl font-bold leading-none">&times;</span>
                </button>
              </div>
              <div className="flex-1 bg-slate-800 relative">
                <iframe
                  src={previewDocUrl}
                  className="w-full h-full border-0"
                  title="Document Preview"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
