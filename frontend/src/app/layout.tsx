import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Doc Agent - 智能文档问答助手",
  description: "上传文档，AI 智能问答",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className="min-h-full flex flex-col bg-zinc-50 text-zinc-900 antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
