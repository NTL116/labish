import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import SystemStatusBanner from "@/components/SystemStatusBanner";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Labish",
  description: "A privately held portfolio of businesses and creative ventures.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${lora.variable} antialiased`}>
      <body>
        <SystemStatusBanner />
        {children}
      </body>
    </html>
  );
}
