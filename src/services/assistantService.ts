import { ChatMessage } from '../types/assistant';

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-welcome',
    sender: 'assistant',
    text: 'Hello! I am your Smart Utility AI Assistant. I have analyzed your Oct 2024 bill (352 kWh, ₹2,430). How can I help you understand your consumption or reduce your bill today?',
    timestamp: 'Just now',
    suggestedFollowups: [
      'Why was my bill higher this month?',
      'How can I reduce my bill?',
      'What will my next bill be?',
      'How does weather affect my bill?'
    ]
  }
];

export class AssistantService {
  private messages: ChatMessage[] = [...INITIAL_MESSAGES];

  getInitialMessages(): ChatMessage[] {
    return this.messages;
  }

  async sendMessage(query: string): Promise<ChatMessage> {
    const qLower = query.toLowerCase();
    let replyText = '';
    let suggestedFollowups: string[] = [];

    if (qLower.includes('higher') || qLower.includes('increase') || qLower.includes('why')) {
      replyText = 'Your October bill of ₹2,430 (352 kWh) was 12% higher than September. The main driver was Air Conditioning, accounting for 38% (133 kWh) of your usage due to persistent hot & humid ambient temperatures (28°C avg, 78% humidity).';
      suggestedFollowups = ['Which appliances consume the most?', 'What will my next bill be?'];
    } else if (qLower.includes('reduce') || qLower.includes('save') || qLower.includes('tips')) {
      replyText = 'Here are 3 key actions to lower your monthly bill:\n\n1. **Reduce AC run-time by 1 hour daily** — saves ~₹350/month.\n2. **Set AC thermostat to 24°C instead of 18°C** — each degree higher saves ~6% electricity.\n3. **Switch to 5-Star inverter appliances** — reduces base load by up to 35%.';
      suggestedFollowups = ['How much can I save on AC?', 'Show forecast for next month'];
    } else if (qLower.includes('forecast') || qLower.includes('next')) {
      replyText = 'Based on weather projections and historical patterns, your November 2024 bill is forecasted to be between **₹2,650 and ₹2,950** (~386 kWh).';
      suggestedFollowups = ['Why is November higher?', 'How can I avoid the higher slab rate?'];
    } else if (qLower.includes('weather')) {
      replyText = 'Currently in Mumbai, conditions are **Hot & Humid (28°C, 78% humidity)**. Humidity causes air conditioner compressors to work longer to dehumidify indoor air, adding about 40–60 kWh to your monthly cooling load.';
      suggestedFollowups = ['How can I lower AC energy during humidity?', 'Show consumption breakdown'];
    } else if (qLower.includes('appliance') || qLower.includes('breakdown')) {
      replyText = 'Appliance energy share for Oct 2024:\n- **AC**: 38% (133 kWh)\n- **Refrigerator**: 18% (63 kWh)\n- **Lighting**: 12% (42 kWh)\n- **Fans**: 10% (35 kWh)\n- **Other**: 22% (77 kWh)';
      suggestedFollowups = ['Tips to optimize refrigerator', 'How to reduce lighting usage'];
    } else {
      replyText = `I have logged your question: "${query}". Based on your Oct 2024 bill analysis, your usage is 352 kWh (₹2,430). You are currently in tariff slab 301-500 kWh. Setting your AC to 24°C and turning off idle standby units will keep your next bill below ₹2,600.`;
      suggestedFollowups = ['How can I reduce my bill?', 'Show forecast'];
    }

    const newMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'assistant',
      text: replyText,
      timestamp: 'Just now',
      suggestedFollowups
    };

    this.messages.push(newMsg);
    return newMsg;
  }
}

export const assistantService = new AssistantService();
