export type EventCategory = "Outdoors" | "Craft" | "Social" | "Sports" | "Music" | "Wellness" | "Food"

export type EventWhen = "Today" | "This week" | "This weekend"

export type OrgVideo = {
  title: string
  duration: string
  poster: string
}

export type Organizer = {
  id: string
  name: string
  handle: string
  logo: string
  verified: boolean
  bio: string
  members: number
  eventsHosted: number
  rating: number
  socials: {
    instagram?: string
    youtube?: string
    website?: string
  }
  reel: OrgVideo[]
}

export type CommunityEvent = {
  id: string
  title: string
  blurb: string
  about: string
  category: EventCategory
  when: EventWhen
  date: string
  duration: string
  location: string
  address: string
  city: string
  lat: number
  lng: number
  spots: number
  price: number // 0 = free
  attendees: number
  trending: boolean
  image: string
  highlights: string[]
  bring: string[]
  organizerId: string
}

export const CATEGORIES: EventCategory[] = [
  "Outdoors",
  "Craft",
  "Social",
  "Sports",
  "Music",
  "Wellness",
  "Food",
]

export const WHENS: EventWhen[] = ["Today", "This week", "This weekend"]

export const ORGANIZERS: Record<string, Organizer> = {
  trailheads: {
    id: "trailheads",
    name: "Trailheads SF",
    handle: "@trailheads",
    logo: "/orgs/trailheads.png",
    verified: true,
    bio: "We run small-group hikes and overnight trips around the Bay. No drop-offs, no egos — just good trails and good people.",
    members: 2480,
    eventsHosted: 142,
    rating: 4.9,
    socials: { instagram: "trailheads.sf", youtube: "trailheadssf", website: "trailheads.club" },
    reel: [
      { title: "Mt. Tam Summit Trip", duration: "2:14", poster: "/orgs/reel-trail-1.png" },
      { title: "Alpine Lake Overnighter", duration: "3:48", poster: "/orgs/reel-trail-2.png" },
      { title: "Headlands at Dawn", duration: "1:32", poster: "/experiences/sunrise-hike.png" },
    ],
  },
  kiln: {
    id: "kiln",
    name: "Kiln Collective",
    handle: "@kilncollective",
    logo: "/orgs/kiln-collective.png",
    verified: true,
    bio: "A community ceramics studio. We host beginner-friendly throwing nights and seasonal glaze workshops.",
    members: 860,
    eventsHosted: 96,
    rating: 4.8,
    socials: { instagram: "kiln.collective", website: "kilncollective.studio" },
    reel: [
      { title: "First Bowl Night", duration: "1:58", poster: "/experiences/pottery-night.png" },
      { title: "Glaze & Fire Day", duration: "2:40", poster: "/orgs/reel-trail-2.png" },
    ],
  },
  pace: {
    id: "pace",
    name: "Pace Society",
    handle: "@pacesociety",
    logo: "/orgs/pace-society.png",
    verified: true,
    bio: "An all-paces run club. We meet, we move, we get a drink after. Everyone finishes together.",
    members: 5120,
    eventsHosted: 311,
    rating: 4.9,
    socials: { instagram: "pace.society", youtube: "pacesociety", website: "pacesociety.run" },
    reel: [
      { title: "Bridge Run Recap", duration: "1:12", poster: "/experiences/run-club.png" },
      { title: "Sunset 10k", duration: "2:05", poster: "/experiences/yoga.png" },
    ],
  },
  commons: {
    id: "commons",
    name: "The Commons",
    handle: "@thecommons",
    logo: "/orgs/trailheads.png",
    verified: false,
    bio: "Supper clubs, book nights, and gatherings for people who'd rather meet in person than online.",
    members: 1740,
    eventsHosted: 78,
    rating: 4.7,
    socials: { instagram: "the.commons", website: "thecommons.social" },
    reel: [
      { title: "Rooftop Supper Vol. 4", duration: "2:22", poster: "/experiences/supper-club.png" },
      { title: "Corner Book Club", duration: "1:40", poster: "/experiences/book-club.png" },
    ],
  },
}

