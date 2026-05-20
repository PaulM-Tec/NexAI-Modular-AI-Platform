import { useEffect, useState } from 'react';
import { getRecommendations } from '../services/recommend';
import { useAuth } from '../store/auth';
 
export default function Recommendations() {
  const { user } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
 
  useEffect(() => {
    (async () => {
      if (!user) return;
      setError(null);
      try {
        const data = await getRecommendations(user.id, 3);
        const arr = Array.isArray(data) ? data : data?.recommendations || [];
        setItems(arr);
      } catch (e: any) {
        setError(e?.response?.data?.message || e.message);
      }
    })();
  }, [user]);
 
  return (
    <div style={{ maxWidth: 720, margin: '20px auto' }}>
      <h2>Recommendations</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {items.map((it, idx) => (
          <li key={idx}>
            {typeof it === 'string' ? it : JSON.stringify(it)}
          </li>
        ))}
      </ul>
    </div>
  );