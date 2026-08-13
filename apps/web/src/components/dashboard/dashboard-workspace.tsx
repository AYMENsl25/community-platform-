"use client";

import { useEffect, useState } from "react";
import {
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import { Card, Container } from "@talaqi/ui";

type EventItem = {
  id: string;
  title: string;
  start_at: string | null;
  status: string;
  registration_state?: string | null;
  capacity?: number | null;
  held?: number | null;
  cash_pending?: number | null;
  action_path: string;
};
type ClubItem = {
  id: string;
  name: string;
  slug: string;
  role: string;
  status: string;
  pending_requests: number;
  action_path: string;
};
type NotificationItem = {
  id: string;
  type_key: string;
  action_path: string | null;
  read_at: string | null;
  created_at: string;
};
type MemberData = {
  upcoming_events: EventItem[];
  saved_events: EventItem[];
  joined_clubs: ClubItem[];
  notifications: NotificationItem[];
  profile_blockers: string[];
};
type OrganizerData = {
  clubs: ClubItem[];
  events: EventItem[];
  alerts: { key: string; action_path: string }[];
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="tq-dashboard-card">
      <h2>{title}</h2>
      {children}
    </Card>
  );
}

function Empty({ locale }: { locale: LocaleCode }) {
  return <p>{translate(locale, "dashboard.empty")}</p>;
}

function Events({
  items,
  locale,
  organizer = false,
}: {
  items: EventItem[];
  locale: LocaleCode;
  organizer?: boolean;
}) {
  if (!items.length) return <Empty locale={locale} />;
  return (
    <ul className="tq-dashboard-list">
      {items.map((item) => (
        <li key={item.id}>
          <div>
            <strong>{item.title}</strong>
            <p>
              {item.start_at
                ? new Intl.DateTimeFormat(locale, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(item.start_at))
                : translate(locale, "dashboard.schedulePending")}
            </p>
            {item.registration_state ? (
              <span>
                {translate(
                  locale,
                  `dashboard.state.${item.registration_state}` as TranslationKey,
                )}
              </span>
            ) : null}
            {organizer ? (
              <span>
                {translate(locale, "dashboard.capacity")}: {item.held ?? 0}/
                {item.capacity ?? "—"} ·{" "}
                {translate(locale, "dashboard.cashQueue")}:{" "}
                {item.cash_pending ?? 0}
              </span>
            ) : null}
          </div>
          <a href={item.action_path}>
            {translate(
              locale,
              item.registration_state === "confirmed"
                ? "dashboard.action.ticket"
                : item.registration_state === "cash_pending"
                  ? "dashboard.action.cash"
                  : item.registration_state === "waitlisted"
                    ? "dashboard.action.waitlist"
                    : "dashboard.open",
            )}
          </a>
        </li>
      ))}
    </ul>
  );
}

function Clubs({
  items,
  locale,
  organizer = false,
}: {
  items: ClubItem[];
  locale: LocaleCode;
  organizer?: boolean;
}) {
  if (!items.length) return <Empty locale={locale} />;
  return (
    <ul className="tq-dashboard-list">
      {items.map((item) => (
        <li key={item.id}>
          <div>
            <strong>{item.name}</strong>
            <p>
              {translate(
                locale,
                `dashboard.role.${item.role}` as TranslationKey,
              )}{" "}
              ·{" "}
              {translate(
                locale,
                `dashboard.status.${item.status}` as TranslationKey,
              )}
            </p>
            {organizer ? (
              <span>
                {translate(locale, "dashboard.requests")}:{" "}
                {item.pending_requests}
              </span>
            ) : null}
          </div>
          <a href={item.action_path}>{translate(locale, "dashboard.open")}</a>
        </li>
      ))}
    </ul>
  );
}

export function DashboardWorkspace({
  role,
  locale,
}: {
  role: "member" | "organizer";
  locale: LocaleCode;
}) {
  const [data, setData] = useState<MemberData | OrganizerData>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const path = role === "member" ? "me" : "organizer";
    void fetch(`/api/organizer/api/v1/${path}/dashboard`, {
      cache: "no-store",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("dashboard_unavailable");
        return response.json();
      })
      .then((value) => {
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [role]);

  return (
    <Container>
      <section className="tq-dashboard" aria-labelledby="dashboard-title">
        <header>
          <h1 id="dashboard-title">
            {translate(
              locale,
              role === "member"
                ? "dashboard.member.title"
                : "dashboard.organizer.title",
            )}
          </h1>
          <p>
            {translate(
              locale,
              role === "member"
                ? "dashboard.member.lead"
                : "dashboard.organizer.lead",
            )}
          </p>
        </header>
        {failed ? (
          <p role="alert">{translate(locale, "dashboard.error")}</p>
        ) : !data ? (
          <p role="status">{translate(locale, "dashboard.loading")}</p>
        ) : role === "member" ? (
          <MemberDashboard data={data as MemberData} locale={locale} />
        ) : (
          <OrganizerDashboard data={data as OrganizerData} locale={locale} />
        )}
      </section>
    </Container>
  );
}

function MemberDashboard({
  data,
  locale,
}: {
  data: MemberData;
  locale: LocaleCode;
}) {
  return (
    <div className="tq-dashboard-grid">
      <Section title={translate(locale, "dashboard.upcoming")}>
        <Events items={data.upcoming_events} locale={locale} />
      </Section>
      <Section title={translate(locale, "dashboard.saved")}>
        <Events items={data.saved_events} locale={locale} />
      </Section>
      <Section title={translate(locale, "dashboard.clubs")}>
        <Clubs items={data.joined_clubs} locale={locale} />
      </Section>
      <Section title={translate(locale, "dashboard.notifications")}>
        {data.notifications.length ? (
          <ul className="tq-dashboard-list">
            {data.notifications.map((item) => (
              <li key={item.id}>
                <span>{translate(locale, "dashboard.notificationUpdate")}</span>
                {item.action_path ? (
                  <a href={item.action_path}>
                    {translate(locale, "dashboard.open")}
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <Empty locale={locale} />
        )}
      </Section>
      <Section title={translate(locale, "dashboard.profile")}>
        <p>
          {data.profile_blockers.length
            ? translate(locale, "dashboard.profileBlocked")
            : translate(locale, "dashboard.profileReady")}
        </p>
      </Section>
    </div>
  );
}

function OrganizerDashboard({
  data,
  locale,
}: {
  data: OrganizerData;
  locale: LocaleCode;
}) {
  return (
    <div className="tq-dashboard-grid">
      <Section title={translate(locale, "dashboard.managedClubs")}>
        <Clubs items={data.clubs} locale={locale} organizer />
      </Section>
      <Section title={translate(locale, "dashboard.managedEvents")}>
        <Events items={data.events} locale={locale} organizer />
      </Section>
      <Section title={translate(locale, "dashboard.alerts")}>
        {data.alerts.length ? (
          <ul>
            {data.alerts.map((alert) => (
              <li key={alert.key}>
                <a href={alert.action_path}>
                  {translate(
                    locale,
                    `dashboard.alert.${alert.key}` as TranslationKey,
                  )}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <Empty locale={locale} />
        )}
      </Section>
    </div>
  );
}
