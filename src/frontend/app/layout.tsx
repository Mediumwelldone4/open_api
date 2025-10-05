import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Open Data Insight Platform",
  description: "Connect public data APIs, analyze responses, and visualize insights.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
