// src/services/api.ts
import axios from 'axios';
import { useAuth } from '../store/auth';
 
// Base URL comes from your Vite env vars (.env.development.local)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';
 
// Create a preconfigured Axios instance
export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});
 
// Request interceptor: add Authorization header if we have a token
api.interceptors.request.use((config) => {
  const { token } = useAuth.getState();
  if (token)  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
 
// Optional: Response interceptor to handle 401 (token expired)
// api.interceptors.response.use(
//   (res) => res,
//   (err) => {
//     if (err.response?.status === 401) {
//       useAuth.getState().clearAuth();
//       // You can also redirect to /login here if needed
//     }
//     return Promise.reject(err);
//   }