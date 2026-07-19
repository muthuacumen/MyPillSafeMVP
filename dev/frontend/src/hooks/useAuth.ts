import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, type LoginPayload, type RegisterPayload } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, setUser, setToken, logout: storeLogout } = useAuthStore();

  const register = useCallback(async (payload: RegisterPayload) => {
    const { data } = await authApi.register(payload);
    setToken(data.access_token);
    const { data: me } = await authApi.me();
    setUser(me);
    navigate('/dashboard');
  }, [navigate, setToken, setUser]);

  const login = useCallback(async (payload: LoginPayload) => {
    const { data } = await authApi.login(payload);
    setToken(data.access_token);
    const { data: me } = await authApi.me();
    setUser(me);
    navigate('/dashboard');
  }, [navigate, setToken, setUser]);

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {});
    storeLogout();
    navigate('/login');
  }, [navigate, storeLogout]);

  return { user, isAuthenticated, register, login, logout };
}
