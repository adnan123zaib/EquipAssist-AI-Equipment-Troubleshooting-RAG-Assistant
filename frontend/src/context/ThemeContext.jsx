import {createContext,useContext,useEffect,useState} from 'react';
const ThemeContext=createContext(null);
const preferredTheme=()=>{const saved=localStorage.getItem('equipassist_theme');if(saved==='light'||saved==='dark')return saved;return window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'};
export function ThemeProvider({children}){const[theme,setTheme]=useState(preferredTheme);useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;localStorage.setItem('equipassist_theme',theme)},[theme]);const toggleTheme=()=>setTheme(value=>value==='dark'?'light':'dark');return <ThemeContext.Provider value={{theme,toggleTheme}}>{children}</ThemeContext.Provider>}
export const useTheme=()=>useContext(ThemeContext);