export const EVENTS: CommunityEvent[] = [
  {
    id: "sunrise-ridge-hike",
    title: "Sunrise Ridge Hike",
    blurb: "Catch first light from the headlands with a small crew of early risers.",
    about:
      "We meet in the dark, climb the ridge by headlamp, and reach the lookout just as the sun breaks over the bay. It's a moderate 4-mile loop with one steady climb. We keep the group small so nobody gets left behind, and we hang at the top for coffee and photos before heading down together.",
    category: "Outdoors",
    when: "This weekend",
    date: "Sat, 6:00 AM",
    duration: "3 hours",
    location: "Marin Headlands",
    address: "Conzelman Rd, Sausalito, CA",
    city: "San Francisco",
    lat: 37.8266,
    lng: -122.4995,
    spots: 6,
    price: 0,
    attendees: 18,
    trending: true,
    image: "/experiences/sunrise-hike.png",
    highlights: ["Beginner friendly pace", "Sunrise viewpoint", "Coffee at the top"],
    bring: ["Headlamp", "Water", "Layers"],
    organizerId: "trailheads",
  },
  {
    id: "hands-and-clay",
    title: "Hands & Clay Pottery",
    blurb: "Throw your first bowl over a glass of wine. No experience needed.",
    about:
      "An relaxed, hands-on intro to the pottery wheel. Our instructors walk you through centering, pulling, and shaping your first piece. We fire and glaze your bowl afterwards and you pick it up the following week. Wine and snacks included.",
    category: "Craft",
    when: "This week",
    date: "Thu, 7:30 PM",
    duration: "2 hours",
    location: "East Side Studio",
    address: "2841 Bryant St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7515,
    lng: -122.4094,
    spots: 4,
    price: 32,
    attendees: 12,
    trending: true,
    image: "/experiences/pottery-night.png",
    highlights: ["All materials included", "Wine & snacks", "Take home your piece"],
    bring: ["Clothes you can mess up"],
    organizerId: "kiln",
  },
  {
    id: "strangers-supper",
    title: "Strangers Supper Club",
    blurb: "A long table, six strangers, one unforgettable rooftop dinner.",
    about:
      "Six seats, six strangers, one shared meal under the stars. A chef-prepared three-course dinner, a few conversation prompts to break the ice, and a rooftop view of the city. You'll arrive not knowing anyone and leave with new friends.",
    category: "Social",
    when: "This weekend",
    date: "Fri, 8:00 PM",
    duration: "3 hours",
    location: "Rooftop, Downtown",
    address: "388 Market St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7929,
    lng: -122.3971,
    spots: 12,
    price: 24,
    attendees: 40,
    trending: true,
    image: "/experiences/supper-club.png",
    highlights: ["Three-course dinner", "Rooftop city views", "Curated table of six"],
    bring: ["An open mind"],
    organizerId: "commons",
  },
  {
    id: "bridge-run-club",
    title: "Golden Hour Run Club",
    blurb: "An easy 5k across the bridge, then drinks for whoever's up for it.",
    about:
      "Our flagship weekly run. We gather at Crissy Field, warm up together, and run an easy 5k out toward the bridge at golden hour. All paces welcome — we have sweepers at the back so nobody runs alone. Drinks after for anyone who wants to stick around.",
    category: "Sports",
    when: "Today",
    date: "Today, 6:30 PM",
    duration: "1.5 hours",
    location: "Crissy Field",
    address: "1199 East Beach, San Francisco, CA",
    city: "San Francisco",
    lat: 37.8043,
    lng: -122.4659,
    spots: 20,
    price: 0,
    attendees: 64,
    trending: true,
    image: "/experiences/run-club.png",
    highlights: ["All paces welcome", "Sweepers at the back", "Optional drinks after"],
    bring: ["Running shoes", "Water"],
    organizerId: "pace",
  },
  {
    id: "boulder-night",
    title: "Beginner Bouldering Night",
    blurb: "Climb, fall, laugh, repeat. Shoes and stoke provided.",
    about:
      "A welcoming intro to indoor bouldering. We cover the basics of movement and falling safely, then spend the night working easy problems as a group. Rental shoes are included. Total beginners are exactly who this is for.",
    category: "Sports",
    when: "This week",
    date: "Wed, 7:00 PM",
    duration: "2 hours",
    location: "Mission Cliffs",
    address: "2295 Harrison St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7607,
    lng: -122.4127,
    spots: 8,
    price: 18,
    attendees: 22,
    trending: false,
    image: "/experiences/climbing.png",
    highlights: ["Rental shoes included", "Beginner coaching", "Small group"],
    bring: ["Comfortable clothes"],
    organizerId: "pace",
  },
  {
    id: "corner-book-club",
    title: "Corner Cafe Book Club",
    blurb: "This month: a short story collection and a lot of strong coffee.",
    about:
      "A laid-back monthly book club in the back corner of our favorite cafe. This month we're reading a short story collection — read as much or as little as you like, the conversation is the point. New faces always welcome.",
    category: "Social",
    when: "This week",
    date: "Tue, 6:00 PM",
    duration: "1.5 hours",
    location: "Maple & Vine Cafe",
    address: "1058 Valencia St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7563,
    lng: -122.4213,
    spots: 5,
    price: 0,
    attendees: 15,
    trending: false,
    image: "/experiences/book-club.png",
    highlights: ["No pressure to finish", "Strong coffee", "Friendly regulars"],
    bring: ["The book (or not)"],
    organizerId: "commons",
  },
  {
    id: "basement-jam",
    title: "Basement Live Jam",
    blurb: "Intimate live set from local artists. Bring an instrument or just vibe.",
    about:
      "An intimate basement session featuring rotating local artists. Open jam in the second half — bring an instrument and sit in, or just soak up the music. BYOB, low lights, good people.",
    category: "Music",
    when: "This weekend",
    date: "Sat, 9:00 PM",
    duration: "3 hours",
    location: "The Underground",
    address: "550 Barneveld Ave, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7385,
    lng: -122.4035,
    spots: 30,
    price: 15,
    attendees: 88,
    trending: true,
    image: "/experiences/live-music.png",
    highlights: ["Live local artists", "Open jam session", "BYOB"],
    bring: ["An instrument (optional)"],
    organizerId: "commons",
  },
  {
    id: "park-sunrise-yoga",
    title: "Park Sunrise Yoga",
    blurb: "Start your day grounded with a slow flow on the grass.",
    about:
      "A gentle morning flow on the grass at Dolores Park. Suitable for every body and every level. We move slowly, breathe deeply, and finish with a few quiet minutes in the sun. Mats available to borrow.",
    category: "Wellness",
    when: "Today",
    date: "Today, 7:00 AM",
    duration: "1 hour",
    location: "Dolores Park",
    address: "Dolores St & 19th St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7596,
    lng: -122.4269,
    spots: 14,
    price: 0,
    attendees: 31,
    trending: false,
    image: "/experiences/yoga.png",
    highlights: ["All levels welcome", "Mats to borrow", "Outdoor in the park"],
    bring: ["A mat (or borrow one)", "Water"],
    organizerId: "trailheads",
  },
  {
    id: "night-food-crawl",
    title: "Night Street Food Crawl",
    blurb: "Five stalls, five bites, one delicious wander through the night market.",
    about:
      "A guided crawl through the night market. We hit five hand-picked stalls for five tasting bites, with a local host sharing the story behind each one. Come hungry and ready to wander.",
    category: "Food",
    when: "This weekend",
    date: "Fri, 7:00 PM",
    duration: "2.5 hours",
    location: "Night Market",
    address: "Larkin St, San Francisco, CA",
    city: "San Francisco",
    lat: 37.7846,
    lng: -122.4179,
    spots: 10,
    price: 28,
    attendees: 47,
    trending: true,
    image: "/experiences/food-crawl.png",
    highlights: ["Five tasting bites", "Local host", "Hidden gems"],
    bring: ["An appetite"],
    organizerId: "commons",
  },
]

export function getEventById(id: string): CommunityEvent | undefined {
  return EVENTS.find((e) => e.id === id)
}

export function getOrganizer(id: string): Organizer | undefined {
  return ORGANIZERS[id]
}

export function getEventsByOrganizer(organizerId: string, excludeId?: string): CommunityEvent[] {
  return EVENTS.filter((e) => e.organizerId === organizerId && e.id !== excludeId)
}
