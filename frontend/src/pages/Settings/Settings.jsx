import {LogOut, UserRound, Palette} from 'lucide-react';
import {useNavigate} from 'react-router-dom';
import {useAuth} from '../../context/AuthContext';
import {useTheme} from '../../context/ThemeContext';
import GlassCard from '../../components/GlassCard/GlassCard';
import './Settings.css';

export default function Settings(){
  const {user,logout}=useAuth();
  const {theme,toggleTheme}=useTheme();
  const navigate=useNavigate();

  const signOut=()=>{
    logout();
    navigate('/login');
  };

  return <div className="page settings">
    <header className="settings-header">
      <div>
        <p className="eyebrow">ACCOUNT</p>
        <h1>Settings</h1>
        <p className="muted">Manage your profile, login session, and appearance.</p>
      </div>
    </header>

    <div className="settings-sections">
      <GlassCard>
        <div className="settings-card-title">
          <span className="settings-icon"><UserRound size={20}/></span>
          <div><h2>Login profile</h2><p className="muted">Your current account information.</p></div>
        </div>
        <div className="profile-grid">
          <label>Full name<input value={user?.full_name||''} readOnly/></label>
          <label>Email<input value={user?.email||''} readOnly/></label>
        </div>
        <button className="btn btn-danger settings-signout" onClick={signOut}><LogOut size={16}/> Sign out</button>
      </GlassCard>

      <GlassCard>
        <div className="settings-card-title">
          <span className="settings-icon"><Palette size={20}/></span>
          <div><h2>Theme</h2><p className="muted">Choose the appearance used across the application.</p></div>
        </div>
        <div className="theme-choice">
          <div><b>{theme==='dark'?'Dark theme':'Light theme'}</b><p className="muted">Current application appearance.</p></div>
          <button className="btn btn-primary" onClick={toggleTheme}>Switch to {theme==='dark'?'light':'dark'}</button>
        </div>
      </GlassCard>
    </div>
  </div>
}
