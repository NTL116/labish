import type { Metadata } from "next";
import localFont from "next/font/local";
import SystemStatusBanner from "@/components/SystemStatusBanner";
import "./globals.css";

// Fonts are vendored in src/fonts/ (SIL OFL, see OFL-*.txt) so production
// builds never fetch from Google Fonts — required for offline installs.
const inter = localFont({
  src: "../fonts/Inter-Variable.ttf",
  variable: "--font-inter",
});

const lora = localFont({
  src: [
    { path: "../fonts/Lora-Variable.ttf", style: "normal" },
    { path: "../fonts/Lora-Italic-Variable.ttf", style: "italic" },
  ],
  variable: "--font-lora",
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
