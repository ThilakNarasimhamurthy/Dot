import { Badge } from "@/components/ui/badge";
import { AlertCircle, Clock, TrendingUp, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useMemo } from "react";

interface BoroughDetailsProps {
  borough: string;
}

export const BoroughDetails = ({ borough }: BoroughDetailsProps) => {
  const { data: zonesData, isLoading: zonesLoading } = useQuery({
    queryKey: ['zones', borough],
    queryFn: () => apiClient.getCurrentZones(borough),
    refetchInterval: 30000,
  });

  const { data: segmentsData, isLoading: segmentsLoading } = useQuery({
    queryKey: ['segments', borough],
    queryFn: () => apiClient.getCurrentSegments(1000, undefined, borough),
    refetchInterval: 30000,
  });

  // Calculate borough data from real API data
  const boroughData = useMemo(() => {
    const defaultData: Record<string, any> = {
      "Bronx": { riskScore: 92, status: "CRITICAL", aqi: 95, erVisits: 194, responseTime: "11.5m", avgSpeed: "8.2mph", alerts: [], population: 54000 },
      "Manhattan": { riskScore: 48, status: "MODERATE", aqi: 52, erVisits: 127, responseTime: "7.8m", avgSpeed: "12.4mph", alerts: [], population: 38000 },
      "Brooklyn": { riskScore: 62, status: "ELEVATED", aqi: 68, erVisits: 156, responseTime: "8.9m", avgSpeed: "10.7mph", alerts: [], population: 47000 },
      "Queens": { riskScore: 71, status: "HIGH", aqi: 78, erVisits: 178, responseTime: "9.8m", avgSpeed: "9.5mph", alerts: [], population: 51000 },
      "Staten Island": { riskScore: 28, status: "LOW", aqi: 35, erVisits: 42, responseTime: "6.2m", avgSpeed: "18.3mph", alerts: [], population: 15000 }
    };

    if (!zonesData || !segmentsData) {
      return defaultData;
    }

    // Calculate real data for each borough
    const calculateBoroughMetrics = (boroughName: string) => {
      // Filter zones and segments for this borough using borough field
      const boroughZones = zonesData.zones.filter(z => 
        z.borough === boroughName
      );

      const boroughSegments = segmentsData.segments.filter(s => 
        s.borough === boroughName
      );

      // Calculate metrics from zones (preferred - aggregated data)
      const avgCongestion = boroughZones.length > 0
        ? boroughZones.reduce((sum, z) => sum + (z.avg_congestion_index !== null && z.avg_congestion_index !== undefined && !isNaN(z.avg_congestion_index) ? z.avg_congestion_index : 0), 0) / boroughZones.length
        : 0.5;
      
      const avgPM25 = boroughZones.length > 0
        ? boroughZones.filter(z => z.avg_pm25 !== null && z.avg_pm25 !== undefined && !isNaN(z.avg_pm25)).reduce((sum, z) => sum + (z.avg_pm25 || 0), 0) / boroughZones.filter(z => z.avg_pm25 !== null && z.avg_pm25 !== undefined && !isNaN(z.avg_pm25)).length
        : 0;
      
      const aqi = avgPM25 > 0 ? Math.min(150, Math.round(avgPM25 * 2.5)) : defaultData[boroughName]?.aqi || 50;

      // Use zone incident counts (more accurate aggregated data)
      const incidentCount = boroughZones.reduce((sum, z) => sum + (z.incident_count || 0), 0);
      const transitDelays = boroughZones.reduce((sum, z) => sum + (z.transit_delay_count || 0), 0);
      const totalIncidents = incidentCount + transitDelays;
      
      // Get traffic pollution risk from zones
      const highRiskZones = boroughZones.filter(z => z.traffic_pollution_risk === 'High').length;
      const mediumRiskZones = boroughZones.filter(z => z.traffic_pollution_risk === 'Medium').length;
      const trafficPollutionRisk = highRiskZones > 0 ? 'High' : mediumRiskZones > 0 ? 'Medium' : 'Low';
      
      // Get total segment count from zones
      const totalSegmentCount = boroughZones.reduce((sum, z) => sum + (z.segment_count || 0), 0);

      // Use avg_speed_mph from zones (preferred) or calculate from segments
      const avgSpeedFromZones = boroughZones.length > 0
        ? boroughZones.reduce((sum, z) => sum + (z.avg_speed_mph !== null && z.avg_speed_mph !== undefined && !isNaN(z.avg_speed_mph) ? z.avg_speed_mph : 0), 0) / boroughZones.length
        : 0;
      
      const avgSpeed = avgSpeedFromZones > 0 ? avgSpeedFromZones : (
        boroughSegments.length > 0
          ? boroughSegments.filter(s => s.speed_mph !== null && s.speed_mph !== undefined && !isNaN(s.speed_mph) && s.speed_mph > 0).reduce((sum, s) => sum + (s.speed_mph || 0), 0) / boroughSegments.filter(s => s.speed_mph !== null && s.speed_mph !== undefined && !isNaN(s.speed_mph) && s.speed_mph > 0).length
          : 0
      );
      
      // Calculate response time - ensure it's always a number
      let responseTime: number;
      if (avgSpeed > 0) {
        responseTime = Math.max(5, 15 - (avgSpeed / 2));
      } else {
        // Parse default response time if available, otherwise use 9
        const defaultResponseTime = defaultData[boroughName]?.responseTime;
        if (typeof defaultResponseTime === 'string') {
          responseTime = parseFloat(defaultResponseTime.replace('m', '')) || 9;
        } else {
          responseTime = 9;
        }
      }

      // Calculate risk score using traffic_pollution_risk from zones
      const riskFromPollution = trafficPollutionRisk === 'High' ? 30 : trafficPollutionRisk === 'Medium' ? 15 : 5;
      const riskScore = Math.min(100, Math.round(
        (avgCongestion * 40) + 
        (Math.min(1, totalIncidents / 10) * 30) + 
        riskFromPollution
      ));

      const status = riskScore >= 86 ? "CRITICAL" : riskScore >= 71 ? "HIGH" : riskScore >= 51 ? "ELEVATED" : riskScore >= 31 ? "MODERATE" : "LOW";

      // Generate detailed alerts based on real data with specific insights
      const alerts: string[] = [];
      
      // Traffic pollution insights
      if (trafficPollutionRisk === 'High') {
        const highRiskZoneCount = boroughZones.filter(z => z.traffic_pollution_risk === 'High').length;
        alerts.push(`High traffic pollution risk detected in ${highRiskZoneCount} zone${highRiskZoneCount !== 1 ? 's' : ''}`);
      }
      
      // Air quality insights
      if (avgPM25 > 30) {
        const unhealthyZones = boroughZones.filter(z => z.avg_pm25 && z.avg_pm25 > 30).length;
        alerts.push(`High PM2.5 levels (${Math.round(avgPM25)} µg/m³) affecting ${unhealthyZones} zone${unhealthyZones !== 1 ? 's' : ''}`);
      } else if (avgPM25 > 12) {
        alerts.push(`Moderate PM2.5 levels (${Math.round(avgPM25)} µg/m³) - monitor closely`);
      }
      
      // Incident insights
      if (incidentCount > 0) {
        const highCongestionIncidents = boroughSegments.filter(s => 
          s.incident_flag && s.congestion_index > 0.7
        ).length;
        alerts.push(`${incidentCount} active traffic incident${incidentCount !== 1 ? 's' : ''}${highCongestionIncidents > 0 ? ` (${highCongestionIncidents} with high congestion)` : ''}`);
      }
      
      // Transit delay insights
      if (transitDelays > 0) {
        const affectedSegments = boroughSegments.filter(s => s.transit_delay_flag).length;
        alerts.push(`${transitDelays} transit delay${transitDelays !== 1 ? 's' : ''} affecting ${affectedSegments} segment${affectedSegments !== 1 ? 's' : ''}`);
      }
      
      // Speed insights
      if (avgSpeed < 10 && avgSpeed > 0) {
        const slowSegments = boroughSegments.filter(s => s.speed_mph < 10 && s.speed_mph > 0).length;
        alerts.push(`Slow traffic speeds (${avgSpeed.toFixed(1)} mph avg) affecting ${slowSegments} segment${slowSegments !== 1 ? 's' : ''}`);
      }
      
      // Congestion insights
      if (totalSegmentCount > 0 && avgCongestion > 0.7) {
        const highCongestionSegments = boroughSegments.filter(s => 
          s.congestion_index > 0.7
        ).length;
        alerts.push(`High congestion (${(avgCongestion * 100).toFixed(0)}%) affecting ${highCongestionSegments} of ${totalSegmentCount} segment${totalSegmentCount !== 1 ? 's' : ''}`);
      } else if (avgCongestion > 0.5) {
        alerts.push(`Moderate congestion (${(avgCongestion * 100).toFixed(0)}%) detected`);
      }
      
      // Data quality insights
      const lowConfidenceSegments = boroughSegments.filter(s => 
        s.data_confidence_score < 0.7
      ).length;
      if (lowConfidenceSegments > 0) {
        alerts.push(`${lowConfidenceSegments} segment${lowConfidenceSegments !== 1 ? 's' : ''} with low data confidence (<70%)`);
      }
      
      if (alerts.length === 0) alerts.push("All systems operating normally");

      // Format avgSpeed - ensure it's always a number before formatting
      let avgSpeedFormatted: string;
      if (avgSpeed > 0) {
        avgSpeedFormatted = `${avgSpeed.toFixed(1)}mph`;
      } else {
        const defaultAvgSpeed = defaultData[boroughName]?.avgSpeed;
        if (typeof defaultAvgSpeed === 'string') {
          const parsedSpeed = parseFloat(defaultAvgSpeed.replace('mph', '')) || 10.0;
          avgSpeedFormatted = `${parsedSpeed.toFixed(1)}mph`;
        } else {
          avgSpeedFormatted = '10.0mph';
        }
      }

      return {
        riskScore,
        status,
        aqi,
        erVisits: totalIncidents * 10, // Estimate based on incidents
        responseTime: `${responseTime.toFixed(1)}m`,
        avgSpeed: avgSpeedFormatted,
        alerts: alerts.map(text => ({ text })),
        population: defaultData[boroughName]?.population || 30000,
        breakdown: defaultData[boroughName]?.breakdown || [],
        segmentCount: totalSegmentCount,
        trafficPollutionRisk: trafficPollutionRisk
      };
    };

    const computed: Record<string, any> = {};
    ["Bronx", "Manhattan", "Brooklyn", "Queens", "Staten Island"].forEach(boroughName => {
      computed[boroughName] = calculateBoroughMetrics(boroughName);
    });

    return computed;
  }, [zonesData, segmentsData, borough]);

  const data = boroughData[borough] || boroughData["Bronx"] || {
    riskScore: 50,
    status: "MODERATE",
    aqi: 50,
    erVisits: 100,
    responseTime: "9.0m",
    avgSpeed: "10.0mph",
    alerts: [{ text: "Loading data..." }],
    population: 30000,
    breakdown: []
  };

  if (zonesLoading || segmentsLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm h-full">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  const getBorderColor = () => {
    if (data.riskScore >= 86) return 'border-red-600';
    if (data.riskScore >= 71) return 'border-orange-600';
    if (data.riskScore >= 51) return 'border-amber-600';
    return 'border-blue-600';
  };

  const getStatusColor = () => {
    if (data.riskScore >= 86) return 'bg-red-600';
    if (data.riskScore >= 71) return 'border-orange-600';
    return 'bg-blue-600';
  };

  const getRiskColor = () => {
    if (data.riskScore >= 86) return 'text-red-600';
    if (data.riskScore >= 71) return 'text-orange-600';
    return 'text-blue-600';
  };

  const getProgressColor = () => {
    if (data.riskScore >= 86) return 'bg-red-600';
    if (data.riskScore >= 71) return 'bg-orange-600';
    return 'bg-blue-600';
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold text-gray-900">{borough}</h3>
        <Badge className={`${getStatusColor()} text-white border-0 rounded-full px-3 py-1 text-xs font-semibold`}>
          {data.status}
        </Badge>
      </div>

        {/* Health Risk Score */}
        <div className="mb-6">
          <div className="flex items-baseline gap-2 mb-3">
            <span className={`text-5xl font-bold ${getRiskColor()} tabular-nums`}>{data.riskScore}</span>
            <span className="text-xl text-gray-600">/100</span>
          </div>
          <div className="bg-gray-200 h-3 rounded-full overflow-hidden">
            <div 
              className={`${getProgressColor()} h-full rounded-full transition-all`}
              style={{ width: `${data.riskScore}%` }}
            />
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">AQI</div>
            <div className="text-2xl font-bold text-high-risk tabular-nums">{data.aqi}</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">ER Visits</div>
            <div className="text-2xl font-bold text-health tabular-nums">{data.erVisits}</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Response Time</div>
            <div className="text-2xl font-bold text-critical tabular-nums">{data.responseTime}</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Speed</div>
            <div className="text-2xl font-bold text-moderate tabular-nums">{data.avgSpeed}</div>
          </div>
          {data.segmentCount !== undefined && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Segments</div>
              <div className="text-2xl font-bold text-blue-600 tabular-nums">{data.segmentCount}</div>
            </div>
          )}
          {data.trafficPollutionRisk && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Pollution Risk</div>
              <div className={`text-2xl font-bold tabular-nums ${
                data.trafficPollutionRisk === 'High' ? 'text-red-600' :
                data.trafficPollutionRisk === 'Medium' ? 'text-orange-600' : 'text-green-600'
              }`}>
                {data.trafficPollutionRisk}
              </div>
            </div>
          )}
        </div>

      {/* Critical Issues */}
      <div className="space-y-2 mb-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Critical Issues</h4>
        {data.alerts && data.alerts.length > 0 ? (
          data.alerts.slice(0, 3).map((alert: any, idx: number) => {
            const isCritical = data.riskScore >= 71;
            const bgColor = isCritical ? "bg-critical-bg border-critical" : "bg-high-risk-bg border-high-risk";
            const textColor = isCritical ? "text-critical" : "text-high-risk";
            const Icon = idx === 0 ? AlertCircle : idx === 1 ? Clock : TrendingUp;
            
            return (
              <div key={idx} className={`${bgColor} border-l-4 rounded-lg p-3 flex items-start gap-3`}>
                <Icon className={`h-4 w-4 ${textColor} flex-shrink-0 mt-0.5`} />
          <div>
                  <p className="text-sm text-gray-900 font-medium">{alert.text}</p>
          </div>
        </div>
            );
          })
        ) : (
          <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-3 flex items-start gap-3">
            <AlertCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
              <p className="text-sm text-gray-900 font-medium">All systems operating normally</p>
        </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="space-y-2">
        <button className="w-full py-3 bg-info hover:bg-blue-700 text-white font-semibold rounded-xl text-sm transition-colors shadow-sm">
          Reroute Traffic
        </button>
        <button className="w-full py-3 bg-safe hover:bg-green-700 text-white font-semibold rounded-xl text-sm transition-colors shadow-sm">
          Deploy Mobile Clinic
        </button>
        <button className="w-full py-3 bg-high-risk hover:bg-orange-700 text-white font-semibold rounded-xl text-sm transition-colors shadow-sm">
          Alert Residents
        </button>
      </div>
    </div>
  );
};
