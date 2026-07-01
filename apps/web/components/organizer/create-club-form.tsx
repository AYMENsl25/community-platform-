"use client"

import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { AlertCircle, Building2, CheckCircle2, Loader2 } from "lucide-react"
import { type FormEvent, useState } from "react"
import { apiPost, bearerHeaders } from "@/lib/api"
import { cn } from "@/lib/utils"

type CreatedClub = {
  id: string
  name: string
  slug: string
  city: string | null
}

type FormState = {
  name: string
  description: string
  city: string
  country: string
  visibility: string
}

const CITY_SUGGESTIONS = ["Riyadh", "Jeddah", "Istanbul", "Ankara", "Dubai", "Doha", "London", "Paris"]

export function CreateClubForm() {
  const { getToken } = useAuth()
  const [form, setForm] = useState<FormState>({
    name: "",
    description: "",
    city: "Riyadh",
    country: "Saudi Arabia",
    visibility: "public",
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdClub, setCreatedClub] = useState<CreatedClub | null>(null)

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setCreatedClub(null)

    if (!form.name.trim()) {
      setError("Club name is required.")
      return
    }

    setSubmitting(true)
    try {
      const token = await getToken()
      const club = await apiPost<CreatedClub>("/clubs", {
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description.trim() || null,
          city: form.city.trim() || "Riyadh",
          country: form.country.trim() || "Saudi Arabia",
          visibility: form.visibility,
          status: "published",
        }),
        headers: bearerHeaders(token),
      })

      setCreatedClub(club)
      setForm({
        name: "",
        description: "",
        city: form.city,
        country: form.country,
        visibility: "public",
      })
    } catch (submitError) {
      console.error("Club creation failed.", submitError)
      setError(submitError instanceof Error ? submitError.message : "Club creation failed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-primary">Club setup</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Create a club</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Any signed-in user can create a club. You become the owner and can publish events for it.
          </p>
        </div>
        <Link
          href="/organizer/events/new"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background/50 px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-primary/50 hover:text-primary"
        >
          <Building2 className="size-3.5 text-primary" aria-hidden="true" />
          Add event
        </Link>
      </div>

      {error && (
        <div className="mt-5 flex gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}

      {createdClub && (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/10 p-4 text-sm">
          <span className="inline-flex items-center gap-2 text-primary">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            {createdClub.name} is ready.
          </span>
          <Link href="/organizer/events/new" className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">
            Add first event
          </Link>
        </div>
      )}

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <Field label="Club name" className="lg:col-span-2">
          <input
            value={form.name}
            onChange={(event) => updateField("name", event.target.value)}
            placeholder="Istanbul Sports Circle"
            className={inputClassName}
            required
          />
        </Field>

        <Field label="Description" className="lg:col-span-2">
          <textarea
            value={form.description}
            onChange={(event) => updateField("description", event.target.value)}
            placeholder="Describe who this club is for and what kind of events it hosts."
            className={cn(inputClassName, "min-h-28 resize-y py-3")}
          />
        </Field>

        <Field label="City">
          <input
            list="club-city-suggestions"
            value={form.city}
            onChange={(event) => updateField("city", event.target.value)}
            placeholder="Start typing, e.g. ist"
            className={inputClassName}
          />
          <datalist id="club-city-suggestions">
            {CITY_SUGGESTIONS.map((city) => (
              <option key={city} value={city} />
            ))}
          </datalist>
        </Field>

        <Field label="Country">
          <input
            value={form.country}
            onChange={(event) => updateField("country", event.target.value)}
            className={inputClassName}
          />
        </Field>

        <Field label="Visibility">
          <select value={form.visibility} onChange={(event) => updateField("visibility", event.target.value)} className={inputClassName}>
            <option value="public">Public</option>
            <option value="private">Private</option>
          </select>
        </Field>
      </div>

      <div className="mt-6 flex justify-end border-t border-border pt-5">
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Building2 className="size-4" aria-hidden="true" />}
          {submitting ? "Creating" : "Create club"}
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
