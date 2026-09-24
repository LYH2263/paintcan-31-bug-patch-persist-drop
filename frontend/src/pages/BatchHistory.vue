<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
const totalOf = (h) => {
  try {
    const r = JSON.parse(h.result_json)
    // 写入即钉选：含补刷的记录取 total_liters（墙面+补刷），无补刷记录取 liters
    if (r.total_liters != null) return r.total_liters
    if (r.wall_liters != null && r.touch_up_liters != null) {
      return Number(r.wall_liters) + Number(r.touch_up_liters)
    }
    return r.liters
  } catch { return null }
}
</script>
<template><div class="page"><h1>估算记录</h1><table>
  <tr><th>#</th><th>时间</th><th>合计升数</th><th></th></tr>
  <tr v-for="h in items" :key="h.id">
    <td>#{{ h.id }}</td><td>{{ h.created_at }}</td><td>{{ totalOf(h) }} L</td>
    <td><router-link :to="`/estimate?run=${h.id}`">打开</router-link></td>
  </tr>
</table></div></template>
