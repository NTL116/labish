"use server";

import { redirect } from "next/navigation";
import {
  saveSapConnectionSettingsSapSavePost,
  testSapConnectionSettingsSapTestPost,
} from "@/lib/api";
import { configureApiClient } from "@/lib/session";

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
