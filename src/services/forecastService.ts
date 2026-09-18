import { ForecastData } from '../types/forecast';
import { MOCK_ANALYSIS_RESULT } from './analysisService';

export class ForecastService {
  async getForecast(): Promise<ForecastData> {
    return MOCK_ANALYSIS_RESULT.forecast;
  }
}

export const forecastService = new ForecastService();
