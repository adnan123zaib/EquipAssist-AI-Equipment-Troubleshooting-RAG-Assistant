import axios from 'axios';
const api=axios.create({baseURL:import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api/v1'});
api.interceptors.request.use(config=>{const token=localStorage.getItem('equipassist_token');if(token)config.headers.Authorization=`Bearer ${token}`;return config});
api.interceptors.response.use(r=>r,error=>{if(error.response?.status===401){localStorage.removeItem('equipassist_token');localStorage.removeItem('equipassist_user');if(!location.pathname.startsWith('/login'))location.href='/login'}return Promise.reject(error)});
export default api;
