export interface WeatherData {
  location: string;
  tempC: number | null;
  condition: string; // e.g. "Hot & Humid", or "Unavailable"
  humidityPercent: number | null;
  impactLevel: 'Low' | 'Moderate' | 'High';
  impactSummary: string; // e.g. "Moderate impact on consumption"
  detailNote: string;
  /** "unavailable" whenever weather enrichment is off or the fetch failed. */
  weatherStatus?: 'available' | 'unavailable';
}
