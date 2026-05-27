import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center px-6">
      <main className="flex flex-col items-center gap-8 text-center max-w-xl">
        <div className="size-16 rounded-2xl bg-blue-600 flex items-center justify-center">
          <span className="text-2xl text-white font-bold">D</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight">Doc Agent</h1>
        <p className="text-lg text-zinc-500">
          上传你的文档，通过 AI 智能问答快速获取信息
        </p>
        <div className="flex gap-4 mt-4">
          <Link
            href="/upload"
            className="rounded-xl bg-zinc-900 px-6 py-3 text-sm font-medium text-white hover:bg-zinc-800 transition-colors"
          >
            上传文档
          </Link>
          <Link
            href="/chat"
            className="rounded-xl border border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 transition-colors"
          >
            开始对话
          </Link>
        </div>
      </main>
    </div>
  );
}
