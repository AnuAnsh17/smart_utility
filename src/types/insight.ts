export type InsightBadgeType = 'warning' | 'positive' | 'neutral' | 'info';

export interface InsightItem {
  id: string;
  type: InsightBadgeType;
  iconName: 'zap' | 'shieldCheck' | 'droplet' | 'sparkles' | 'alertTriangle' | 'trendingUp';
  text: string;
}

export interface Recommendation {
  id: string;
  title: string;
  impactLevel: 'High' | 'Medium' | 'Low';
  suggestedAction: string;
  whyItMatters: string;
  potentialImpact: string;
  iconName: 'leaf' | 'shield' | 'clock' | 'zap';
}
