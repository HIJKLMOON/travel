"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { API_BASE_URL } from "@/lib/config";

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface UploadResult {
  document_id: string;
  filename: string;
  chunks: number;
}

export default function FileUploader({ onSuccess }: { onSuccess: (result: UploadResult) => void }) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = useCallback(async (uploadFile: File) => {
    setFile(uploadFile);
    setStatus("uploading");
    setMessage("");

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await res.json();
      setStatus("success");
      setMessage(`成功！${data.chunks} 个文本块已索引`);
      onSuccess(data);
    } catch (e: unknown) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Upload failed");
    }
  }, [onSuccess]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleUpload(f);
  }, [handleUpload]);

  const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleUpload(f);
  }, [handleUpload]);

  const reset = useCallback(() => {
    setStatus("idle");
    setMessage("");
    setFile(null);
  }, []);

  const acceptedTypes = ".pdf,.txt,.md";

  return (
    <div className="w-full max-w-md mx-auto">
      {status === "idle" && (
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`flex flex-col items-center gap-4 p-10 border-2 border-dashed rounded-2xl cursor-pointer transition-colors
            ${dragOver ? "border-blue-500 bg-blue-50" : "border-zinc-200 hover:border-zinc-400"}`}
        >
          <Upload className="size-10 text-zinc-400" />
          <div className="text-center">
            <p className="text-sm font-medium">点击上传或拖拽文件到此</p>
            <p className="text-xs text-zinc-400 mt-1">支持 PDF、TXT、Markdown</p>
          </div>
          <input type="file" accept={acceptedTypes} onChange={onFileSelect} className="hidden" />
        </label>
      )}

      {status === "uploading" && (
        <div className="flex flex-col items-center gap-4 p-10 border-2 border-blue-200 rounded-2xl bg-blue-50">
          <Loader2 className="size-8 text-blue-600 animate-spin" />
          <p className="text-sm text-zinc-600">正在上传并索引文档...</p>
        </div>
      )}

      {status === "success" && (
        <div className="flex flex-col items-center gap-4 p-8 border-2 border-green-200 rounded-2xl bg-green-50">
          <CheckCircle className="size-10 text-green-600" />
          <div className="text-center">
            <p className="font-medium text-green-800">上传成功</p>
            <p className="text-sm text-green-600 mt-1">{message}</p>
          </div>
          <button onClick={reset} className="text-xs text-zinc-500 underline mt-2">
            上传另一个文档
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="flex flex-col items-center gap-4 p-8 border-2 border-red-200 rounded-2xl bg-red-50">
          <XCircle className="size-10 text-red-600" />
          <div className="text-center">
            <p className="font-medium text-red-800">上传失败</p>
            <p className="text-sm text-red-600 mt-1">{message}</p>
          </div>
          <button onClick={reset} className="text-xs text-zinc-500 underline mt-2">
            重试
          </button>
        </div>
      )}
    </div>
  );
}
