import { SignUp } from "@clerk/nextjs"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Create account - COMMUNITI",
}

export default function AuthPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4 py-16">
      <SignUp
        appearance={{
          elements: {
            cardBox: "rounded-2xl border border-border shadow-2xl",
            headerTitle: "text-foreground",
            headerSubtitle: "text-muted-foreground",
          },
        }}
      />
    </main>
  )
}
