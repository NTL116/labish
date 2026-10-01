export type NewsCategory =
  | "Deal"
  | "Partnership"
  | "Portfolio Update"
  | "Corporate";

export interface NewsArticle {
  id: string;
  title: string;
  slug: string;
  date: string;
  category: NewsCategory;
  summary: string;
  author: string;
  image: string;
  imageAlt: string;
  content: NewsContentBlock[];
}

export type NewsContentBlock =
  | { type: "paragraph"; text: string }
  | { type: "heading"; text: string }
  | { type: "quote"; text: string; attribution?: string }
  | { type: "image"; src: string; alt: string; caption?: string };

export interface NewsArticleLink {
  label: string;
  href: string;
}

export interface TeamMember {
  id: string;
  name: string;
  slug: string;
  title: string;
  image: string;
  bio: string;
  specialties: string[];
}

export interface NavLink {
  label: string;
  href: string;
}

export interface NavGroup {
  label: string;
  links: NavLink[];
}