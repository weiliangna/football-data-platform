import axios from "axios"

/**
 * Single HTTP boundary for the new data-terminal pages.
 * The browser always talks to the same-origin /api proxy; production hosts
 * and credentials stay outside the bundle.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 20000),
  withCredentials: true,
  headers: { Accept: "application/json" },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    const message = status === 401 ? "登录状态已失效" : status === 403 ? "暂无访问权限" : "网络请求失败"
    return Promise.reject(Object.assign(error, { userMessage: message }))
  },
)

export function unwrap(response) {
  const payload = response?.data
  if (payload?.code !== undefined && payload.code !== 200) {
    throw new Error(payload.msg || "接口返回失败")
  }
  return payload?.data ?? payload
}
