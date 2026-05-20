import { api } from './api';
 
export async function getRecommendations(userId: number, topN = 3) {
  const res = await api.post('/recommend',  const res = await api.post('/recommend', { user_id: userId, top_n: topN });
  return res.data;