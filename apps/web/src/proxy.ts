import { NextResponse, type NextRequest } from "next/server";
import { isSessionTokenUsable, SESSION_COOKIE } from "@/lib/session";

export function proxy(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const authenticated = isSessionTokenUsable(token);
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/portal") && !authenticated) {
    const loginUrl = new URL("/login", request.url);
    const response = NextResponse.redirect(loginUrl);
    if (token) {
      // Drop stale or malformed session cookies on the way out.
      response.cookies.delete(SESSION_COOKIE);
    }
    return response;
  }

  if (pathname.startsWith("/login") && authenticated) {
    return NextResponse.redirect(new URL("/portal", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/portal/:path*", "/login"],
};
