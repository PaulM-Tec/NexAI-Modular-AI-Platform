import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './routes/Login';
import Register from './routes/Register';
import Chat from './routes/Chat';
import Recommendations from './routes/Recommendations';
import Embeddings from './routes/Embeddings';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
 
export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recommendations"
          element={
            <ProtectedRoute>
              <Recommendations />
            </ProtectedRoute>
          }
        />
        <Route
          path="/embeddings"
          element={
            <ProtectedRoute>
              <Embeddings />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Login />} />
      </Routes>
    </BrowserRouter    </BrowserRouter>
  );