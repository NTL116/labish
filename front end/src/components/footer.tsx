import Link from "next/link";

const footerLinks = [
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Terms of Use", href: "/terms" },
];

export default function Footer() {
  return (
    <footer className="sheet-footer flex flex-wrap items-center justify-between gap-3 font-sans text-[9px] uppercase tracking-[0.12em] text-swiss-slate">
      <span>Labish</span>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        {footerLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="transition-colors hover:text-swiss-ink"
          >
            {link.label}
          </Link>
        ))}
        <span>© {new Date().getFullYear()}</span>
      </div>
    </footer>
  );
}