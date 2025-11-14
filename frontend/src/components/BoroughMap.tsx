import { useState, useMemo } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { InteractiveMap } from "./InteractiveMap";

interface BoroughMapProps {
  onBoroughSelect: (borough: string) => void;
  selectedBorough: string;
  boroughFilter?: string;
}

export const BoroughMap = ({ onBoroughSelect, selectedBorough, boroughFilter = "All NYC Boroughs" }: BoroughMapProps) => {
  const [showTraffic, setShowTraffic] = useState(true);
  const [showAQI, setShowAQI] = useState(true);
  const [showEmergencies, setShowEmergencies] = useState(true);

  const { data: zonesData, isLoading: zonesLoading } = useQuery({
    queryKey: ['zones', boroughFilter],
    queryFn: () => apiClient.getCurrentZones(boroughFilter),
    refetchInterval: 30000,
  });

  const { data: segmentsData, isLoading: segmentsLoading } = useQuery({
    queryKey: ['segments', boroughFilter],
    queryFn: () => apiClient.getCurrentSegments(1000, undefined, boroughFilter),
    refetchInterval: 30000,
  });

  // Calculate borough risk scores from zones and segments
  const boroughRiskScores = useMemo(() => {
    const defaultScores: Record<string, number> = {
      "Manhattan": 48,
      "Brooklyn": 62,
      "Queens": 71,
      "Bronx": 92,
      "Staten Island": 28,
    };

    if (!zonesData || !segmentsData) {
      return defaultScores;
    }

    // Calculate risk based on zones and segments
    // Risk = (congestion * 40) + (incidents * 30) + (AQI * 30)
    const scores: Record<string, { congestion: number; incidents: number; aqi: number; count: number }> = {};

    // Process zones - use traffic_pollution_risk and aggregated data
    zonesData.zones.forEach(zone => {
      // Use borough field if available, otherwise infer from zone_id
      let borough = zone.borough || "Manhattan"; // default
      if (!borough) {
        const zoneIdLower = zone.zone_id.toLowerCase();
        if (zoneIdLower.includes("bronx") || zoneIdLower.includes("bx")) borough = "Bronx";
        else if (zoneIdLower.includes("brooklyn") || zoneIdLower.includes("bk")) borough = "Brooklyn";
        else if (zoneIdLower.includes("queens") || zoneIdLower.includes("qn")) borough = "Queens";
        else if (zoneIdLower.includes("staten") || zoneIdLower.includes("si")) borough = "Staten Island";
      }

      if (!scores[borough]) {
        scores[borough] = { congestion: 0, incidents: 0, aqi: 0, count: 0 };
      }
      scores[borough].congestion += zone.avg_congestion_index;
      scores[borough].incidents += zone.incident_count + zone.transit_delay_count; // Use aggregated counts
      if (zone.avg_pm25) scores[borough].aqi += zone.avg_pm25;
      scores[borough].count += zone.segment_count; // Use segment_count as weight
    });

    // Process segments for more granular data
    segmentsData.segments.forEach(segment => {
      // Use borough field if available, otherwise infer from segment name
      let borough = segment.borough || "Manhattan";
      if (!borough) {
        const nameLower = segment.segment_name?.toLowerCase() || "";
        if (nameLower.includes("bronx") || nameLower.includes("bx")) borough = "Bronx";
        else if (nameLower.includes("brooklyn") || nameLower.includes("bk")) borough = "Brooklyn";
        else if (nameLower.includes("queens") || nameLower.includes("qn")) borough = "Queens";
        else if (nameLower.includes("staten") || nameLower.includes("si")) borough = "Staten Island";
      }

      if (!scores[borough]) {
        scores[borough] = { congestion: 0, incidents: 0, aqi: 0, count: 0 };
      }
      if (segment.congestion_index !== null && segment.congestion_index !== undefined && !isNaN(segment.congestion_index)) {
        scores[borough].congestion += segment.congestion_index;
      }
      if (segment.incident_flag) scores[borough].incidents += 1;
      if (segment.pm25_nearby !== null && segment.pm25_nearby !== undefined && !isNaN(segment.pm25_nearby)) {
        scores[borough].aqi += segment.pm25_nearby;
      }
      scores[borough].count += 1;
    });

    // Calculate final risk scores using zones' traffic_pollution_risk
    const finalScores: Record<string, number> = {};
    Object.keys(defaultScores).forEach(borough => {
      const data = scores[borough];
      if (data && data.count > 0) {
        const avgCongestion = data.congestion / Object.keys(zonesData.zones.filter(z => {
          const zoneIdLower = z.zone_id.toLowerCase();
          const boroughLower = borough.toLowerCase();
          return zoneIdLower.includes(boroughLower) || 
                 (borough === "Bronx" && (zoneIdLower.includes("bx"))) ||
                 (borough === "Brooklyn" && (zoneIdLower.includes("bk"))) ||
                 (borough === "Queens" && (zoneIdLower.includes("qn"))) ||
                 (borough === "Staten Island" && (zoneIdLower.includes("si") || zoneIdLower.includes("staten")));
        })).length || 1;
        
        const totalIncidents = data.incidents;
        const avgAQI = data.aqi / (data.count > 0 ? data.count : 1);
        
        // Get traffic pollution risk from zones
        const boroughZones = zonesData.zones.filter(z => {
          const zoneIdLower = z.zone_id.toLowerCase();
          const boroughLower = borough.toLowerCase();
          return zoneIdLower.includes(boroughLower) || 
                 (borough === "Bronx" && (zoneIdLower.includes("bx"))) ||
                 (borough === "Brooklyn" && (zoneIdLower.includes("bk"))) ||
                 (borough === "Queens" && (zoneIdLower.includes("qn"))) ||
                 (borough === "Staten Island" && (zoneIdLower.includes("si") || zoneIdLower.includes("staten")));
        });
        const highRiskZones = boroughZones.filter(z => z.traffic_pollution_risk === 'High').length;
        const pollutionRisk = highRiskZones > 0 ? 30 : boroughZones.filter(z => z.traffic_pollution_risk === 'Medium').length > 0 ? 15 : 5;
        
        // Risk score: 0-100 scale
        const risk = Math.min(100, Math.round(
          (avgCongestion * 40) + 
          (Math.min(1, totalIncidents / 10) * 30) + 
          pollutionRisk
        ));
        finalScores[borough] = risk;
      } else {
        finalScores[borough] = defaultScores[borough];
      }
    });

    return finalScores;
  }, [zonesData, segmentsData]);

  const getRiskColor = (risk: number) => {
    if (risk >= 86) return { color: "rgba(220, 38, 38, 0.25)", hoverColor: "rgba(220, 38, 38, 0.35)", stroke: "#DC2626" };
    if (risk >= 71) return { color: "rgba(234, 88, 12, 0.15)", hoverColor: "rgba(234, 88, 12, 0.25)", stroke: "#EA580C" };
    if (risk >= 51) return { color: "rgba(217, 119, 6, 0.15)", hoverColor: "rgba(217, 119, 6, 0.25)", stroke: "#D97706" };
    if (risk >= 31) return { color: "rgba(2, 132, 199, 0.15)", hoverColor: "rgba(2, 132, 199, 0.25)", stroke: "#0284C7" };
    return { color: "rgba(5, 150, 105, 0.15)", hoverColor: "rgba(5, 150, 105, 0.25)", stroke: "#059669" };
  };

  const boroughs = [
    {
      name: "Manhattan",
      path: "M 250,200 L 280,180 L 290,220 L 295,280 L 285,320 L 270,340 L 260,320 L 250,280 Z",
      labelX: 273,
      labelY: 260,
      risk: boroughRiskScores["Manhattan"] || 48
    },
    {
      name: "Brooklyn",
      path: "M 270,340 L 285,320 L 320,340 L 350,370 L 360,400 L 340,420 L 310,410 L 280,380 Z",
      labelX: 315,
      labelY: 375,
      risk: boroughRiskScores["Brooklyn"] || 62
    },
    {
      name: "Queens",
      path: "M 295,280 L 320,270 L 360,290 L 380,320 L 370,360 L 350,370 L 320,340 L 285,320 Z",
      labelX: 340,
      labelY: 315,
      risk: boroughRiskScores["Queens"] || 71
    },
    {
      name: "Bronx",
      path: "M 250,150 L 280,140 L 310,160 L 320,190 L 310,220 L 280,210 L 260,190 Z",
      labelX: 283,
      labelY: 175,
      risk: boroughRiskScores["Bronx"] || 92
    },
    {
      name: "Staten Island",
      path: "M 180,380 L 210,370 L 240,390 L 245,420 L 230,440 L 200,430 L 180,410 Z",
      labelX: 213,
      labelY: 405,
      risk: boroughRiskScores["Staten Island"] || 28
    }
  ].map(borough => ({
    ...borough,
    ...getRiskColor(borough.risk)
  }));

  if (zonesLoading || segmentsLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
        <div className="flex items-center justify-center h-[500px]">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Interactive Borough Map</h3>
          <p className="text-sm text-gray-600">
            Click any borough to view detailed metrics
          </p>
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-gray-600">Live</span>
        </div>
      </div>

      {/* Layer toggles */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => setShowTraffic(!showTraffic)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            showTraffic 
              ? "bg-blue-100 text-blue-700" 
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Traffic
        </button>
        <button
          onClick={() => setShowAQI(!showAQI)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            showAQI 
              ? "bg-blue-100 text-blue-700" 
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Air Quality
        </button>
        <button
          onClick={() => setShowEmergencies(!showEmergencies)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            showEmergencies 
              ? "bg-blue-100 text-blue-700" 
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Emergency
        </button>
      </div>

      {/* Interactive Map Container */}
      <InteractiveMap
        onBoroughSelect={onBoroughSelect}
        selectedBorough={selectedBorough}
        showTraffic={showTraffic}
        showAQI={showAQI}
        showEmergencies={showEmergencies}
        boroughFilter={boroughFilter}
      />
    </div>
  );
};
