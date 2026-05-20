import axios from 'axios';
 
const NLP_BASE = import.meta.env.VITE_NLP_BASE || 'http://localhost:8081';
const NLP_JWT = import.meta.env.VITE_NLP_JWT; // dev-only
 
export async function getEmbeddings(texts: string[], model = 'tfidf_v1', normalize = true) {
  const res = await axios.post(
    `${NLP_BASE}/v1/nlp/embeddings`,
    { texts, model, normalize },
    { headers: NLP_JWT ? { Authorization: `Bearer ${NLP_JWT}` } : {} }
   );
  return res.data;