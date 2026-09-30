import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { loginAction } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="grid grid-cols-1 items-center gap-8 sm:grid-cols-12">
          <div className="space-y-6 sm:col-span-7">
            <h1 className="font-serif text-4xl font-light">Login</h1>
            {error ? (
              <p
                role="alert"
                className="max-w-sm font-sans text-[10px] font-medium uppercase tracking-[0.14em] text-red-700"
              >
                Invalid email or password. Please try again.
              </p>
            ) : null}
            <form action={loginAction} className="max-w-sm space-y-5 pt-2">
              <label className="block font-sans text-[9px] font-medium uppercase tracking-[0.14em] text-swiss-slate">
                Email
                <input
                  name="email"
                  type="email"
                  required
                  autoComplete="username"
                  className="mt-2 block w-full border-0 border-b border-swiss-slate/30 bg-transparent px-0 py-3 text-sm normal-case tracking-normal text-swiss-ink outline-none transition-colors placeholder:text-swiss-slate/70 focus:border-swiss-ink"
                />
              </label>
              <label className="block font-sans text-[9px] font-medium uppercase tracking-[0.14em] text-swiss-slate">
                Password
                <input
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  className="mt-2 block w-full border-0 border-b border-swiss-slate/30 bg-transparent px-0 py-3 text-sm normal-case tracking-normal text-swiss-ink outline-none transition-colors focus:border-swiss-ink"
                />
              </label>
              <button
                type="submit"
                className="inline-flex min-h-10 items-center rounded-[6px] bg-swiss-ink px-5 font-sans text-[10px] font-medium uppercase tracking-[0.15em] text-swiss-cream transition-opacity hover:opacity-75"
              >
                Sign In
              </button>
            </form>
          </div>
          <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-5">
            <Image
              src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=85"
              alt="Modern office architecture rising toward the sky"
              fill
              priority
              sizes="(max-width: 640px) 100vw, 30vw"
              className="object-cover grayscale"
            />
          </figure>
        </div>
      </section>

      <SideRail />
      <Footer />
    </article>
  );
}