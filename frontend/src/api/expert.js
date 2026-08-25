export async function getExpertList() {
  const response = await fetch('/api/expert/list')

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const result = await response.json()

  if (result.code !== 200) {
    throw new Error(result.msg || '专家数据读取失败')
  }

  return result.data || []
}
