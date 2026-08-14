import { arabicDictionary } from "./dictionaries/ar";
import {
  englishDictionary,
  type Dictionary,
  type TranslationKey,
} from "./dictionaries/en";
import { frenchDictionary } from "./dictionaries/fr";
import { turkishDictionary } from "./dictionaries/tr";
import type { LocaleCode } from "./types";

export const dictionaries = {
  en: englishDictionary,
  tr: turkishDictionary,
  fr: frenchDictionary,
  ar: arabicDictionary,
} satisfies Record<LocaleCode, Dictionary>;

export const API_MESSAGE_KEYS = [
  "errors.unknown",
  "errors.admin_mfa_required",
  "errors.authentication_required",
  "errors.bad_request",
  "errors.conflict",
  "errors.unavailable",
  "errors.csrf_failed",
  "errors.forbidden",
  "errors.http",
  "errors.idempotency_conflict",
  "errors.idempotency_in_progress",
  "errors.internal",
  "errors.invalid_credentials",
  "errors.invalid_credentials_input",
  "errors.invalid_cursor",
  "errors.notification_not_found",
  "errors.profile_required",
  "errors.invalid_profile",
  "errors.invalid_recovery_token",
  "errors.invalid_session",
  "errors.legal_acceptance_required",
  "errors.method_not_allowed",
  "errors.not_found",
  "errors.rate_limited",
  "errors.cancellation_closed",
  "errors.cash_confirmation_expired",
  "errors.registration_closed",
  "errors.registration_not_allowed",
  "errors.region_not_found",
  "errors.unauthorized",
  "errors.username_unavailable",
  "errors.validation",
  "errors.feature_disabled",
  "errors.validation.invalid",
  "errors.validation.missing",
  "errors.validation.extra_forbidden",
  "errors.validation.string_too_short",
  "errors.validation.string_too_long",
  "errors.validation.string_type",
  "errors.validation.bool_type",
  "errors.validation.literal_error",
  "errors.validation.int_parsing",
  "errors.validation.int_type",
  "errors.validation.uuid_parsing",
  "errors.profile.username_taken",
] as const satisfies readonly TranslationKey[];

export function translate(locale: LocaleCode, key: TranslationKey): string {
  return dictionaries[locale][key];
}
