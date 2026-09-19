import { ChatMessage } from '../types/assistant';
import { ApiError, sendChatMessage } from './apiClient';

/** Context the panel knows about from the analysis currently on screen. */
export interface AssistantContext {
  jobId: string | null;
  /** e.g. "Tata Power, 01 Oct 2024 - 31 Oct 2024" — never a figure. */
  billLabel: string | null;
}

const UNAVAILABLE =
  'Could not reach the local analysis service. Is the backend running?';

export class AssistantService {
  private sessionId: string | null = null;

  /**
   * The opening message.
   *
   * Deliberately carries no numbers: every figure the assistant states has to
   * come back from the backend, which reads them out of the stored analysis.
   */
  getInitialMessages(context: AssistantContext): ChatMessage[] {
    if (!context.jobId) {
      return [
        {
          id: 'msg-welcome',
          sender: 'assistant',
          text:
            'Upload an electricity bill and I can answer questions about your units, ' +
            'charges, forecast, and how to reduce consumption. I only answer questions ' +
            'about electricity bills and usage.',
          timestamp: 'Just now',
          suggestedFollowups: [],
        },
      ];
    }

    const subject = context.billLabel
      ? `I have read your bill (${context.billLabel}).`
      : 'I have read your bill.';

    return [
      {
        id: 'msg-welcome',
        sender: 'assistant',
        text: `${subject} Ask about the units consumed, the charges, the next-month forecast, or how to bring it down.`,
        timestamp: 'Just now',
        suggestedFollowups: this.defaultFollowups(),
      },
    ];
  }

  private defaultFollowups(): string[] {
    return [
      'How many units did I use?',
      'What will my next bill be?',
      'Why is my bill high?',
      'How can I reduce it?',
    ];
  }

  async sendMessage(query: string, context: AssistantContext): Promise<ChatMessage> {
    try {
      const payload = await sendChatMessage({
        message: query,
        job_id: context.jobId,
        session_id: this.sessionId,
      });
      this.sessionId = payload.session_id;

      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        text: payload.reply,
        timestamp: 'Just now',
        suggestedFollowups:
          payload.suggested_followups.length > 0
            ? payload.suggested_followups
            : this.defaultFollowups(),
      };
    } catch (error) {
      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        text: error instanceof ApiError ? error.message : UNAVAILABLE,
        timestamp: 'Just now',
        suggestedFollowups: [],
      };
    }
  }
}

export const assistantService = new AssistantService();
