import {
  getLocaleDirection,
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import { Container, SkipLink } from "@talaqi/ui";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { LogoutButton } from "@/components/pwa/logout-button";

type ShellProps = {
  children: ReactNode;
  locale: LocaleCode;
  currentHref: string;
};

type NavigationItem = {
  href: string;
  label: TranslationKey;
};

const publicNavigation: NavigationItem[] = [
  { href: "/explore", label: "shell.navigation.explore" },
  { href: "/", label: "shell.navigation.home" },
  { href: "#community", label: "shell.navigation.community" },
  { href: "#about", label: "shell.navigation.about" },
];

const workspaceNavigation = {
  member: [
    { href: "/overview", label: "shell.navigation.overview" },
    { href: "/calendar", label: "shell.navigation.calendar" },
    { href: "/clubs", label: "shell.navigation.clubs" },
  ],
  organizer: [
    { href: "/organizer/overview", label: "shell.navigation.overview" },
    { href: "/organizer/clubs", label: "shell.navigation.clubs" },
    { href: "/organizer/events", label: "shell.navigation.events" },
    { href: "/calendar", label: "shell.navigation.calendar" },
  ],
  admin: [
    { href: "/overview", label: "shell.navigation.overview" },
    { href: "/admin/review", label: "shell.navigation.review" },
    { href: "/admin/audit", label: "shell.navigation.audit" },
    { href: "/admin/operations", label: "shell.navigation.operations" },
  ],
} satisfies Record<string, NavigationItem[]>;

function Brand({
  locale,
  compact = false,
}: {
  locale: LocaleCode;
  compact?: boolean;
}) {
  return (
    <Link className="tq-brand" href="/">
      <Image
        alt={translate(locale, "brand.name")}
        className={compact ? "tq-brand__icon" : "tq-brand__wordmark"}
        height={compact ? 64 : 88}
        priority={!compact}
        src={compact ? "/brand/talaqi-icon.png" : "/brand/talaqi-wordmark.png"}
        width={compact ? 62 : 249}
        unoptimized
      />
    </Link>
  );
}

function Navigation({
  currentHref,
  items,
  label,
  locale,
  variant,
}: {
  currentHref: string;
  items: NavigationItem[];
  label: TranslationKey;
  locale: LocaleCode;
  variant: "public" | "workspace";
}) {
  return (
    <nav
      aria-label={translate(locale, label)}
      className={`tq-navigation tq-navigation--${variant}`}
    >
      <ul>
        {items.map((item) => (
          <li key={item.href}>
            <a
              aria-current={currentHref === item.href ? "page" : undefined}
              href={item.href}
            >
              {translate(locale, item.label)}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function ShellFooter({ locale }: { locale: LocaleCode }) {
  return (
    <footer className="tq-shell-footer">
      <Container>
        <p>{translate(locale, "shell.footer.tagline")}</p>
      </Container>
    </footer>
  );
}

export function PublicShell({ children, currentHref, locale }: ShellProps) {
  return (
    <div
      className="tq-shell tq-public-shell"
      dir={getLocaleDirection(locale)}
      lang={locale}
    >
      <SkipLink href="#main-content">
        {translate(locale, "shell.skipToContent")}
      </SkipLink>
      <header className="tq-public-header">
        <Container className="tq-public-header__inner">
          <Brand locale={locale} />
          <Navigation
            currentHref={currentHref}
            items={publicNavigation}
            label="shell.navigation.primary"
            locale={locale}
            variant="public"
          />
        </Container>
      </header>
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <ShellFooter locale={locale} />
    </div>
  );
}

type WorkspaceRole = keyof typeof workspaceNavigation;

const roleLabels = {
  member: "shell.role.member",
  organizer: "shell.role.organizer",
  admin: "shell.role.admin",
} satisfies Record<WorkspaceRole, TranslationKey>;

function WorkspaceShell({
  children,
  currentHref,
  locale,
  role,
}: ShellProps & { role: WorkspaceRole }) {
  const roleLabel = roleLabels[role];
  return (
    <div
      className="tq-shell tq-workspace-shell"
      dir={getLocaleDirection(locale)}
      lang={locale}
    >
      <SkipLink href="#main-content">
        {translate(locale, "shell.skipToContent")}
      </SkipLink>
      <header className="tq-workspace-header">
        <Container className="tq-workspace-header__inner">
          <Brand compact locale={locale} />
          <strong>{translate(locale, roleLabel)}</strong>
          <LogoutButton locale={locale} />
        </Container>
      </header>
      <div className="tq-workspace-frame">
        <aside
          aria-label={translate(locale, roleLabel)}
          className="tq-workspace-aside"
        >
          <h2>{translate(locale, roleLabel)}</h2>
          <Navigation
            currentHref={currentHref}
            items={workspaceNavigation[role]}
            label="shell.navigation.workspace"
            locale={locale}
            variant="workspace"
          />
        </aside>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
      <ShellFooter locale={locale} />
    </div>
  );
}

export function MemberShell(props: ShellProps) {
  return <WorkspaceShell {...props} role="member" />;
}

export function OrganizerShell(props: ShellProps) {
  return <WorkspaceShell {...props} role="organizer" />;
}

export function AdminShell(props: ShellProps) {
  return <WorkspaceShell {...props} role="admin" />;
}
