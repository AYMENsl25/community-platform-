"use client";

import type { TranslationKey } from "@talaqi/translations";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import {
  createOrganizerClient,
  type ClubJoinRequest,
  type ClubMember,
  type ManagedClub,
  type OrganizerResult,
} from "@/lib/api/organizer-client";
import { useLocale } from "@/lib/locale/locale-context";
import { CommunicationsPanel } from "./communications-panel";

type Feedback = {
  key: TranslationKey;
  requestId?: string;
  fieldNames?: string[];
};
type Confirmation =
  | { kind: "role"; member: ClubMember; nextRole: "admin" | "member" }
  | { kind: "ownership"; member: ClubMember }
  | { kind: "reject"; request: ClubJoinRequest }
  | { kind: "close" };

const profileFields = new Set([
  "name",
  "slug",
  "description",
  "category_slug",
  "country_code",
  "city_slug",
  "membership_policy",
  "revision",
]);

const roleKeys = {
  owner: "organizer.role.owner",
  admin: "organizer.role.admin",
  member: "organizer.role.member",
} as const satisfies Record<ClubMember["role"], TranslationKey>;

const statusKeys = {
  draft: "organizer.status.draft",
  published: "organizer.status.published",
  unpublished: "organizer.status.unpublished",
  suspended: "organizer.status.suspended",
  closed: "organizer.status.closed",
} as const satisfies Record<ManagedClub["status"], TranslationKey>;

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("talaqi_csrf="));
  return entry
    ? decodeURIComponent(entry.slice("talaqi_csrf=".length))
    : undefined;
}

function hasCapability(club: ManagedClub, capability: string): boolean {
  return club.capabilities.includes(
    capability as ManagedClub["capabilities"][number],
  );
}

