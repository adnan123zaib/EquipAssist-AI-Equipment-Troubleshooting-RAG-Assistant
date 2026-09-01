import {Navigate} from 'react-router-dom';import {useAuth} from '../../context/AuthContext';import './ProtectedRoute.css';
export default function ProtectedRoute({children}){const{user,loading}=useAuth();if(loading)return <div className="auth-loading">Verifying secure session…</div>;return user?children:<Navigate to="/login" replace/>}
