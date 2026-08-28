/** TODO_API: these endpoints are not present in the current FastAPI app. */
export const monitorService = {
  async getPlatforms() { return { data: [], source: "mock" } },
  async getTasks() { return { data: [], source: "mock" } },
  async getErrors() { return { data: [], source: "mock" } },
}
