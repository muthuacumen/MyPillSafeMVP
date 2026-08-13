import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, type LoginPayload, type RegisterPayload } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';

export type RegisterOutcome = 'signed_in' | 'pending_approval';

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, setUser, setToken, logout: storeLogout } = useAuthStore();

  /**
   * Resolves to 'pending_approval' when the account was created but is not
   * usable yet -- NOTHING is stored and there is no navigation, because there
   * is no session to navigate into. The caller renders the waiting state.
   */
  const register = useCallback(async (payload: RegisterPayload): Promise<RegisterOutcome> => {
    const { data, status } = await authApi.register(payload);
    if (status === 202 || !('access_token' in data)) {
      return 'pending_approval';
    }
    setToken(data.access_token);
    const { data: me } = await authApi.me();
    setUser(me);
    navigate('/dashboard');
    return 'signed_in';
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
