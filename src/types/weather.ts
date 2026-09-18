export interface WeatherData {
  location: string;
  tempC: number;
  condition: string; // e.g. "Hot & Humid"
  humidityPercent: number;
  impactLevel: 'Low' | 'Moderate' | 'High';
  impactSummary: string; // e.g. "Moderate impact on consumption"
  detailNote: string;
}
