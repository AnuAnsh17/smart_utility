export type SenderRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  sender: SenderRole;
  text: string;
  timestamp: string;
  suggestedFollowups?: string[];
  actionLink?: {
    label: string;
    targetTab: string;
  };
}
