'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, User, Bot, Loader2 } from 'lucide-react';
import { ChatMessage } from '@/types/assistant';
import { assistantService } from '@/services/assistantService';

export const AssistantPanel: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    assistantService.getInitialMessages()
  );
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const SUGGESTED_QUESTIONS = [
    'Why was my bill higher this month?',
    'How can I reduce my bill?',
    'What will my next bill be?',
    'How does weather affect my bill?',
    'Which appliances consume the most?'
  ];

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputText;
    if (!textToSend.trim() || isTyping) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: 'Just now'
    };

    setMessages(prev => [...prev, userMsg]);
    if (!queryText) setInputText('');
    setIsTyping(true);

    setTimeout(async () => {
      const response = await assistantService.sendMessage(textToSend);
      setMessages(prev => [...prev, response]);
      setIsTyping(false);
    }, 700);
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col rounded-3xl bg-white border border-slate-200/80 shadow-md font-sans overflow-hidden">
      {/* Top Assistant Header */}
      <div className="p-4 md:px-6 md:py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-white leading-tight">
              Smart Utility Energy Assistant
            </h2>
            <p className="text-xs text-slate-300">
              Ask questions about your bill, tariff rates, or saving tips
            </p>
          </div>
        </div>
      </div>

      {/* Suggested Questions Bar */}
      <div className="p-3 bg-slate-50 border-b border-slate-200/80 overflow-x-auto whitespace-nowrap flex gap-2 shrink-0">
        {SUGGESTED_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            className="px-3 py-1.5 rounded-full bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 border border-slate-200 hover:border-emerald-300 text-xs font-semibold shadow-2xs transition-all cursor-pointer inline-flex items-center gap-1.5 shrink-0"
          >
            <Sparkles className="w-3 h-3 text-emerald-600" />
            {q}
          </button>
        ))}
      </div>

      {/* Chat Messages Container */}
      <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 bg-slate-50/40">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                  <Bot className="w-4 h-4 stroke-[2.2]" />
                </div>
              )}

              <div className={`max-w-xl flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                <div
                  className={`p-4 rounded-2xl text-xs md:text-sm leading-relaxed whitespace-pre-line shadow-2xs ${
                    isUser
                      ? 'bg-emerald-600 text-white font-medium rounded-tr-none'
                      : 'bg-white text-slate-800 border border-slate-200/80 font-normal rounded-tl-none'
                  }`}
                >
                  {msg.text}
                </div>

                {/* Suggested followups */}
                {!isUser && msg.suggestedFollowups && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {msg.suggestedFollowups.map((f, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(f)}
                        className="px-2.5 py-1 rounded-full bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-200/80 text-[11px] font-semibold cursor-pointer shadow-2xs transition-colors"
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs font-bold text-xs">
                  A
                </div>
              )}
            </motion.div>
          );
        })}

        {isTyping && (
          <div className="flex gap-3 justify-start items-center">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3 bg-white border border-slate-200/80 rounded-2xl text-xs font-semibold text-slate-500 flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
              Thinking...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Box Bar */}
      <div className="p-3 md:p-4 bg-white border-t border-slate-200/80 flex items-center gap-2 shrink-0">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask me anything about your electricity usage..."
          className="flex-1 bg-slate-50 border border-slate-200 focus:border-emerald-500 focus:bg-white focus:ring-3 focus:ring-emerald-500/10 rounded-full px-4 py-2.5 text-xs md:text-sm text-slate-900 outline-none transition-all"
        />
        <button
          type="button"
          onClick={() => handleSend()}
          disabled={!inputText.trim() || isTyping}
          className="w-10 h-10 rounded-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white flex items-center justify-center shrink-0 shadow-md transition-all cursor-pointer"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
