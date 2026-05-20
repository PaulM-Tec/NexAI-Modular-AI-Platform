import { api } from './api';
import { useAuth } from '../store/auth';
 
type Credentials = { email: string; password: string };
type RegisterPayload = Credentials & { name?: string };
 
export async function login(data: Credentials) {
  const res = await api.post('/auth/login', data);
  const { token, user } = res.data;
  useAuth.getState().setAuth(token, user);
  return user;
}
 
export async function register(data: RegisterPayload) {
  const res = await api.post('/auth/register', data);
   const { token, user } = res.data;
  useAuth.getState().setAuth(token, user);
  return user;
}
 
export function logout() {
  useAuth.getState().clearAuth();