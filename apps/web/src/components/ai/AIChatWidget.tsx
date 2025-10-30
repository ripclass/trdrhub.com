import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  MessageCircle,
  Send,
  Bot,
  User,
  AlertTriangle,
  Minimize2,
  Maximize2,
  X,
} from 'lucide-react';
import { api } from '@/api/client';

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  confidenceScore?: number;
  modelUsed?: string;
  fallbackUsed?: boolean;
}

interface AIChatWidgetProps {
  lcId?: string;
  className?: string;
  minimized?: boolean;
  onToggleMinimize?: (minimized: boolean) => void;
  onClose?: () => void;
}

export default function AIChatWidget({
  lcId,
  className = "",
  minimized = false,
  onToggleMinimize,
  onClose
}: AIChatWidgetProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: 'Hello! I\'m your AI assistant for trade finance. I can help you understand discrepancies, draft amendments, and answer questions about LC compliance. How can I assist you today?',
      sender: 'ai',
      timestamp: new Date(),
      confidenceScore: 1.0,
      modelUsed: 'gpt-4'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const confidenceToScore = (confidence?: string): number => {
    if (!confidence) return 0.5;
    switch (confidence.toLowerCase()) {
      case 'high':
        return 0.9;
      case 'medium':
        return 0.7;
      case 'low':
        return 0.4;
      default:
        return 0.5;
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      content: input.trim(),
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const { data } = await api.post('/api/ai/chat', {
        session_id: sessionId,
        question: userMessage.content,
        language: 'en',
        context_documents: [],
      });

      const aiMessage: ChatMessage = {
        id: `msg_${Date.now()}_ai`,
        content: data.output || data.content || 'I have shared the requested information.',
        sender: 'ai',
        timestamp: new Date(),
        confidenceScore:
          typeof data.confidence_score === 'number'
            ? data.confidence_score
            : confidenceToScore(data.confidence),
        modelUsed: data.model_used || data.model_version,
        fallbackUsed: Boolean(data.fallback_used),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now()}_error`,
        content:
          'I encountered an error while responding. Please try again or contact support if the issue persists.',
        sender: 'ai',
        timestamp: new Date(),
        confidenceScore: 0,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getConfidenceColor = (score?: number) => {
    if (!score) return 'bg-gray-100 text-gray-800';
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  if (minimized) {
    return (
      <Card className={`w-80 ${className}`}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-blue-600" />
              <CardTitle className="text-sm">AI Assistant</CardTitle>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onToggleMinimize?.(false)}
                className="h-6 w-6 p-0"
              >
                <Maximize2 className="w-3 h-3" />
              </Button>
              {onClose && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="h-6 w-6 p-0"
                >
                  <X className="w-3 h-3" />
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={`w-96 h-[500px] flex flex-col ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-lg">AI Assistant</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggleMinimize?.(true)}
              className="h-8 w-8 p-0"
            >
              <Minimize2 className="w-4 h-4" />
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-4 pt-0">
        <ScrollArea className="flex-1 pr-4" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.sender === 'ai' && (
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="bg-blue-100">
                      <Bot className="w-4 h-4 text-blue-600" />
                    </AvatarFallback>
                  </Avatar>
                )}

                <div
                  className={`max-w-[80%] ${
                    message.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  } rounded-lg p-3`}
                >
                  <div className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </div>

                  {message.sender === 'ai' && message.confidenceScore !== undefined && (
                    <div className="flex items-center gap-1 mt-2">
                      <Badge
                        className={`text-xs ${getConfidenceColor(message.confidenceScore)}`}
                      >
                        {Math.round(message.confidenceScore * 100)}%
                      </Badge>
                      {message.fallbackUsed && (
                        <Badge variant="outline" className="text-xs text-orange-600">
                          Fallback
                        </Badge>
                      )}
                    </div>
                  )}

                  <div className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>

                {message.sender === 'user' && (
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="bg-gray-100">
                      <User className="w-4 h-4 text-gray-600" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start">
                <Avatar className="w-8 h-8">
                  <AvatarFallback className="bg-blue-100">
                    <Bot className="w-4 h-4 text-blue-600" />
                  </AvatarFallback>
                </Avatar>
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-xs text-gray-500">AI is typing...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="flex gap-2 mt-4">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about trade finance, discrepancies, or LC compliance..."
            disabled={loading}
            className="flex-1"
          />
          <Button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            size="icon"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>

        <div className="text-xs text-muted-foreground mt-2 text-center">
          Trade finance AI assistant - Powered by LCopilot
        </div>
      </CardContent>
    </Card>
  );
}
