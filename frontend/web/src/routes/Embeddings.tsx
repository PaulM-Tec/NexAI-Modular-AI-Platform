import { useState } from 'react';
import { getEmbeddings } from '../services/nlp';
 
export default function Embeddings() {
  const [texts, setTexts] = useState('This is a test\nVectorize me please');
  const [model, setModel] = useState('tfidf_v1');
  const [normalize, setNormalize] = useState(true);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
 
  const run = async () => {
    setError(null);
    try {
      const arr = texts.split('\n').map((t) => t.trim()).filter(Boolean);
      const data = await getEmbeddings(arr, model, normalize);
      setResult(data);
    } catch (e: any) {
      setError(e?.response?.data?.message || e.message);
    }
  };
 
  return (
    <div style={{ maxWidth: 840, margin: '20px auto' }}>
      <h2>NLP Embeddings</h2>
      <textarea rows={6} style={{ width: '100%' }} value={texts} onChange={(e) => setTexts(e.target.value)} />
      <div style={{ marginTop: 8 }}>
        <label>Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} />
        <label style={{ marginLeft: 12 }}>
          <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} /> Normalize
        </label>
        <button onClick={run} style={{ marginLeft: 12 }}>Vectorize</button>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 12 }}>
          <pre style={{ background: '#f7f7f7', padding: 8 }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </    </div>
  );