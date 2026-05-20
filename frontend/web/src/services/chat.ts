import { api } from './api';
 
export async function sendChatMessage(sessionId: number, userId: number, message: string) {
   const res = await api.post('/chat', { session_id: sessionId, user_id: userId, message });
  return res.data;