"use client"

import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet"
import "leaflet/dist/leaflet.css"

export default function EventMap({
  lat,
  lng,
  label,
}: {
  lat: number
  lng: number
  label: string
}) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={14}
      scrollWheelZoom={false}
      className="size-full"
      style={{ background: "oklch(0.16 0.02 280)" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <CircleMarker
        center={[lat, lng]}
        radius={11}
        pathOptions={{
          color: "oklch(0.7 0.18 300)",
          fillColor: "oklch(0.7 0.18 300)",
          fillOpacity: 0.9,
          weight: 3,
        }}
      >
        <Tooltip direction="top" offset={[0, -8]} opacity={1}>
          {label}
        </Tooltip>
      </CircleMarker>
    </MapContainer>
  )
}
