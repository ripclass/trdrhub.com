/**
 * TrackingMap Component
 * 
 * Interactive map showing shipment locations and routes using Leaflet (free).
 */

import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Ship, Container, Anchor, Navigation } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

// Fix Leaflet default marker icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom ship marker icon
const createShipIcon = (status: string) => {
  const color = status === 'delayed' ? '#ef4444' : 
                status === 'delivered' ? '#22c55e' : 
                status === 'at_port' ? '#f59e0b' : '#3b82f6';
  
  return L.divIcon({
    className: 'custom-ship-marker',
    html: `
      <div style="
        width: 32px;
        height: 32px;
        background: ${color};
        border: 2px solid white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1 .6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>
          <path d="M19.38 20A11.6 11.6 0 0 0 21 14l-9-4-9 4c0 2.9.94 5.34 2.81 7.76"/>
          <path d="M19 13V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6"/>
          <path d="M12 10v4"/>
          <path d="M12 2v3"/>
        </svg>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
};

// Port marker icon
const portIcon = L.divIcon({
  className: 'custom-port-marker',
  html: `
    <div style="
      width: 24px;
      height: 24px;
      background: #6366f1;
      border: 2px solid white;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    ">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="5" r="3"/>
        <line x1="12" y1="22" x2="12" y2="8"/>
        <path d="M5 12H2a10 10 0 0 0 20 0h-3"/>
      </svg>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -12],
});

export interface ShipmentLocation {
  id: string;
  reference: string;
  type: 'container' | 'vessel';
  status: string;
  latitude: number;
  longitude: number;
  vessel_name?: string;
  carrier?: string;
  origin?: string;
  destination?: string;
  eta?: string;
  progress?: number;
}

export interface PortLocation {
  name: string;
  code: string;
  latitude: number;
  longitude: number;
  type: 'origin' | 'destination' | 'waypoint';
}

export interface RouteData {
  coordinates: [number, number][];
  color?: string;
}

interface TrackingMapProps {
  shipments?: ShipmentLocation[];
  ports?: PortLocation[];
  routes?: RouteData[];
  selectedShipmentId?: string;
  onShipmentClick?: (shipment: ShipmentLocation) => void;
  height?: string | number;
  center?: [number, number];
  zoom?: number;
  className?: string;
}

// Component to fit bounds when data changes
function FitBounds({ shipments, ports }: { shipments?: ShipmentLocation[], ports?: PortLocation[] }) {
  const map = useMap();
  
  useEffect(() => {
    const points: [number, number][] = [];
    
    shipments?.forEach(s => {
      if (s.latitude && s.longitude) {
        points.push([s.latitude, s.longitude]);
      }
    });
    
    ports?.forEach(p => {
      if (p.latitude && p.longitude) {
        points.push([p.latitude, p.longitude]);
      }
    });
    
    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 6 });
    }
  }, [map, shipments, ports]);
  
  return null;
}

export default function TrackingMap({
  shipments = [],
  ports = [],
  routes = [],
  selectedShipmentId,
  onShipmentClick,
  height = 400,
  center = [20, 0],
  zoom = 2,
  className = '',
}: TrackingMapProps) {
  const mapRef = useRef<L.Map>(null);

  return (
    <div className={`relative ${className}`} style={{ height }}>
      <MapContainer
        ref={mapRef}
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }}
        scrollWheelZoom={true}
        zoomControl={true}
      >
        {/* Dark theme map tiles from CartoDB */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        {/* Route lines */}
        {routes.map((route, idx) => (
          <Polyline
            key={`route-${idx}`}
            positions={route.coordinates}
            pathOptions={{
              color: route.color || '#3b82f6',
              weight: 3,
              opacity: 0.7,
              dashArray: '10, 10',
            }}
          />
        ))}
        
        {/* Port markers */}
        {ports.map((port) => (
          <Marker
            key={`port-${port.code}`}
            position={[port.latitude, port.longitude]}
            icon={portIcon}
          >
            <Popup>
              <div className="p-2 min-w-[150px]">
                <div className="flex items-center gap-2 mb-1">
                  <Anchor className="w-4 h-4 text-indigo-500" />
                  <span className="font-semibold">{port.name}</span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">{port.code}</span>
                <Badge variant="outline" className="ml-2 text-xs">
                  {port.type}
                </Badge>
              </div>
            </Popup>
          </Marker>
        ))}
        
        {/* Shipment markers */}
        {shipments.map((shipment) => (
          <Marker
            key={shipment.id}
            position={[shipment.latitude, shipment.longitude]}
            icon={createShipIcon(shipment.status)}
            eventHandlers={{
              click: () => onShipmentClick?.(shipment),
            }}
          >
            <Popup>
              <div className="p-2 min-w-[200px]">
                <div className="flex items-center gap-2 mb-2">
                  {shipment.type === 'container' ? (
                    <Container className="w-4 h-4 text-blue-500" />
                  ) : (
                    <Ship className="w-4 h-4 text-blue-500" />
                  )}
                  <span className="font-mono font-semibold">{shipment.reference}</span>
                </div>
                
                {shipment.vessel_name && (
                  <p className="text-sm text-muted-foreground mb-1">
                    {shipment.vessel_name}
                  </p>
                )}
                
                <div className="space-y-1 text-xs">
                  {shipment.origin && (
                    <p><span className="text-muted-foreground">From:</span> {shipment.origin}</p>
                  )}
                  {shipment.destination && (
                    <p><span className="text-muted-foreground">To:</span> {shipment.destination}</p>
                  )}
                  {shipment.eta && (
                    <p><span className="text-muted-foreground">ETA:</span> {new Date(shipment.eta).toLocaleDateString()}</p>
                  )}
                </div>
                
                <div className="mt-2 pt-2 border-t">
                  <Link 
                    to={`/tracking/dashboard/${shipment.type}/${shipment.reference}`}
                    className="text-blue-500 hover:underline text-xs"
                  >
                    View Details →
                  </Link>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
        
        {/* Auto-fit bounds */}
        <FitBounds shipments={shipments} ports={ports} />
      </MapContainer>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-background/90 backdrop-blur-sm rounded-lg p-3 text-xs shadow-lg z-[1000]">
        <p className="font-semibold mb-2">Legend</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span>In Transit</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span>At Port</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span>Delayed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span>Delivered</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-indigo-500" />
            <span>Port</span>
          </div>
        </div>
      </div>
    </div>
  );
}

