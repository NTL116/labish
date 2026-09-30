"use client";

import { useState } from 'react';
import Link from 'next/link';

export default function Navbar() {
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle('dark');
  };

  const menu = [
    { name: 'Home', path: '/' },
    {
      name: 'Companies',
      children: [
        { name: 'Blue Hat Cleaning', path: '/companies/blue-hat-cleaning' },
        { name: 'May Birch', path: '/companies/may-birch' },
        { name: 'Slate Micro', path: '/companies/slate-micro' }
      ]
    },
    { name: 'News & Updates', path: '/news' },
    {
      name: 'Responsibility',
      children: [
        { name: 'Responsible Vision', path: '/responsibility/responsible-vision' },
        { name: 'Giving Back', path: '/responsibility/giving-back' }
      ]
    },
    {
      name: 'Creative Showcase',
      children: [
        { name: 'Photography', path: '/creative/photography' },
        { name: 'Fine Art', path: '/creative/art' }
      ]
    },
    { name: 'People', path: '/people' },
    { name: 'Contact', path: '/contact' }
  ];

  return (
    <nav className="w-full relative z-50 border-b border-swiss-slate/10 px-8 py-5 flex items-center justify-between select-none">
      {/* Brand Identity / Swiss Grid Axis Point */}
      <Link href="/" className="font-sans font-bold text-lg tracking-normal uppercase">
        Labish
      </Link>

      {/* Navigation Matrix */}
      <div className="hidden items-center space-x-8 xl:flex">
        {menu.map((item) => (
          <div
            key={item.name}
            className="relative"
            onMouseEnter={() => item.children && setActiveDropdown(item.name)}
            onMouseLeave={() => setActiveDropdown(null)}
          >
            {item.children ? (
              <button className="font-sans text-[13px] font-medium tracking-wide uppercase opacity-80 hover:opacity-100 transition-opacity flex items-center cursor-pointer">
                {item.name} <span className="ml-1 text-[9px] opacity-50">↓</span>
              </button>
            ) : (
              <Link href={item.path!} className="font-sans text-[13px] font-medium tracking-wide uppercase opacity-80 hover:opacity-100 transition-opacity">
                {item.name}
              </Link>
            )}

            {/* Glassmorphic Dropdown Container */}
            {item.children && activeDropdown === item.name && (
              <div className="absolute top-full left-0 mt-2 w-56 bg-swiss-glass dark:bg-swiss-glass-dark backdrop-blur-md rounded-macos shadow-xl border border-swiss-slate/20 p-2 space-y-1 animate-glass font-sans">
                {item.children.map((child) => (
                  <Link
                    key={child.name}
                    href={child.path}
                    className="block px-4 py-2 text-[12px] uppercase tracking-wider font-medium font-sans text-swiss-ink dark:text-swiss-cream rounded-md hover:bg-swiss-slate/10 transition-colors"
                  >
                    {child.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Action Suite / Theme Controls */}
      <div className="hidden items-center space-x-4 xl:flex">
        {/* Tactile Skewed Toggle Button */}
        <button
          type="button"
          aria-label="Toggle color theme"
          onClick={toggleDarkMode}
          className="min-w-16 rounded-macos border border-swiss-slate/20 px-3 py-2 text-[10px] font-sans font-medium uppercase tracking-[0.16em] hover:bg-swiss-slate/10 transition-colors cursor-pointer"
        >
          <span className="dark:hidden">Dark</span>
          <span className="hidden dark:inline">Light</span>
        </button>

        <Link href="/login" className="px-5 py-2 text-[12px] font-sans font-medium tracking-widest uppercase border border-swiss-ink dark:border-swiss-cream rounded-macos hover:bg-swiss-ink hover:text-swiss-cream dark:hover:bg-swiss-cream dark:hover:text-swiss-ink transition-all">
          Login
        </Link>
      </div>

      <div className="flex items-center gap-3 xl:hidden">
        <button
          type="button"
          aria-label="Toggle color theme"
          onClick={toggleDarkMode}
          className="min-w-16 rounded-macos border border-swiss-slate/20 px-3 py-2 text-[10px] font-sans font-medium uppercase tracking-[0.16em] hover:bg-swiss-slate/10 transition-colors cursor-pointer"
        >
          <span className="dark:hidden">Dark</span>
          <span className="hidden dark:inline">Light</span>
        </button>
        <button
          type="button"
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-site-menu"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="rounded-macos border border-swiss-slate/20 px-3 py-2 text-[10px] font-sans font-medium uppercase tracking-[0.16em]"
        >
          {mobileMenuOpen ? "Close" : "Menu"}
        </button>
      </div>

      {mobileMenuOpen && (
        <div
          id="mobile-site-menu"
          className="absolute inset-x-0 top-full border-b border-swiss-slate/20 bg-swiss-cream px-6 py-5 shadow-xl dark:bg-swiss-ink xl:hidden"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            {menu.map((item) => (
              <div key={item.name}>
                {item.path ? (
                  <Link
                    href={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className="font-sans text-xs font-medium uppercase tracking-[0.14em]"
                  >
                    {item.name}
                  </Link>
                ) : (
                  <>
                    <p className="font-sans text-xs font-medium uppercase tracking-[0.14em] text-swiss-slate">
                      {item.name}
                    </p>
                    <div className="mt-3 grid gap-3">
                      {item.children?.map((child) => (
                        <Link
                          key={child.path}
                          href={child.path}
                          onClick={() => setMobileMenuOpen(false)}
                          className="font-sans text-xs uppercase tracking-[0.1em]"
                        >
                          {child.name}
                        </Link>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ))}
            <Link
              href="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="font-sans text-xs font-medium uppercase tracking-[0.14em]"
            >
              Login
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
