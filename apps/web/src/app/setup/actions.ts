"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import {
  ingestSapSchemaSettingsSapIngestPost,
  saveSapConnectionSettingsSapSavePost,
  testSapConnectionSettingsSapTestPost,
} from "@/lib/api";
import { configureApiClient, SESSION_COOKIE } from "@/lib/session";

type SAPConnectionForm = {
  service_layer_url: string;
  company_db: string;
  username: string;
  password: string;
  fallback_phone_number: string | null;
};

function parseForm(formData: FormData): SAPConnectionForm | null {
  const serviceLayerUrl = formData.get("service_layer_url");
  const companyDb = formData.get("company_db");
  const username = formData.get("username");
  const password = formData.get("password");
  const fallbackPhoneNumber = formData.get("fallback_phone_number");

  if (
    typeof serviceLayerUrl !== "string" ||
    typeof companyDb !== "string" ||
    typeof username !== "string" ||
    typeof password !== "string"
  ) {
    return null;
  }

  return {
    service_layer_url: serviceLayerUrl,
    company_db: companyDb,
    username,
    password,
    fallback_phone_number:
      typeof fallbackPhoneNumber === "string" && fallbackPhoneNumber.trim()
        ? fallbackPhoneNumber.trim()
        : null,
  };
}

export async function testSapConnectionAction(
  formData: FormData,
): Promise<void> {
  const body = parseForm(formData);
  if (!body) {
    redirect("/setup?status=error");
  }

  configureApiClient();
  const { data, error } = await testSapConnectionSettingsSapTestPost({ body });

  if (error || !data?.success) {
    redirect("/setup?status=test-failed");
  }
  redirect("/setup?status=test-ok");
}

export async function saveSapConnectionAction(
  formData: FormData,
): Promise<void> {
  const body = parseForm(formData);
  if (!body) {
    redirect("/setup?status=error");
  }

  configureApiClient();
  const { data, error } = await saveSapConnectionSettingsSapSavePost({ body });

  if (error || !data?.is_validated) {
    redirect("/setup?status=save-failed");
  }
  redirect("/setup?status=saved");
}

export async function ingestSapSchemaAction(): Promise<void> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/setup?status=ingest-unauthorized");
  }

  configureApiClient();
  const { data, error } = await ingestSapSchemaSettingsSapIngestPost({
    headers: { Authorization: `Bearer ${token}` },
  });

  if (error || !data?.success) {
    redirect("/setup?status=ingest-failed");
  }

  // Trigger an immediate local type-validation refresh: the regenerated
  // sap.d.ts / data dictionary invalidate the cached setup render.
  revalidatePath("/setup");
  redirect(
    `/setup?status=ingest-ok&entities=${data.entities}&complex=${data.complex_types}`,
  );
}
