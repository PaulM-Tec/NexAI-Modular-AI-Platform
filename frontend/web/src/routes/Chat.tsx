import { useState } from 'react';
import { sendChatMessage } from '../services/chat';
import { useAuth } from '../store/auth';
 
type Msg = { role: 'user' | 'agent'; text: string };
 
export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const { user } = useAuth();
 
  const send = async () => {
    if (!input.trim() || !user) return;
    const userMsg: Msg = { role: 'user', text: input };
    setMessages((m) => [...m, userMsg]);
    try {
      const resp = await sendChatMessage(1, user.id, input);
      const replyText = resp?.reply ?? resp?.message ?? JSON.stringify(resp);
      setMessages((m) => [...m, { role: 'agent', text: replyText }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'agent', text: `Error: ${e.message}` }]);
    } finally {
      setInput('');
    }
  };
 
  return (
    <div style={{ maxWidth: 720, margin: '20px auto' }}>
      <h2>Chat</h2>
      <div style={{ border: '1px solid #ddd', minHeight: 240, padding: 12 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ margin: '8px 0' }}>
            <b>{m.role === 'user' ? 'You' : 'Agent'}:</b> {m.text}
          </div>
        ))}
      </div>
      <div style={{ marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message"
          style={{          style={{ width: '80%' }}
        />
        <button onClick={send} style={{ marginLeft: 8 }}>Send</button>
      </div>
    </div>
  );