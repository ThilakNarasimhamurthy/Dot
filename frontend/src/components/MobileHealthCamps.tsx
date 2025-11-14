import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { MockData } from "@/lib/utils";
import { useMemo } from "react";

interface MobileHealthCampsProps {
  boroughFilter?: string;
}

export const MobileHealthCamps = ({ boroughFilter = "All NYC Boroughs" }: MobileHealthCampsProps) => {
  const { data: zonesData, isLoading } = useQuery({
    queryKey: ['zones', boroughFilter],
    queryFn: () => apiClient.getCurrentZones(boroughFilter),
    refetchInterval: 30000,
  });

  // Generate priority locations from zones data
  const locations = useMemo(() => {
    const defaultLocations = [
      { rank: 1, neighborhood: "Mott Haven", borough: "Bronx", risk: 92, aqi: 95, pop: 54000, lives: "8-12", priority: "CRITICAL", rankColor: "text-red-600" },
      { rank: 2, neighborhood: "Hunts Point", borough: "Bronx", risk: 88, aqi: 91, pop: 47000, lives: "6-10", priority: "CRITICAL", rankColor: "text-red-600" },
      { rank: 3, neighborhood: "Port Morris", borough: "Bronx", risk: 85, aqi: 87, pop: 32000, lives: "4-7", priority: "HIGH", rankColor: "text-orange-600" },
      { rank: 4, neighborhood: "East Harlem", borough: "Manhattan", risk: 78, aqi: 82, pop: 41000, lives: "3-6", priority: "HIGH", rankColor: "text-orange-600" },
      { rank: 5, neighborhood: "Brownsville", borough: "Brooklyn", risk: 72, aqi: 76, pop: 38000, lives: "2-5", priority: "MODERATE", rankColor: "text-amber-600" }
    ];

    if (!zonesData || zonesData.zones.length === 0) {
      return defaultLocations;
    }

    // Sort zones by risk (traffic_pollution_risk, incidents, and congestion)
    const sortedZones = [...zonesData.zones].sort((a, b) => {
      const riskA = a.traffic_pollution_risk === 'High' ? 3 : a.traffic_pollution_risk === 'Medium' ? 2 : 1;
      const riskB = b.traffic_pollution_risk === 'High' ? 3 : b.traffic_pollution_risk === 'Medium' ? 2 : 1;
      if (riskA !== riskB) return riskB - riskA;
      // Then by total incidents
      const incidentsA = a.incident_count + a.transit_delay_count;
      const incidentsB = b.incident_count + b.transit_delay_count;
      if (incidentsA !== incidentsB) return incidentsB - incidentsA;
      // Then by congestion
      return b.avg_congestion_index - a.avg_congestion_index;
    });

    return sortedZones
      .map((zone, idx) => {
      // Calculate risk using traffic_pollution_risk and incidents
      const pollutionRisk = zone.traffic_pollution_risk === 'High' ? 40 : zone.traffic_pollution_risk === 'Medium' ? 20 : 5;
      const incidentRisk = Math.min(30, ((zone.incident_count + zone.transit_delay_count) / zone.segment_count) * 30);
      const congestionRisk = zone.avg_congestion_index * 30;
      const risk = Math.round(pollutionRisk + incidentRisk + congestionRisk);
      
      const aqi = zone.avg_pm25 ? Math.min(150, Math.round(zone.avg_pm25 * 2.5)) : 50;
      const priority = risk >= 86 ? 'CRITICAL' : risk >= 71 ? 'HIGH' : 'MODERATE';
      const rankColor = risk >= 86 ? 'text-red-600' : risk >= 71 ? 'text-orange-600' : 'text-amber-600';
      
      // Use borough field if available, otherwise infer from zone_id
      let borough = zone.borough || "Manhattan";
      if (!borough) {
        const zoneIdLower = zone.zone_id.toLowerCase();
        if (zoneIdLower.includes("bronx") || zoneIdLower.includes("bx")) borough = "Bronx";
        else if (zoneIdLower.includes("brooklyn") || zoneIdLower.includes("bk")) borough = "Brooklyn";
        else if (zoneIdLower.includes("queens") || zoneIdLower.includes("qn")) borough = "Queens";
        else if (zoneIdLower.includes("staten") || zoneIdLower.includes("si")) borough = "Staten Island";
      }
      
      // Filter by boroughFilter if not "All NYC Boroughs"
      if (boroughFilter !== "All NYC Boroughs" && borough !== boroughFilter) {
        return null;
      }

      // Calculate detailed insights
      const totalIncidents = zone.incident_count + zone.transit_delay_count;
      const incidentRate = zone.segment_count > 0 ? (totalIncidents / zone.segment_count) * 100 : 0;
      const congestionPercent = Math.round(zone.avg_congestion_index * 100);
      const avgSpeed = zone.avg_speed_mph || 0;
      
      // Calculate lives saved estimate based on incidents, congestion, and PM2.5
      // Formula: Base on incidents + congestion impact + air quality impact
      const baseLives = Math.max(2, Math.round(totalIncidents * 1.5));
      const congestionImpact = congestionPercent > 70 ? Math.round(congestionPercent / 10) : 0;
      const airQualityImpact = zone.avg_pm25 && zone.avg_pm25 > 25 ? Math.round((zone.avg_pm25 - 15) / 2) : 0;
      const maxLives = baseLives + congestionImpact + airQualityImpact;
      
      // Population at risk calculation
      // Base on segment count, adjusted by congestion and incidents
      const basePop = zone.segment_count * 1000;
      const congestionMultiplier = congestionPercent > 70 ? 1.3 : congestionPercent > 50 ? 1.15 : 1.0;
      const incidentMultiplier = incidentRate > 10 ? 1.2 : incidentRate > 5 ? 1.1 : 1.0;
      const popAtRisk = Math.round(basePop * congestionMultiplier * incidentMultiplier);
      
      return {
        rank: idx + 1,
        neighborhood: zone.zone_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        borough,
        risk,
        aqi,
        pop: popAtRisk,
        lives: `${baseLives}-${maxLives}`,
        priority,
        rankColor,
        // Additional detailed insights
        congestionPercent,
        avgSpeed: avgSpeed.toFixed(1),
        incidentRate: incidentRate.toFixed(1),
        segmentCount: zone.segment_count,
        pm25: zone.avg_pm25 ? zone.avg_pm25.toFixed(1) : MockData.getPM25(boroughFilter).toFixed(1)
      };
      })
      .filter(loc => loc !== null)
      .slice(0, 5);
  }, [zonesData, boroughFilter]);

  return (
    <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            Priority Health Camp Locations{boroughFilter !== "All NYC Boroughs" ? ` - ${boroughFilter}` : ""}
          </h3>
          <p className="text-sm text-gray-600">Neighborhoods ranked by lives-saved potential</p>
        </div>
        <Button className="bg-safe hover:bg-green-700 text-white flex items-center gap-2 rounded-lg shadow-sm">
          <Plus className="h-4 w-4" />
          Deploy Camp
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">#</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Neighborhood</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Borough</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Risk</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">AQI</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Pop at Risk</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Lives/Day</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Priority</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-600 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {locations.map((loc) => (
              <tr key={loc.rank} className="hover:bg-blue-50/50 transition-colors group">
                <td className="py-4 px-4"><span className={`text-2xl font-bold ${loc.rankColor} tabular-nums`}>#{loc.rank}</span></td>
                <td className="py-4 px-4">
                  <div>
                    <span className="font-semibold text-gray-900">{loc.neighborhood}</span>
                    {loc.segmentCount !== undefined && (
                      <div className="text-xs text-gray-500 mt-0.5">{loc.segmentCount} segments</div>
                    )}
                  </div>
                </td>
                <td className="py-4 px-4"><span className="text-gray-600">{loc.borough}</span></td>
                <td className="py-4 px-4">
                  <div>
                    <span className={`text-xl font-bold ${loc.rankColor} tabular-nums`}>{loc.risk}</span><span className="text-sm text-gray-600">/100</span>
                    {loc.congestionPercent !== undefined && (
                      <div className="text-xs text-gray-500 mt-0.5">{loc.congestionPercent}% congestion</div>
                    )}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div>
                    <span className="text-lg font-bold text-high-risk tabular-nums">{loc.aqi}</span>
                    {loc.pm25 && (
                      <div className="text-xs text-gray-500 mt-0.5">PM2.5: {loc.pm25}</div>
                    )}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div>
                    <span className="font-semibold text-gray-900 tabular-nums">{loc.pop.toLocaleString()}</span>
                    {loc.avgSpeed && (
                      <div className="text-xs text-gray-500 mt-0.5">Speed: {loc.avgSpeed} mph</div>
                    )}
                  </div>
                </td>
                <td className="py-4 px-4"><div className="bg-safe-bg border border-green-300 rounded-lg px-3 py-1.5 inline-block"><span className="text-lg font-bold text-safe tabular-nums">{loc.lives}</span></div></td>
                <td className="py-4 px-4">
                  <Badge className={`${
                    loc.priority === 'CRITICAL' ? 'bg-critical-bg text-critical border border-red-200' : 
                    loc.priority === 'HIGH' ? 'bg-high-risk-bg text-high-risk border border-orange-200' : 
                    'bg-moderate-bg text-moderate border border-yellow-200'
                  } rounded-full border`}>
                    {loc.priority}
                  </Badge>
                </td>
                <td className="py-4 px-4">
                  <Button className="bg-safe hover:bg-green-700 text-white font-semibold rounded-lg px-4 py-2 text-sm shadow-sm">
                    {loc.priority === 'CRITICAL' ? 'Deploy Now' : 'Schedule'}
                  </Button>
                </td>
              </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
