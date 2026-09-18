import { WeatherData } from '../types/weather';
import { MOCK_ANALYSIS_RESULT } from './analysisService';

export class WeatherService {
  async getWeather(location: string = 'Mumbai, MH'): Promise<WeatherData> {
    return {
      ...MOCK_ANALYSIS_RESULT.weather,
      location,
    };
  }
}

export const weatherService = new WeatherService();
