import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kawn Video Generation",
  description: "Create short AI videos for your Kawn community.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gradient-to-b from-kawn-black via-kawn-black to-kawn-charcoal">
        {children}
      </body>
    </html>
  );
}
