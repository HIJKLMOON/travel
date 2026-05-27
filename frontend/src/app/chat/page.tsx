"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, X, Check, Loader2 } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";
import { API_BASE_URL } from "@/lib/config";

interface DocInfo {
  document_id: string;
  filename: string;
  chunks: number;
  created_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/documents`);
      const data = await res.json();
      setDocs(data);
      if (data.length > 0 && selectedIds.length === 0) {
        setSelectedIds([data[0].document_id]);
      }
    } catch {
      console.error("Failed to fetch docs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const toggleDoc = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleAddDoc = () => {
    router.push("/upload");
  };

  return (
    <div className="flex flex-1 h-screen">
      <aside className="w-64 border-r border-zinc-200 bg-white flex flex-col">
        <div className="p-4 border-b border-zinc-100">
          <Link href="/" className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-800 mb-3">
            <ArrowLeft className="size-4" />
            首页
          </Link>
          <h2 className="text-sm font-medium text-zinc-800">选择文档</h2>
          <p className="text-xs text-zinc-400 mt-0.5">选中后即可对话</p>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-5 text-zinc-300 animate-spin" />
            </div>
          ) : docs.length === 0 ? (
            <div className="text-center py-8 text-zinc-400 text-sm">
              暂无文档
            </div>
          ) : (
            docs.map((doc) => (
              <button
                key={doc.document_id}
                onClick={() => toggleDoc(doc.document_id)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors flex items-center gap-2 ${
                  selectedIds.includes(doc.document_id)
                    ? "bg-zinc-100 text-zinc-900"
                    : "text-zinc-600 hover:bg-zinc-50"
                }`}
              >
                <div className={`size-4 rounded border flex items-center justify-center ${
                  selectedIds.includes(doc.document_id)
                    ? "bg-zinc-900 border-zinc-900"
                    : "border-zinc-300"
                }`}>
                  {selectedIds.includes(doc.document_id) && (
                    <Check className="size-3 text-white" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-xs font-medium">{doc.filename}</p>
                  <p className="text-[10px] text-zinc-400">{doc.chunks} 块</p>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="p-3 border-t border-zinc-100">
          <button
            onClick={handleAddDoc}
            className="w-full flex items-center justify-center gap-1.5 rounded-xl border border-dashed border-zinc-300 py-2 text-xs text-zinc-500 hover:bg-zinc-50"
          >
            <Plus className="size-3.5" />
            上传新文档
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <ChatInterface documentIds={selectedIds} onAddDoc={handleAddDoc} />
      </main>
    </div>
  );
}
