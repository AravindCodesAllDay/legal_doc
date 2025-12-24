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
  const { id: urlSessionId } = useParams<{ id: string }>();
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
        console.log(data);
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
        setSessions((prev) => prev.filter((s) => s._id !== sessionId));
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
          prev.map((s) => (s._id === sessionId ? { ...s, title: newTitle } : s))
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
          // Navigate to the new session
          navigate(`/chat/${targetSessionId}`, { replace: true });

          // Wait a bit for navigation to complete before sending message
          await new Promise((resolve) => setTimeout(resolve, 100));
        } else {
          return;
        }
      } catch (e) {
        console.error("Error creating session", e);
        return;
      }
    }

    // Optimistic Update - Add user message
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

      // Add assistant message placeholder
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
              // Ignore parse errors
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
    // 1. Determine the ID: Use existing URL ID or "new" for a new session
    const targetSessionId = urlSessionId || "new";
    const isNewSession = !urlSessionId;

    const fileArray = Array.from(files);

    try {
      setIsUploading(true);
      setUploadProgress(`Uploading ${fileArray.length} file(s)...`);

      // Create FormData with ALL files at once
      const formData = new FormData();
      fileArray.forEach((file) => {
        formData.append("files", file);
      });

      // Single upload request with all files
      const res = await fetch(
        `${API_BASE_URL}/chats/${targetSessionId}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (res.ok) {
        const result = await res.json();

        // Log the result for debugging
        console.log("Upload result:", result);

        // Get the actual session ID assigned by the server
        const actualSessionId = result.session_id;

        // Show summary with better messaging
        if (result.skipped_count > 0 || result.failed_count > 0) {
          let message = "";
          if (result.uploaded_count > 0) {
            message += `${result.uploaded_count} file(s) uploaded successfully. `;
          }
          if (result.skipped_count > 0) {
            const skippedFiles = result.skipped_files
              .map((f: any) => f.filename)
              .join(", ");
            message += `Skipped (already exist): ${skippedFiles}. `;
          }
          if (result.failed_count > 0) {
            const failedFiles = result.failed_files
              .map((f: any) => f.filename)
              .join(", ");
            message += `Failed: ${failedFiles}`;
          }
          alert(message.trim());
        }

        // Update State & Navigate (even if some were skipped)
        const totalProcessed = result.uploaded_count + result.skipped_count;
        if (totalProcessed > 0) {
          if (isNewSession) {
            // Fetch the newly created session data using the actual ID from server
            const sessionRes = await fetch(
              `${API_BASE_URL}/chats/${actualSessionId}`
            );
            if (sessionRes.ok) {
              const sessionData = await sessionRes.json();
              // Add to sidebar
              setSessions((prev) => [sessionData, ...prev]);
              // Navigate to the new session
              navigate(`/chat/${actualSessionId}`, { replace: true });

              // Wait for navigation, then set state
              await new Promise((resolve) => setTimeout(resolve, 100));
              setMessages(sessionData.messages || []);
              setDocuments(sessionData.documents || []);
              setIsDocListOpen(true); // Auto-open doc list
            }
          } else {
            // Refresh the current session data
            await fetchSessionData(actualSessionId);
            await fetchSessions(); // Update sidebar timestamp
            setIsDocListOpen(true); // Auto-open doc list
          }
        } else {
          alert("No files were uploaded successfully.");
        }
      } else {
        const errorText = await res.text();
        console.error("Upload failed:", errorText);
        alert("Failed to upload files. Please try again.");
      }
    } catch (error) {
      console.error("Upload process error", error);
      alert("Error uploading files. Please check your connection.");
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
                  className="px-2 hover:bg-slate-800 rounded-full transition-colors"
                >
                  <span className="text-2xl font-bold leading-none">
                    &times;
                  </span>
                </button>
              </div>
              <div className="flex-1 bg-slate-800 relative">
                <iframe
                  src={`${previewDocUrl}#toolbar=0`}
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
