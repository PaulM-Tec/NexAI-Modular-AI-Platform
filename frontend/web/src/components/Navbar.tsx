// src/components/Navbar.tsx
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
 
export default function Navbar() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
 
  const onLogout = () => {
    useAuth.getState().clearAuth();
    navigate('/login');
  };
 
  return (
    <nav style={{
      padding: '8px 16px',
      borderBottom: '1px solid #ddd',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 16
    }}>
      <div style={{ display: 'flex', gap: 12 }}>
        <Link to="/chat">Chat</Link>
        <Link to="/recommendations">Recommendations</Link>
        <Link to="/embeddings">Embeddings</Link>
      </div>
 
      <div>
        {token ? (
          <>
            <span style={{ marginRight: 12 }}>{user?.email}</span>
            <button onClick={onLogout}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" style={{ marginRight: 12 }}>Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}