import { CircleMarker, MapContainer, Marker, Polyline, Rectangle, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { useStore } from "../../state/store";
import { hhmm, routeColor, routeDash, congColor } from "../../lib";
import type { S } from "../../api/client";

const dark = () => true; // Tempo is a dark control-room UI

function Fit({ bbox }: { bbox: [number, number, number, number] | undefined }) {
  const map = useMap();
  const key = bbox?.join(",");  // depend on the values: a new array each render must not re-fit (it resets the user's zoom)
  useEffect(() => { if (bbox) map.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]]); }, [key, map]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function Clicks({ onClick, onHover }: { onClick?: (lon: number, lat: number) => void; onHover?: (p: [number, number] | null) => void }) {
  useMapEvents({
    click: (e) => onClick?.(e.latlng.lng, e.latlng.lat),
    mousemove: (e) => onHover?.([e.latlng.lng, e.latlng.lat]),
    mouseout: () => onHover?.(null),
  });
  return null;
}

const depotIcon = L.divIcon({ className: "", html: '<div style="width:14px;height:14px;background:#f0b429;border:2px solid #0c0d0a;transform:rotate(45deg)"></div>', iconSize: [14, 14] });

/** Dashed ghost/fallback style when `dashed`; chevrons are approximated by arrowhead markers at segment midpoints. */
export function RouteLayer({ geometry, dashed = false, ghost = false }: { geometry: number[][][]; dashed?: boolean; ghost?: boolean }) {
  return (
    <>
      {geometry.map((g, i) => (
        <Polyline key={i} positions={g.map(([x, y]) => [y, x] as [number, number])}
          pathOptions={{ color: routeColor(i), weight: ghost ? 3 : 4, opacity: ghost ? 0.4 : 0.9, dashArray: dashed ? "8 6" : routeDash(i) }}>
          <Tooltip sticky>Vehicle {i + 1}</Tooltip>
        </Polyline>
      ))}
    </>
  );
}

export function CongestionLayer({ edges, faint = false }: { edges: S["CongestionEdge"][]; faint?: boolean }) {
  return (
    <>
      {edges.map((e, i) => (
        <Polyline key={i} positions={[[e.a[1], e.a[0]], [e.b[1], e.b[0]]]}
          pathOptions={faint ? { color: "#d9dec9", weight: e.road_class <= 2 ? 3 : 2, opacity: 0.45, interactive: false } : { color: congColor(e.ratio), weight: e.road_class <= 2 ? 4 : 2, opacity: 0.6 }} />
      ))}
    </>
  );
}

export function IncidentLayer({ edges, hover = false }: { edges: [number, number][][]; hover?: boolean }) {
  return (
    <>
      {edges.map((e, i) => (
        <Polyline key={i} positions={e.map(([x, y]) => [y, x] as [number, number])}
          pathOptions={hover ? { color: "#f0b429", weight: 7, opacity: 0.9, interactive: false } : { color: "#ff4d3d", weight: 8, opacity: 0.9, interactive: false }} />
      ))}
    </>
  );
}

export function VehicleMarker({ lon, lat, label, eta }: { lon: number; lat: number; label: string; eta: number }) {
  return (
    <CircleMarker center={[lat, lon]} radius={7} pathOptions={{ color: "#ff4d3d", fillColor: "#FFFFFF", fillOpacity: 1, weight: 3 }}>
      <Tooltip permanent direction="top">{label} · ETA {hhmm(eta)}</Tooltip>
    </CircleMarker>
  );
}

export default function MapView({ children, onClick, onHover }: { children?: React.ReactNode; onClick?: (lon: number, lat: number) => void; onHover?: (p: [number, number] | null) => void }) {
  const detail = useStore((s) => s.detail);
  const pts = detail ? [detail.depot, ...detail.customers.map((c) => [c.lon, c.lat] as [number, number])] : [];
  const bbox: [number, number, number, number] | undefined = pts.length
    ? [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))]
    : undefined;
  // CARTO basemaps now require an API key; OSM standard tiles are the keyless default.
  const url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const darkTiles = dark();
  return (
    <MapContainer center={[28.628, 77.209]} zoom={14} className="h-full w-full" zoomControl>
      <TileLayer url={url} className={darkTiles ? "tiles-dark" : ""} eventHandlers={{ tileerror: () => useStore.getState().set({ tilesOffline: true }), tileload: () => { if (useStore.getState().tilesOffline) useStore.getState().set({ tilesOffline: false }); } }} attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
      <Fit bbox={bbox} />
      <Clicks onClick={onClick} onHover={onHover} />
      {bbox && <Rectangle bounds={[[bbox[1], bbox[0]], [bbox[3], bbox[2]]]} pathOptions={{ color: "transparent", fillOpacity: 0, interactive: false }} />}
      {detail && <Marker position={[detail.depot[1], detail.depot[0]]} icon={depotIcon}><Tooltip>Depot</Tooltip></Marker>}
      {detail?.customers.map((c, i) => (
        <CircleMarker key={i} center={[c.lat, c.lon]} radius={3 + c.demand * 0.5} pathOptions={{ color: "#b8f04a", fillColor: "#0c0d0a", fillOpacity: 0.9, weight: 1.5 }}>
          <Tooltip>Customer {i + 1} · demand {c.demand}</Tooltip>
        </CircleMarker>
      ))}
      {children}
    </MapContainer>
  );
}

export function PointMarkers({ depot, points }: { depot: [number, number] | null; points: { lon: number; lat: number; demand: number }[] }) {
  return (
    <>
      {depot && <CircleMarker center={[depot[1], depot[0]]} radius={8} pathOptions={{ color: "#b8f04a", fillOpacity: 0.8 }}><Tooltip>New depot</Tooltip></CircleMarker>}
      {points.map((p, i) => <CircleMarker key={i} center={[p.lat, p.lon]} radius={5} pathOptions={{ color: "#b8f04a", fillOpacity: 0.4 }}><Tooltip>New customer {i + 1}</Tooltip></CircleMarker>)}
    </>
  );
}
