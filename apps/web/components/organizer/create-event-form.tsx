"use client"

import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { AlertCircle, Building2, CalendarPlus, CheckCircle2, Loader2 } from "lucide-react"
import { type FormEvent, useEffect, useMemo, useState } from "react"
import { apiGet, apiPost, bearerHeaders } from "@/lib/api"
import type { MyClubSummary } from "@/lib/backend-clubs"
import { cn } from "@/lib/utils"

type CreatedEvent = {
  id: string
  title: string
  starts_at: string
  club_name: string
}

type FormState = {
  clubId: string
  title: string
  description: string
  eventType: string
  startsAt: string
  endsAt: string
  locationName: string
  address: string
  city: string
  capacity: string
  priceAmount: string
}

const CITY_SUGGESTIONS = ["Riyadh", "Jeddah", "Istanbul", "Ankara", "Dubai", "Doha", "London", "Paris"]
const EVENT_TYPE_SUGGESTIONS = ["community", "sports", "technology", "outdoors", "wellness", "food", "music", "creative", "networking"]
const MANAGER_ROLES = new Set(["owner", "admin"])

function toDatetimeLocal(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}`
}

function createInitialForm(): FormState {
  const starts = new Date(Date.now() + 86_400_000)
  starts.setMinutes(0, 0, 0)
  const ends = new Date(starts.getTime() + 2 * 3_600_000)

  return {
    clubId: "",
    title: "",
    description: "",
    eventType: "community",
    startsAt: toDatetimeLocal(starts),
    endsAt: toDatetimeLocal(ends),
    locationName: "",
    address: "",
    city: "Riyadh",
    capacity: "30",
    priceAmount: "0",
  }
}

export function CreateEventForm() {
  const { getToken } = useAuth()
  const [clubs, setClubs] = useState<MyClubSummary[]>([])
  const [form, setForm] = useState<FormState>(() => createInitialForm())
  const [loadingClubs, setLoadingClubs] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdEvent, setCreatedEvent] = useState<CreatedEvent | null>(null)

  useEffect(() => {
    let active = true

    async function loadClubs() {
      try {
        const token = await getToken()
        const data = await apiGet<MyClubSummary[]>("/me/clubs", {
          headers: bearerHeaders(token),
        })
        const manageableClubs = data.filter(
          (club) => MANAGER_ROLES.has(club.member_role) && club.member_status === "active",
        )
        if (!active) return
        setClubs(manageableClubs)
        setForm((current) => ({ ...current, clubId: current.clubId || manageableClubs[0]?.id || "" }))
      } catch (loadError) {
        if (!active) return
        console.error("Club loading failed.", loadError)
        setError("We could not load your clubs. Sign in again or check that the API is running.")
      } finally {
        if (active) setLoadingClubs(false)
      }
    }

    loadClubs()
    return () => {
      active = false
    }
  }, [getToken])

  const selectedClub = useMemo(() => clubs.find((club) => club.id === form.clubId), [clubs, form.clubId])

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setCreatedEvent(null)

    if (!form.clubId) {
      setError("Create or choose a club before creating an event.")
      return
    }

    if (!form.title.trim()) {
      setError("Event title is required.")
      return
    }

    setSubmitting(true)
    try {
      const token = await getToken()
      const payload = {
        club_id: form.clubId,
        title: form.title.trim(),
        description: form.description.trim() || null,
        event_type: form.eventType.trim().toLowerCase() || "community",
        starts_at: new Date(form.startsAt).toISOString(),
        ends_at: form.endsAt ? new Date(form.endsAt).toISOString() : null,
        timezone: "Asia/Riyadh",
        location_name: form.locationName.trim() || null,
        address: form.address.trim() || null,
        city: form.city.trim() || "Riyadh",
        country: "Saudi Arabia",
        capacity: form.capacity ? Number(form.capacity) : null,
        price_amount: form.priceAmount ? Number(form.priceAmount) : 0,
        currency: "SAR",
        status: "published",
        requires_approval: false,
      }

      const event = await apiPost<CreatedEvent>("/events", {
        body: JSON.stringify(payload),
        headers: bearerHeaders(token),
      })

      setCreatedEvent(event)
      setForm((current) => ({ ...createInitialForm(), clubId: current.clubId }))
    } catch (submitError) {
      console.error("Event creation failed.", submitError)
      setError(submitError instanceof Error ? submitError.message : "Event creation failed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-primary">Organizer tool</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Add a new event</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Publish an event under a club you own or administer.
          </p>
        </div>
        <Link
          href="/organizer/clubs/new"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background/50 px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-primary/50 hover:text-primary"
        >
          <Building2 className="size-3.5 text-primary" aria-hidden="true" />
          Create club
        </Link>
      </div>

      {error && (
        <div className="mt-5 flex gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}

      {createdEvent && (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/10 p-4 text-sm">
          <span className="inline-flex items-center gap-2 text-primary">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            {createdEvent.title} is live for {createdEvent.club_name}.
          </span>
          <Link href={`/explore/${createdEvent.id}`} className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">
            View event
          </Link>
        </div>
      )}

      {!loadingClubs && clubs.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-border bg-background/40 p-5">
          <h2 className="text-base font-semibold">Create your first club before adding events</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Every event belongs to a club. Once you create a club, you become its owner and can publish events for it.
          </p>
          <Link href="/organizer/clubs/new" className="mt-4 inline-flex rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
            Create club
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_1fr]">
          <Field label="Club">
            <select
              value={form.clubId}
              onChange={(event) => updateField("clubId", event.target.value)}
              disabled={loadingClubs || clubs.length === 0}
              className={inputClassName}
              required
            >
              {loadingClubs ? <option>Loading clubs...</option> : null}
              {clubs.map((club) => (
                <option key={club.id} value={club.id}>
                  {club.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Type">
            <input
              list="event-type-suggestions"
              value={form.eventType}
              onChange={(event) => updateField("eventType", event.target.value)}
              placeholder="Start typing, e.g. spo"
              className={inputClassName}
            />
            <datalist id="event-type-suggestions">
              {EVENT_TYPE_SUGGESTIONS.map((type) => (
                <option key={type} value={type} />
              ))}
            </datalist>
          </Field>

          <Field label="Title" className="lg:col-span-2">
            <input
              value={form.title}
              onChange={(event) => updateField("title", event.target.value)}
              placeholder="AI Builders Night"
              className={inputClassName}
              required
            />
          </Field>

          <Field label="Description" className="lg:col-span-2">
            <textarea
              value={form.description}
              onChange={(event) => updateField("description", event.target.value)}
              placeholder="Tell people what will happen, who it is for, and what they should expect."
              className={cn(inputClassName, "min-h-28 resize-y py-3")}
            />
          </Field>

          <Field label="Starts at">
            <input
              type="datetime-local"
              value={form.startsAt}
              onChange={(event) => updateField("startsAt", event.target.value)}
              className={inputClassName}
              required
            />
          </Field>

          <Field label="Ends at">
            <input
              type="datetime-local"
              value={form.endsAt}
              onChange={(event) => updateField("endsAt", event.target.value)}
              className={inputClassName}
            />
          </Field>

          <Field label="Location name">
            <input
              value={form.locationName}
              onChange={(event) => updateField("locationName", event.target.value)}
              placeholder="Innovation Hub Riyadh"
              className={inputClassName}
            />
          </Field>

          <Field label="City">
            <input
              list="city-suggestions"
              value={form.city}
              onChange={(event) => updateField("city", event.target.value)}
              placeholder="Start typing, e.g. ist"
              className={inputClassName}
            />
            <datalist id="city-suggestions">
              {CITY_SUGGESTIONS.map((city) => (
                <option key={city} value={city} />
              ))}
            </datalist>
          </Field>

          <Field label="Address" className="lg:col-span-2">
            <input
              value={form.address}
              onChange={(event) => updateField("address", event.target.value)}
              placeholder="Building, district, or meeting point"
              className={inputClassName}
            />
          </Field>

          <Field label="Capacity">
            <input
              type="number"
              min="1"
              value={form.capacity}
              onChange={(event) => updateField("capacity", event.target.value)}
              className={inputClassName}
            />
          </Field>

          <Field label="Price (SAR)">
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.priceAmount}
              onChange={(event) => updateField("priceAmount", event.target.value)}
              className={inputClassName}
            />
          </Field>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
        <p className="text-xs text-muted-foreground">
          {selectedClub ? `Publishing under ${selectedClub.name}.` : "Choose a club to publish this event."}
        </p>
        <button
          type="submit"
          disabled={submitting || loadingClubs || clubs.length === 0}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <CalendarPlus className="size-4" aria-hidden="true" />}
          {submitting ? "Publishing" : "Add event"}
        </button>
      </div>
    </form>
  )
}

function Field({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={cn("grid gap-2 text-sm font-medium", className)}>
      <span>{label}</span>
      {children}
    </label>
  )
}

const inputClassName =
  "h-11 w-full rounded-xl border border-border bg-background/60 px-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
