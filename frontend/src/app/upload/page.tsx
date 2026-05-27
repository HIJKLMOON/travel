"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import FileUploader from "@/components/FileUploader";
import Link from "next/link";

interface UploadResult {
  document_id: string;
  filename: string;
  chunks: number;
}

export default function UploadPage() {
  const router = useRouter();
  const [result, setResult] = useState<UploadResult | null>(null);

  return (
    <div className="flex flex-col flex-1 items-center px-6 py-12">
      <div className="w-full max-w-lg">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-800 mb-8">
          <ArrowLeft className="size-4" />
          返回首页
        </Link>

        <h1 className="text-2xl font-bold mb-2">上传文档</h1>
        <p className="text-sm text-zinc-500 mb-8">上传 PDF、TXT 或 Markdown 文件，AI 将自动索引文档内容</p>

        <FileUploader onSuccess={(r) => setResult(r)} />

        {result && (
          <div className="mt-6 text-center">
            <button
              onClick={() => router.push(`/chat?doc=${result.document_id}`)}
              className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              开始提问
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
