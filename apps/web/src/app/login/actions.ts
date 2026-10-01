"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { loginAuthLoginPost } from "@/lib/api";
import { configureApiClient, SESSION_COOKIE } from "@/lib/session";

export async function loginAction(formData: FormData): Promise<void> {
  const email = formData.get("email");
  const password = formData.get("password");

  if (typeof email !== "string" || typeof password !== "string") {
    redirect("/login?error=1");
  }

  configureApiClient();
  const { data, error } = await loginAuthLoginPost({
    body: { email, password },
  });

  if (error || !data) {
    redirect("/login?error=1");
  }

  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 60 * 30,
  });

  redirect("/portal");
}
