import { AxiosError } from "axios";

export class ApiError extends Error {
  constructor(message, response) {
    super(message);
    this.response = response;
  }
}

// Понятный текст ошибки: сообщение сервера, ошибка проверки полей или отсутствие связи
const messageOf = (e) => {
  const detail = e.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return `Проверьте поле «${detail[0].loc?.at(-1)}»: ${detail[0].msg}`;
  if (e.code === "ERR_NETWORK" || !e.response) return "Нет связи с сервером";
  if (e.response.status >= 500) return "Ошибка сервера, попробуйте позже";
  return e.message;
};

export function getApiError(e) {
  if (e instanceof AxiosError) {
    return new ApiError(messageOf(e), e.response);
  }
  return new ApiError(e.message, e.response);
}
