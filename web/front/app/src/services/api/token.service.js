import { backendClient } from "./axios.clients";
import jwtService from "@/services/jwt/jwt.service";
import { jwtDecode } from "jwt-decode";
import logger from '@/common/helpers/logger';
import { useAuthStore } from '@/stores/auth';

// Обновление access-токена. Результат:
//   строка — новый токен;
//   false  — сервер отклонил refresh-токен: сессия закончилась, нужен вход;
//   null   — сервер недоступен: сессию не трогаем, попробуем позже.
let refreshing = null;

async function _refreshToken() {
  const refreshToken = jwtService.getRefreshToken();
  if (!refreshToken) return false;
  logger.info("Токен истёк. Обновление токена...");

  try {
    const result = await backendClient.post("/api/v1/refresh/", { refresh_token: refreshToken });
    const token = result.data?.access_token;
    if (!token) return false;
    useAuthStore().access_token = token;
    jwtService.saveAccessToken(token);
    logger.info(`Получен новый токен до ${new Date(jwtDecode(token).exp * 1000).toLocaleString()}`);
    return token;
  } catch (error) {
    const status = error.response?.status;
    if (status && status >= 400 && status < 500) return false;
    logger.error("Сервер недоступен, токен не обновлён", error);
    return null;
  }
}

export function handleTokenRefresh() {
  if (!refreshing) {
    refreshing = _refreshToken().finally(() => { refreshing = null; });
  }
  return refreshing;
}
