"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, FileText } from "lucide-react";
import { API_BASE_URL } from "@/lib/config";

interface Source {
  content: string;
  source: string;
  page?: number | null;
  document_id?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

interface Props {
  documentIds: string[];
  onAddDoc: () => void;
}

function parseSSE(data: string): { sources?: Source[]; token?: string; done?: string } {
  try {
    const lines = data.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6);
        if (payload === "[DONE]") return { done: "" };
        const parsed = JSON.parse(payload);
        return parsed;
      }
    }
  } catch {}
  return { token: data };
}

async function* iterSSE(response: Response): AsyncGenerator<{ event: string; data: string }> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        yield { event: eventType, data: line.slice(6) };
        eventType = "";
      }
    }
  }
}

export default function ChatInterface({ documentIds, onAddDoc }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingDocId, setStreamingDocId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading || documentIds.length === 0) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: documentIds, message: userMsg.content, history }),
      });

      if (!res.ok) throw new Error("Stream request failed");

      let assistantContent = "";
      let assistantSources: Source[] = [];

      for await (const event of iterSSE(res)) {
        if (event.event === "sources") {
          assistantSources = JSON.parse(event.data);
        } else if (event.event === "token") {
          assistantContent += event.data;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              last.content = assistantContent;
            } else {
              next.push({ role: "assistant", content: assistantContent });
            }
            return [...next];
          });
        } else if (event.event === "done") {
          assistantContent = event.data;
        }
      }

      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          last.content = assistantContent;
          last.sources = assistantSources;
        } else {
          next.push({ role: "assistant", content: assistantContent, sources: assistantSources });
        }
        return [...next];
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "抱歉，请求失败，请重试。" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (documentIds.length === 0) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center text-zinc-400 gap-4 px-4">
        <FileText className="size-12 opacity-50" />
        <p className="text-lg">请先上传文档</p>
        <button onClick={onAddDoc} className="rounded-xl bg-zinc-900 px-6 py-3 text-sm font-medium text-white hover:bg-zinc-800">
          去上传
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 h-full">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-zinc-400 mt-20">
            <FileText className="size-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">已选 {documentIds.length} 个文档，开始提问吧</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-zinc-900 text-white"
                  : "bg-white border border-zinc-200 text-zinc-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.sources && msg.sources.length > 0 && msg.sources[0]?.source && (
                <details className="mt-2 text-xs text-zinc-400">
                  <summary className="cursor-pointer hover:text-zinc-600">
                    来源 ({msg.sources.length})
                  </summary>
                  <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                    {msg.sources.map((s, j) => (
                      <div key={j} className="p-2 bg-zinc-50 rounded-lg">
                        <p className="text-zinc-500 mb-1">
                          {s.source.split("/").pop()}
                          {s.page ? ` (第${s.page}页)` : ""}
                          {s.document_id ? ` [${s.document_id.slice(0, 6)}]` : ""}
                        </p>
                        <p className="text-zinc-400 line-clamp-2">{s.content}</p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-zinc-200 px-4 py-4 bg-white">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题..."
            disabled={loading}
            className="flex-1 rounded-xl border border-zinc-200 px-4 py-2.5 text-sm outline-none focus:border-zinc-400 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading || documentIds.length === 0}
            className="rounded-xl bg-zinc-900 px-4 py-2.5 text-white hover:bg-zinc-800 disabled:opacity-40 flex items-center gap-1"
          >
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
