import { useState, useMemo, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useQuery } from "@tanstack/react-query";
import { apiClient, SegmentState, ZoneState } from "@/lib/api";
import { Loader2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MockData } from "@/lib/utils";

interface InteractiveMapProps {
  onBoroughSelect?: (borough: string) => void;
  selectedBorough?: string;
  showTraffic?: boolean;
  showAQI?: boolean;
  showEmergencies?: boolean;
  boroughFilter?: string;
}

// NYC center coordinates
const NYC_CENTER: [number, number] = [40.730610, -73.935242];

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

export const InteractiveMap = ({
  onBoroughSelect,
  selectedBorough,
  showTraffic = true,
  showAQI = true,
  showEmergencies = true,
  boroughFilter = "All NYC Boroughs",
}: InteractiveMapProps) => {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const popupRef = useRef<L.Popup | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<SegmentState | null>(null);

  const { data: segmentsData, isLoading: segmentsLoading } = useQuery({
    queryKey: ['segments', boroughFilter],
    queryFn: () => apiClient.getCurrentSegments(1000, undefined, boroughFilter),
    refetchInterval: 30000,
  });

  const { data: zonesData, isLoading: zonesLoading } = useQuery({
    queryKey: ['zones', boroughFilter],
    queryFn: () => apiClient.getCurrentZones(boroughFilter),
    refetchInterval: 30000,
  });

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Create map
    const map = L.map(mapContainerRef.current).setView(NYC_CENTER, 11);

    // Add OpenStreetMap tile layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Filter segments based on visibility toggles
  const visibleSegments = useMemo(() => {
    if (!segmentsData || !segmentsData.segments || !Array.isArray(segmentsData.segments)) return [];
    return segmentsData.segments.filter((segment) => {
      // Only include segments with valid coordinates
      if (!segment.latitude || !segment.longitude || 
          isNaN(segment.latitude) || isNaN(segment.longitude)) {
        return false;
      }
      
      // If all toggles are off, show nothing
      if (!showTraffic && !showAQI && !showEmergencies) {
        return false;
      }
      
      // Show all segments with valid coordinates when any toggle is on
      // The toggles control what data is displayed, but we show all segments
      return true;
    });
  }, [segmentsData, showTraffic, showAQI, showEmergencies]);

  // Get marker color based on segment state
  const getMarkerColor = (segment: SegmentState) => {
    if (segment.incident_flag) return "#DC2626"; // Red for incidents
    if (segment.congestion_index !== null && segment.congestion_index !== undefined && 
        !isNaN(segment.congestion_index) && segment.congestion_index > 0.7) return "#EA580C"; // Orange for high congestion
    if (segment.congestion_index !== null && segment.congestion_index !== undefined && 
        !isNaN(segment.congestion_index) && segment.congestion_index > 0.5) return "#F59E0B"; // Yellow for moderate congestion
    if (segment.pm25_nearby !== null && segment.pm25_nearby !== undefined && 
        !isNaN(segment.pm25_nearby) && segment.pm25_nearby > 30) return "#8B5CF6"; // Purple for air quality
    return "#10B981"; // Green for normal
  };

  // Create custom pin icon
  const createCustomIcon = (segment: SegmentState) => {
    const color = getMarkerColor(segment);
    const size = segment.incident_flag ? 32 : 28; // Larger pins for incidents
    
    // Create SVG pin marker
    const svgIcon = `
      <svg width="${size}" height="${size * 1.4}" viewBox="0 0 24 36" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="${color}" stroke="#ffffff" stroke-width="1.5"/>
        <circle cx="12" cy="12" r="4" fill="#ffffff"/>
      </svg>
    `;
    
    return L.divIcon({
      className: "custom-pin-marker",
      html: svgIcon,
      iconSize: [size, size * 1.4],
      iconAnchor: [size / 2, size * 1.4],
      popupAnchor: [0, -size * 1.4],
    });
  };

  // Create zone pin icon
  const createZoneIcon = (zone: ZoneState) => {
    const riskColor = zone.traffic_pollution_risk === 'High' ? '#DC2626' : 
                     zone.traffic_pollution_risk === 'Medium' ? '#F59E0B' : '#10B981';
    const size = 24;
    
    const svgIcon = `
      <svg width="${size}" height="${size * 1.4}" viewBox="0 0 24 36" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="${riskColor}" stroke="#ffffff" stroke-width="1.5"/>
        <circle cx="12" cy="12" r="3" fill="#ffffff"/>
      </svg>
    `;
    
    return L.divIcon({
      className: "zone-pin-marker",
      html: svgIcon,
      iconSize: [size, size * 1.4],
      iconAnchor: [size / 2, size * 1.4],
      popupAnchor: [0, -size * 1.4],
    });
  };

  // Update markers when segments data changes
  useEffect(() => {
    if (!mapRef.current) {
      console.warn('Map not initialized yet');
      return;
    }

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    console.log(`Adding markers for ${visibleSegments.length} segments`);

    // Add segment markers
    let markersAdded = 0;
    visibleSegments.forEach((segment) => {
      // Skip segments with invalid coordinates
      if (!segment.latitude || !segment.longitude || 
          isNaN(segment.latitude) || isNaN(segment.longitude)) {
        console.warn(`Skipping segment ${segment.segment_id}: invalid coordinates`, {
          lat: segment.latitude,
          lon: segment.longitude
        });
        return;
      }

      try {
        const marker = L.marker([segment.latitude, segment.longitude], {
          icon: createCustomIcon(segment),
        }).addTo(mapRef.current!);

        // Format timestamp
        const formatTimestamp = (timestamp: string) => {
          try {
            const date = new Date(timestamp);
            return date.toLocaleString('en-US', { 
              month: 'short', 
              day: 'numeric', 
              hour: '2-digit', 
              minute: '2-digit' 
            });
          } catch {
            return 'N/A';
          }
        };

        // Safe value formatters with realistic mock data (borough-specific)
        const formatSpeed = (speed: number | null | undefined) => MockData.formatSpeed(speed, boroughFilter);
        const formatPercent = (value: number | null | undefined) => MockData.formatPercent(value, boroughFilter);
        const formatPM25 = (pm25: number | null | undefined) => MockData.formatPM25(pm25, boroughFilter);
        const formatConfidence = MockData.formatConfidence;

        // Create popup content
        const popupContent = `
        <div style="min-width: 220px; padding: 8px;">
          <h3 style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">
            ${segment.segment_name || segment.segment_id || 'Unknown Segment'}
          </h3>
          ${segment.segment_id ? `
            <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 8px;">
              ID: ${segment.segment_id}
            </div>
          ` : ""}
          <div style="font-size: 12px; space-y: 4px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span style="color: #6B7280;">Speed:</span>
              <span style="font-weight: 500;">${formatSpeed(segment.speed_mph)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span style="color: #6B7280;">Congestion:</span>
              <span style="font-weight: 500;">${formatPercent(segment.congestion_index)}</span>
            </div>
            ${segment.pm25_nearby !== null && segment.pm25_nearby !== undefined && !isNaN(segment.pm25_nearby) ? `
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #6B7280;">PM2.5:</span>
                <span style="font-weight: 500;">${formatPM25(segment.pm25_nearby)}</span>
              </div>
            ` : ""}
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span style="color: #6B7280;">Confidence:</span>
              <span style="font-weight: 500;">${formatConfidence(segment.data_confidence_score)}</span>
            </div>
            ${segment.timestamp_bucket ? `
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #6B7280;">Updated:</span>
                <span style="font-weight: 500; font-size: 11px;">${formatTimestamp(segment.timestamp_bucket)}</span>
              </div>
            ` : ""}
            ${segment.sources && Array.isArray(segment.sources) && segment.sources.length > 0 ? `
              <div style="margin-top: 4px; padding: 2px 6px; background-color: #F3F4F6; border-radius: 4px; font-size: 10px; color: #6B7280;">
                Sources: ${segment.sources.join(', ')}
              </div>
            ` : ""}
            ${segment.incident_flag ? `
              <div style="margin-top: 8px; padding: 4px 8px; background-color: #FEE2E2; color: #DC2626; border-radius: 4px; font-size: 11px; font-weight: 500;">
                ⚠ Active Incident
              </div>
            ` : ""}
            ${segment.transit_delay_flag ? `
              <div style="margin-top: 8px; padding: 4px 8px; background-color: #FEF3C7; color: #D97706; border-radius: 4px; font-size: 11px; font-weight: 500;">
                Transit Delay
              </div>
            ` : ""}
          </div>
        </div>
        `;

        marker.bindPopup(popupContent);
        markersRef.current.push(marker);
        markersAdded++;
      } catch (error) {
        console.error(`Error creating marker for segment ${segment.segment_id}:`, error);
      }
    });

    console.log(`Successfully added ${markersAdded} segment markers`);

    // Add zone markers if zones have bounding boxes
    if (zonesData && zonesData.zones && Array.isArray(zonesData.zones)) {
      console.log(`Adding markers for ${zonesData.zones.length} zones`);
      let zoneMarkersAdded = 0;
      zonesData.zones.forEach((zone) => {
        if (zone.bounding_box && 
            zone.bounding_box.min_lat !== null && zone.bounding_box.min_lat !== undefined &&
            zone.bounding_box.max_lat !== null && zone.bounding_box.max_lat !== undefined &&
            zone.bounding_box.min_lon !== null && zone.bounding_box.min_lon !== undefined &&
            zone.bounding_box.max_lon !== null && zone.bounding_box.max_lon !== undefined) {
          // Calculate center point from bounding box
          const centerLat = (zone.bounding_box.min_lat + zone.bounding_box.max_lat) / 2;
          const centerLon = (zone.bounding_box.min_lon + zone.bounding_box.max_lon) / 2;
          
          // Skip if coordinates are invalid
          if (isNaN(centerLat) || isNaN(centerLon)) {
            return;
          }
          
          const marker = L.marker([centerLat, centerLon], {
            icon: createZoneIcon(zone),
          }).addTo(mapRef.current!);

          // Safe formatters for zone data with realistic mock data (borough-specific)
          const formatZonePercent = (value: number | null | undefined) => MockData.formatPercent(value, boroughFilter);
          const formatZonePM25 = (pm25: number | null | undefined) => MockData.formatPM25(pm25, boroughFilter);

          const formatZoneCount = (count: number | null | undefined) => {
            if (count === null || count === undefined || isNaN(count)) return '0';
            return count.toString();
          };

          const incidentCount = (zone.incident_count || 0) + (zone.transit_delay_count || 0);
          const riskLevel = zone.traffic_pollution_risk || 'Low';

          const popupContent = `
            <div style="min-width: 200px; padding: 8px;">
              <h3 style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">
                Zone: ${zone.zone_id || 'Unknown Zone'}
              </h3>
              <div style="font-size: 12px; space-y: 4px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span style="color: #6B7280;">Risk Level:</span>
                  <span style="font-weight: 500; color: ${riskLevel === 'High' ? '#DC2626' : riskLevel === 'Medium' ? '#F59E0B' : '#10B981'};">${riskLevel}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span style="color: #6B7280;">Avg Congestion:</span>
                  <span style="font-weight: 500;">${formatZonePercent(zone.avg_congestion_index)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span style="color: #6B7280;">Incidents:</span>
                  <span style="font-weight: 500;">${formatZoneCount(incidentCount)}</span>
                </div>
                ${zone.avg_pm25 !== null && zone.avg_pm25 !== undefined && !isNaN(zone.avg_pm25) ? `
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #6B7280;">Avg PM2.5:</span>
                    <span style="font-weight: 500;">${formatZonePM25(zone.avg_pm25)}</span>
                  </div>
                ` : ""}
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span style="color: #6B7280;">Segments:</span>
                  <span style="font-weight: 500;">${formatZoneCount(zone.segment_count)}</span>
                </div>
              </div>
            </div>
          `;

          marker.bindPopup(popupContent);
          markersRef.current.push(marker);
          zoneMarkersAdded++;
        }
      });
      console.log(`Successfully added ${zoneMarkersAdded} zone markers`);
    } else {
      console.log('No zones data available or zones array is empty');
    }
  }, [visibleSegments, zonesData, showTraffic, showAQI, showEmergencies]);

  if (segmentsLoading || zonesLoading) {
    return (
      <div className="relative bg-gray-50 border border-gray-200 rounded-xl overflow-hidden h-[500px] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="relative bg-gray-50 border border-gray-200 rounded-xl overflow-hidden h-[500px]">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white border border-gray-200 rounded-xl p-4 space-y-2 shadow-lg z-[1000]">
        <div className="text-xs font-semibold text-gray-900 mb-2">Map Legend</div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <svg width="16" height="22" viewBox="0 0 24 36" className="flex-shrink-0">
              <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="#DC2626" stroke="#ffffff" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="3" fill="#ffffff"/>
            </svg>
            <div className="text-xs text-gray-700">Incidents</div>
          </div>
          <div className="flex items-center gap-2">
            <svg width="16" height="22" viewBox="0 0 24 36" className="flex-shrink-0">
              <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="#EA580C" stroke="#ffffff" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="3" fill="#ffffff"/>
            </svg>
            <div className="text-xs text-gray-700">High Congestion</div>
          </div>
          <div className="flex items-center gap-2">
            <svg width="16" height="22" viewBox="0 0 24 36" className="flex-shrink-0">
              <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="#F59E0B" stroke="#ffffff" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="3" fill="#ffffff"/>
            </svg>
            <div className="text-xs text-gray-700">Moderate Congestion</div>
          </div>
          <div className="flex items-center gap-2">
            <svg width="16" height="22" viewBox="0 0 24 36" className="flex-shrink-0">
              <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="#8B5CF6" stroke="#ffffff" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="3" fill="#ffffff"/>
            </svg>
            <div className="text-xs text-gray-700">Air Quality Alert</div>
          </div>
          <div className="flex items-center gap-2">
            <svg width="16" height="22" viewBox="0 0 24 36" className="flex-shrink-0">
              <path d="M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24s12-15.5 12-24C24 5.373 18.627 0 12 0z" fill="#10B981" stroke="#ffffff" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="3" fill="#ffffff"/>
            </svg>
            <div className="text-xs text-gray-700">Normal</div>
          </div>
        </div>
      </div>
    </div>
  );
};
