import { useState } from 'react';
import { register } from '../services/auth';
import { useNavigate } from 'react-router-dom';
 
export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
 
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register({ name, email, password });
      navigate('/chat');
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Register failed');
    }
  };
 
  return (
    <div style={{ maxWidth: 360, margin: '40px auto' }}>
      <h2>Register</h2>
      <form onSubmit={onSubmit}>
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        <label>Password</label>
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit">Create Account</button        <button type="submit">Create Account</button>
      </form>
    </div>
  );