export function ClubWorkspace({
  initialClubs,
  initialMembers,
  initialRequests,
  initialError,
}: {
  initialClubs: ManagedClub[];
  initialMembers: ClubMember[];
  initialRequests: ClubJoinRequest[];
  initialError?: Feedback;
}) {
  const { t } = useLocale();
  const [clubs, setClubs] = useState(initialClubs);
  const [selectedId, setSelectedId] = useState(initialClubs[0]?.id ?? "");
  const selectedIdRef = useRef(initialClubs[0]?.id ?? "");
  const [members, setMembers] = useState(initialMembers);
  const [requests, setRequests] = useState(initialRequests);
  const [decisionReasons, setDecisionReasons] = useState<
    Record<string, string>
  >({});
  const [feedback, setFeedback] = useState<Feedback | undefined>(initialError);
  const [notice, setNotice] = useState<TranslationKey>();
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState<Confirmation>();
  const [auditReason, setAuditReason] = useState("");
  const [understood, setUnderstood] = useState(false);
  const reasonRef = useRef<HTMLInputElement>(null);
  const loadSequenceRef = useRef(0);
  const confirmationTriggerRef = useRef<HTMLElement | null>(null);
  const confirmationFocusKeyRef = useRef<string | undefined>(undefined);
  const client = useMemo(
    () =>
      createOrganizerClient({
        baseUrl: "/api/organizer",
        csrfToken: csrfToken(),
      }),
    [],
  );
  const selected = clubs.find((club) => club.id === selectedId) ?? clubs[0];

  function showFailure(
    result: Extract<OrganizerResult<unknown>, { ok: false }>,
  ) {
    setNotice(undefined);
    setFeedback({
      key: result.key,
      fieldNames: result.fieldNames.filter((field) => profileFields.has(field)),
      ...(result.requestId ? { requestId: result.requestId } : {}),
    });
  }

  async function loadPeople(
    club: ManagedClub,
    sequence: number,
  ): Promise<boolean> {
    if (!hasCapability(club, "manage_members")) {
      if (sequence === loadSequenceRef.current) {
        setMembers([]);
        setRequests([]);
      }
      return true;
    }
    const [memberResult, requestResult] = await Promise.all([
      client.listMembers(club.id),
      client.listRequests(club.id),
    ]);
    if (sequence !== loadSequenceRef.current) return false;
    if (memberResult.ok) setMembers(memberResult.data.items);
    else showFailure(memberResult);
    if (requestResult.ok) setRequests(requestResult.data.items);
    else showFailure(requestResult);
    return memberResult.ok && requestResult.ok;
  }

  async function selectClub(club: ManagedClub) {
    const sequence = ++loadSequenceRef.current;
    selectedIdRef.current = club.id;
    setSelectedId(club.id);
    setMembers([]);
    setRequests([]);
    setDecisionReasons({});
    setFeedback(undefined);
    setNotice(undefined);
    await loadPeople(club, sequence);
  }

  useEffect(() => {
    if (!confirmation) return;
    reasonRef.current?.focus();
  }, [confirmation]);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setFeedback(undefined);
    const result = await client.updateClub(selected.id, {
      revision: selected.revision,
      name: String(form.get("name") ?? ""),
      slug: String(form.get("slug") ?? ""),
      description: String(form.get("description") ?? ""),
      category_slug: String(form.get("category_slug") ?? ""),
      country_code: String(form.get("country_code") ?? ""),
      city_slug: String(form.get("city_slug") ?? ""),
      membership_policy: String(form.get("membership_policy")) as
        "open" | "approval_required",
    });
    setBusy(false);
    if (!result.ok) return showFailure(result);
    setClubs((current) =>
      current.map((club) =>
        club.id === selected.id
          ? { ...club, ...result.data, capabilities: club.capabilities }
          : club,
      ),
    );
    setNotice("organizer.notice.saved");
  }

  async function approve(request: ClubJoinRequest) {
    if (!selected) return;
    const clubId = selected.id;
    const reason = decisionReasons[request.id] ?? "";
    setBusy(true);
    const result = await client.approveRequest(selected.id, request.id, reason);
    setBusy(false);
    if (!result.ok) return showFailure(result);
    if (selectedIdRef.current !== clubId) return;
    setRequests((current) => current.filter((item) => item.id !== request.id));
    setDecisionReasons((current) => ({ ...current, [request.id]: "" }));
    const sequence = ++loadSequenceRef.current;
    const memberResult = await client.listMembers(clubId);
    if (
      sequence === loadSequenceRef.current &&
      selectedIdRef.current === clubId
    ) {
      if (memberResult.ok) setMembers(memberResult.data.items);
      else showFailure(memberResult);
    }
    setNotice("organizer.notice.completed");
  }

  function openConfirmation(
    value: Confirmation,
    trigger: HTMLElement,
    focusKey: string,
    initialReason = "",
  ) {
    confirmationTriggerRef.current = trigger;
    confirmationFocusKeyRef.current = focusKey;
    setAuditReason(initialReason);
    setUnderstood(false);
    setConfirmation(value);
  }

  function closeConfirmation(preferNavigation = false) {
    const trigger = confirmationTriggerRef.current;
    const focusKey = confirmationFocusKeyRef.current;
    setConfirmation(undefined);
    requestAnimationFrame(() => {
      const replacement = focusKey
        ? document.querySelector<HTMLElement>(`[data-action-key="${focusKey}"]`)
        : null;
      const navigationTarget = document.querySelector<HTMLElement>(
        `[data-club-key="${selectedIdRef.current}"]`,
      );
      const target = preferNavigation
        ? navigationTarget
        : (replacement ?? (trigger?.isConnected ? trigger : navigationTarget));
      target?.focus();
    });
  }

  function handleDialogKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      if (busy) return;
      closeConfirmation();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>(
        "input:not([disabled]), button:not([disabled])",
      ),
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }

  async function confirmAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !confirmation || !understood) return;
    setBusy(true);
    const result =
      confirmation.kind === "role"
        ? await client.changeRole(
            selected.id,
            confirmation.member.user_id,
            confirmation.nextRole,
            auditReason,
          )
        : confirmation.kind === "ownership"
          ? await client.transferOwnership(
              selected.id,
              confirmation.member.user_id,
              auditReason,
            )
          : confirmation.kind === "reject"
            ? await client.rejectRequest(
                selected.id,
                confirmation.request.id,
                auditReason,
              )
            : await client.closeClub(selected.id, auditReason);
    if (!result.ok) {
      setBusy(false);
      return showFailure(result);
    }
    if (confirmation.kind === "role") {
      setMembers((current) =>
        current.map((member) =>
          member.user_id === confirmation.member.user_id
            ? { ...member, role: confirmation.nextRole }
            : member,
        ),
      );
    } else if (confirmation.kind === "reject") {
      setRequests((current) =>
        current.filter((item) => item.id !== confirmation.request.id),
      );
      setDecisionReasons((current) => ({
        ...current,
        [confirmation.request.id]: "",
      }));
    } else if (confirmation.kind === "close") {
      setClubs((current) =>
        current.map((club) =>
          club.id === selected.id
            ? { ...club, status: "closed", capabilities: [] }
            : club,
        ),
      );
    } else {
      const refreshed = await client.listManagedClubs();
      if (refreshed.ok) {
        setClubs(refreshed.data.items);
        const refreshedSelected = refreshed.data.items.find(
          (club) => club.id === selected.id,
        );
        if (refreshedSelected) {
          const peopleLoaded = await loadPeople(
            refreshedSelected,
            ++loadSequenceRef.current,
          );
          if (!peopleLoaded) {
            setBusy(false);
            closeConfirmation(true);
            return;
          }
        } else {
          setMembers([]);
          setRequests([]);
        }
      } else {
        setClubs((current) =>
          current.map((club) =>
            club.id === selected.id ? { ...club, capabilities: [] } : club,
          ),
        );
        showFailure(refreshed);
        setBusy(false);
        closeConfirmation(true);
        return;
      }
    }
    setBusy(false);
    closeConfirmation(confirmation.kind !== "role");
    setNotice("organizer.notice.completed");
  }

  const confirmationTitle =
    confirmation?.kind === "role"
      ? "organizer.dialog.roleTitle"
      : confirmation?.kind === "ownership"
        ? "organizer.dialog.ownershipTitle"
        : confirmation?.kind === "reject"
          ? "organizer.dialog.rejectTitle"
          : "organizer.dialog.closeTitle";
  const confirmationLabel =
    confirmation?.kind === "role"
      ? confirmation.nextRole === "admin"
        ? "organizer.members.promote"
        : "organizer.members.demote"
      : confirmation?.kind === "ownership"
        ? "organizer.members.transfer"
        : confirmation?.kind === "reject"
          ? "organizer.requests.reject"
          : "organizer.close";
  const invalidFields = new Set(feedback?.fieldNames ?? []);

  return (
    <section className="tq-organizer" aria-labelledby="organizer-title">
      <header className="tq-organizer__header">
        <div>
          <h1 id="organizer-title">{t("organizer.title")}</h1>
          <p>{t("organizer.lead")}</p>
        </div>
      </header>

      {feedback ? (
        <div className="tq-organizer__alert" role="alert">
          <p>{t(feedback.key)}</p>
          {feedback.fieldNames?.length ? (
            <div>
              <p>{t("organizer.error.fields")}</p>
              <ul>
                {feedback.fieldNames.map((field) => (
                  <li id={`profile-error-${field}`} key={field}>
                    {field}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {feedback.requestId ? (
            <p>
              {t("organizer.error.requestId")}:{" "}
              <code>{feedback.requestId}</code>
            </p>
          ) : null}
        </div>
      ) : null}
      {notice ? (
        <p className="tq-organizer__notice" role="status">
          {t(notice)}
        </p>
      ) : null}

      {clubs.length === 0 ? (
        <p className="tq-organizer__empty">{t("organizer.empty")}</p>
      ) : (
        <div className="tq-organizer__layout">
          <nav
            aria-label={t("organizer.clubNavigation")}
            className="tq-club-switcher"
          >
            <h2>{t("organizer.clubNavigation")}</h2>
            <ul>
              {clubs.map((club) => (
                <li key={club.id}>
                  <button
                    aria-current={club.id === selected?.id ? "page" : undefined}
                    data-club-key={club.id}
                    onClick={() => void selectClub(club)}
                    type="button"
                  >
                    <span>{club.name}</span>
                    <small>
                      {t(roleKeys[club.role])} · {t(statusKeys[club.status])}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {selected ? (
            <div className="tq-organizer__content">
              <section
                className="tq-organizer-card"
                aria-labelledby="profile-title"
              >
                <div className="tq-organizer-card__heading">
                  <div>
                    <h2 id="profile-title">{t("organizer.profile.title")}</h2>
                    <p>{t("organizer.profile.help")}</p>
                  </div>
                  <span className="tq-status-chip">
                    {t(statusKeys[selected.status])}
                  </span>
                </div>
                {hasCapability(selected, "edit_profile") ? (
                  <form
                    className="tq-club-form"
                    key={selected.id}
                    onSubmit={saveProfile}
                  >
                    <label>
                      {t("organizer.profile.name")}
                      <input
                        aria-describedby={
                          invalidFields.has("name")
                            ? "profile-error-name"
                            : undefined
                        }
                        aria-invalid={invalidFields.has("name") || undefined}
                        defaultValue={selected.name}
                        name="name"
                        required
                      />
                    </label>
                    <label>
                      {t("organizer.profile.slug")}
                      <input
                        aria-describedby={
                          invalidFields.has("slug")
                            ? "profile-error-slug"
                            : undefined
                        }
                        aria-invalid={invalidFields.has("slug") || undefined}
                        defaultValue={selected.slug}
                        name="slug"
                        required
                      />
                    </label>
                    <label className="tq-club-form__wide">
                      {t("organizer.profile.description")}
                      <textarea
                        aria-describedby={
                          invalidFields.has("description")
                            ? "profile-error-description"
                            : undefined
                        }
                        aria-invalid={
                          invalidFields.has("description") || undefined
                        }
                        defaultValue={selected.description ?? ""}
                        name="description"
                        required
                      />
                    </label>
                    <label>
                      {t("organizer.profile.category")}
                      <select
                        aria-describedby={
                          invalidFields.has("category_slug")
                            ? "profile-error-category_slug"
                            : undefined
                        }
                        aria-invalid={
                          invalidFields.has("category_slug") || undefined
                        }
                        defaultValue={selected.category_slug ?? ""}
                        name="category_slug"
                        required
                      >
                        <option value="" />
                        <option value="sports">{t("categories.sports")}</option>
                        <option value="arts-culture">
                          {t("categories.arts-culture")}
                        </option>
                        <option value="technology">
                          {t("categories.technology")}
                        </option>
                        <option value="language-exchange">
                          {t("categories.language-exchange")}
                        </option>
                        <option value="outdoors">
                          {t("categories.outdoors")}
                        </option>
                        <option value="games">{t("categories.games")}</option>
                      </select>
                    </label>
                    <label>
                      {t("organizer.profile.country")}
                      <select
                        aria-describedby={
                          invalidFields.has("country_code")
                            ? "profile-error-country_code"
                            : undefined
                        }
                        aria-invalid={
                          invalidFields.has("country_code") || undefined
                        }
                        defaultValue={selected.country_code ?? ""}
                        name="country_code"
                        required
                      >
                        <option value="" />
                        <option value="TR">{t("regions.country.tr")}</option>
                        <option value="DZ">{t("regions.country.dz")}</option>
                      </select>
                    </label>
                    <label>
                      {t("organizer.profile.city")}
                      <select
                        aria-describedby={
                          invalidFields.has("city_slug")
                            ? "profile-error-city_slug"
                            : undefined
                        }
                        aria-invalid={
                          invalidFields.has("city_slug") || undefined
                        }
                        defaultValue={selected.city_slug ?? ""}
                        name="city_slug"
                        required
                      >
                        <option value="" />
                        <option value="istanbul">
                          {t("regions.city.istanbul")}
                        </option>
                        <option value="algiers">
                          {t("regions.city.algiers")}
                        </option>
                      </select>
                    </label>
                    <label>
                      {t("organizer.profile.membershipPolicy")}
                      <select
                        aria-describedby={
                          invalidFields.has("membership_policy")
                            ? "profile-error-membership_policy"
                            : undefined
                        }
                        aria-invalid={
                          invalidFields.has("membership_policy") || undefined
                        }
                        defaultValue={selected.membership_policy}
                        name="membership_policy"
                      >
                        <option value="open">
                          {t("organizer.profile.open")}
                        </option>
                        <option value="approval_required">
                          {t("organizer.profile.approval")}
                        </option>
                      </select>
                    </label>
                    <button
                      className="tq-organizer-button tq-organizer-button--primary"
                      disabled={busy}
                      type="submit"
                    >
                      {t("organizer.profile.save")}
                    </button>
                  </form>
                ) : null}
              </section>

              {hasCapability(selected, "preview_profile") ? (
                <section
                  className="tq-organizer-card tq-profile-preview"
                  aria-labelledby="preview-title"
                >
                  <h2 id="preview-title">{t("organizer.preview.title")}</h2>
                  <h3>{selected.name}</h3>
                  <p>{selected.description}</p>
                  {selected.status === "published" ? (
                    <a href={`/clubs/${selected.slug}`}>
                      {t("organizer.preview.publicLink")}
                    </a>
                  ) : null}
                </section>
              ) : null}

              {hasCapability(selected, "manage_members") ? (
                <PeopleTables
                  busy={busy}
                  club={selected}
                  decisionReasons={decisionReasons}
                  members={members}
                  onConfirm={openConfirmation}
                  onApprove={(request) => void approve(request)}
                  onReason={(id, reason) =>
                    setDecisionReasons((current) => ({
                      ...current,
                      [id]: reason,
                    }))
                  }
                  requests={requests}
                  t={t}
                />
              ) : null}

              {hasCapability(selected, "edit_profile") ? (
                <CommunicationsPanel kind="club" resourceId={selected.id} />
              ) : null}

              {hasCapability(selected, "close_club") ? (
                <button
                  className="tq-organizer-button tq-organizer-button--danger"
                  data-action-key="close"
                  onClick={(event) =>
                    openConfirmation(
                      { kind: "close" },
                      event.currentTarget,
                      "close",
                    )
                  }
                  type="button"
                >
                  {t("organizer.close")}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {confirmation ? (
        <div
          aria-labelledby="confirmation-title"
          aria-modal="true"
          className="tq-confirmation-backdrop"
          onKeyDown={handleDialogKeyDown}
          role="alertdialog"
        >
          <form className="tq-confirmation" onSubmit={confirmAction}>
            <h2 id="confirmation-title">{t(confirmationTitle)}</h2>
            <p>{t("organizer.dialog.warning")}</p>
            <p>
              <strong>
                {confirmation.kind === "role" ||
                confirmation.kind === "ownership"
                  ? confirmation.member.display_name
                  : confirmation.kind === "reject"
                    ? confirmation.request.display_name
                    : selected?.name}
              </strong>
              {confirmation.kind !== "close" && selected
                ? ` · ${selected.name}`
                : null}
            </p>
            <label>
              {t("organizer.dialog.reason")}
              <input
                minLength={3}
                onChange={(event) => setAuditReason(event.target.value)}
                ref={reasonRef}
                required
                value={auditReason}
              />
            </label>
            <label className="tq-confirmation__check">
              <input
                checked={understood}
                onChange={(event) => setUnderstood(event.target.checked)}
                required
                type="checkbox"
              />
              {t("organizer.dialog.understand")}
            </label>
            <div className="tq-confirmation__actions">
              <button
                disabled={busy}
                onClick={() => closeConfirmation()}
                type="button"
              >
                {t("common.cancel")}
              </button>
              <button
                className="tq-organizer-button--danger"
                disabled={busy || !understood || auditReason.trim().length < 3}
                type="submit"
              >
                {t(confirmationLabel)}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  );
}

function PeopleTables({
  busy,
  club,
  decisionReasons,
  members,
  onApprove,
  onConfirm,
  onReason,
  requests,
  t,
}: {
  busy: boolean;
  club: ManagedClub;
  decisionReasons: Record<string, string>;
  members: ClubMember[];
  onApprove: (request: ClubJoinRequest) => void;
  onConfirm: (
    value: Confirmation,
    trigger: HTMLElement,
    focusKey: string,
    initialReason?: string,
  ) => void;
  onReason: (id: string, reason: string) => void;
  requests: ClubJoinRequest[];
  t: (key: TranslationKey) => string;
}) {
  return (
    <>
      <section className="tq-organizer-card" aria-labelledby="members-title">
        <h2 id="members-title">{t("organizer.members.title")}</h2>
        {members.length === 0 ? (
          <p>{t("organizer.members.empty")}</p>
        ) : (
          <div className="tq-table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("organizer.members.name")}</th>
                  <th scope="col">{t("organizer.members.email")}</th>
                  <th scope="col">{t("organizer.members.role")}</th>
                  <th scope="col">{t("organizer.members.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.user_id}>
                    <td>{member.display_name}</td>
                    <td>{member.email}</td>
                    <td>{t(roleKeys[member.role])}</td>
                    <td className="tq-table-actions">
                      {hasCapability(club, "change_member_roles") &&
                      member.role !== "owner" ? (
                        <button
                          data-action-key={`role-${member.user_id}`}
                          onClick={(event) =>
                            onConfirm(
                              {
                                kind: "role",
                                member,
                                nextRole:
                                  member.role === "admin" ? "member" : "admin",
                              },
                              event.currentTarget,
                              `role-${member.user_id}`,
                            )
                          }
                          type="button"
                        >
                          {t(
                            member.role === "admin"
                              ? "organizer.members.demote"
                              : "organizer.members.promote",
                          )}
                        </button>
                      ) : null}
                      {hasCapability(club, "transfer_ownership") &&
                      member.role !== "owner" ? (
                        <button
                          data-action-key={`ownership-${member.user_id}`}
                          onClick={(event) =>
                            onConfirm(
                              { kind: "ownership", member },
                              event.currentTarget,
                              `ownership-${member.user_id}`,
                            )
                          }
                          type="button"
                        >
                          {t("organizer.members.transfer")}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="tq-organizer-card" aria-labelledby="requests-title">
        <h2 id="requests-title">{t("organizer.requests.title")}</h2>
        {requests.length === 0 ? (
          <p>{t("organizer.requests.empty")}</p>
        ) : (
          <ul className="tq-request-list">
            {requests.map((request) => (
              <li key={request.id}>
                <strong>{request.display_name}</strong>
                <span>{request.email}</span>
                <p>{request.message}</p>
                <label>
                  {t("organizer.requests.reason")}
                  <input
                    minLength={3}
                    onChange={(event) =>
                      onReason(request.id, event.target.value)
                    }
                    value={decisionReasons[request.id] ?? ""}
                  />
                </label>
                <div className="tq-table-actions">
                  <button
                    disabled={
                      busy ||
                      (decisionReasons[request.id]?.trim().length ?? 0) < 3
                    }
                    onClick={() => onApprove(request)}
                    type="button"
                  >
                    {t("organizer.requests.approve")}
                  </button>
                  <button
                    data-action-key={`reject-${request.id}`}
                    disabled={
                      busy ||
                      (decisionReasons[request.id]?.trim().length ?? 0) < 3
                    }
                    onClick={(event) =>
                      onConfirm(
                        { kind: "reject", request },
                        event.currentTarget,
                        `reject-${request.id}`,
                        decisionReasons[request.id] ?? "",
                      )
                    }
                    type="button"
                  >
                    {t("organizer.requests.reject")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
