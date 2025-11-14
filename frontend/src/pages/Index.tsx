import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AIInsightsPanel } from "@/components/AIInsightsPanel";
import { MetricsGrid } from "@/components/MetricsGrid";
import { BoroughMap } from "@/components/BoroughMap";
import { BoroughDetails } from "@/components/BoroughDetails";
import { EmergencyTracking } from "@/components/EmergencyTracking";
import { MobileHealthCamps } from "@/components/MobileHealthCamps";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

const BOROUGHS = [
  "All NYC Boroughs",
  "Manhattan",
  "Brooklyn",
  "Queens",
  "Bronx",
  "Staten Island",
];

const Index = () => {
  const [activeView, setActiveView] = useState("maps");
  const [selectedBorough, setSelectedBorough] = useState("Bronx");
  const [boroughFilter, setBoroughFilter] = useState("All NYC Boroughs");

  const { data: segmentsData } = useQuery({
    queryKey: ['segments', boroughFilter],
    queryFn: () => apiClient.getCurrentSegments(1000, undefined, boroughFilter),
    refetchInterval: 30000,
  });

  const { data: zonesData } = useQuery({
    queryKey: ['zones', boroughFilter],
    queryFn: () => apiClient.getCurrentZones(boroughFilter),
    refetchInterval: 30000,
  });

  // Format last updated time
  const getLastUpdated = () => {
    if (segmentsData?.data_freshness_minutes !== undefined && segmentsData.data_freshness_minutes !== null) {
      if (segmentsData.data_freshness_minutes < 1) return "Just now";
      if (segmentsData.data_freshness_minutes < 60) return `${segmentsData.data_freshness_minutes}m ago`;
      const hours = Math.floor(segmentsData.data_freshness_minutes / 60);
      return `${hours}h ago`;
    }
    return "2m ago";
  };

  // Format API response timestamp
  const getApiTimestamp = () => {
    if (segmentsData?.timestamp) {
      try {
        const date = new Date(segmentsData.timestamp);
        return date.toLocaleString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit', 
          minute: '2-digit' 
        });
      } catch {
        return 'N/A';
      }
    }
    return 'N/A';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar Navigation */}
      <Sidebar activeView={activeView} onViewChange={setActiveView} />

      {/* Main Content */}
      <main className="ml-60 mr-80 p-8">
        {/* Top Bar */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">
              {activeView === "maps" && "Borough Maps"}
              {activeView === "environment" && "Environmental Data"}
              {activeView === "analytics" && "Department Analytics"}
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Real-time monitoring across NYC • Data freshness: {getLastUpdated()} • 
              {segmentsData?.count !== undefined && ` ${segmentsData.count} segments`}
              {zonesData?.count !== undefined && ` • ${zonesData.count} zones`}
              {segmentsData?.timestamp && ` • API: ${getApiTimestamp()}`}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Select value={boroughFilter} onValueChange={(value) => {
              setBoroughFilter(value);
              if (value !== "All NYC Boroughs") {
                setSelectedBorough(value);
              }
            }}>
              <SelectTrigger className="w-48 bg-white border border-slate-200 rounded-xl py-2.5 px-4 text-sm font-medium hover:border-blue-300 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 shadow-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-white border border-slate-200 rounded-xl shadow">
                {BOROUGHS.map((borough) => (
                  <SelectItem key={borough} value={borough} className="hover:bg-slate-50">
                    {borough}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Executive Summary */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-6">
            Executive Summary{boroughFilter !== "All NYC Boroughs" ? ` - ${boroughFilter}` : ""}
          </h2>
          <MetricsGrid boroughFilter={boroughFilter} />
        </section>

        {/* Borough Map & Details */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-6">
            NYC Borough Health Risk Overview{boroughFilter !== "All NYC Boroughs" ? ` - ${boroughFilter}` : ""}
          </h2>
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-8">
              <BoroughMap 
                onBoroughSelect={(borough) => {
                  setSelectedBorough(borough);
                  setBoroughFilter(borough);
                }}
                selectedBorough={boroughFilter !== "All NYC Boroughs" ? boroughFilter : selectedBorough}
                boroughFilter={boroughFilter}
              />
            </div>
            <div className="col-span-4">
              <BoroughDetails borough={boroughFilter !== "All NYC Boroughs" ? boroughFilter : selectedBorough} />
            </div>
          </div>
        </section>

        {/* Emergency Tracking */}
        <section className="mb-8">
          <EmergencyTracking boroughFilter={boroughFilter} />
        </section>

        {/* Mobile Health Camps */}
        <section className="mb-8">
          <MobileHealthCamps boroughFilter={boroughFilter} />
        </section>
      </main>

      {/* AI Insights Panel */}
      <AIInsightsPanel />
    </div>
  );
};

export default Index;
