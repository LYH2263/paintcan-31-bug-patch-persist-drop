<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON } from '../api'
const route = useRoute()
const room_id = ref(1)
const coats = ref(null)
const coverage = ref(null)
const touch_mode = ref('merge')
const touch_coverage = ref(null)
const blocks = ref([])
const out = ref(null)
const err = ref(null)
const loaded_run = ref(null)

const addBlock = () => blocks.value.push({ w: 1, h: 1 })
const removeBlock = (i) => blocks.value.splice(i, 1)

const buildBody = (persist) => ({
  room_id: room_id.value,
  persist,
  coats: coats.value ?? null,
  coverage: coverage.value ?? null,
  touch_up_mode: touch_mode.value,
  touch_up_coverage: touch_mode.value === 'separate' ? (touch_coverage.value ?? null) : null,
  touch_ups: blocks.value.map(b => ({ w: Number(b.w), h: Number(b.h) })),
})

const run = async () => {
  loaded_run.value = null
  err.value = null
  try {
    out.value = await postJSON('/api/estimate', buildBody(true))
  } catch (e) {
    out.value = null
    err.value = '估算被拒绝：补刷块宽高须为正整数，本次未保存记录。'
  }
}

const prefillFromRun = async (id) => {
  // 历史回放：带回当时钉选的补刷块、模式与结果，不按房间现状重算
  const r = await getJSON(`/api/history/${id}`)
  loaded_run.value = r.id
  const inp = r.input_json || {}
  room_id.value = inp.room_id
  coats.value = inp.coats ?? null
  coverage.value = inp.coverage ?? null
  touch_mode.value = inp.touch_up_mode || 'merge'
  touch_coverage.value = inp.touch_up_coverage ?? null
  blocks.value = (inp.touch_ups || []).map(b => ({ w: b.w, h: b.h }))
  out.value = r.result_json
}

onMounted(() => { if (route.query.run) prefillFromRun(Number(route.query.run)) })
</script>
<template><div class="page"><h1>估漆工作台</h1>
<label>房间ID <input v-model.number="room_id" /></label>
<label>遍数 <input v-model.number="coats" placeholder="默认" style="width:5rem" /></label>
<label>墙面涂布率 m²/L <input v-model.number="coverage" placeholder="默认" style="width:6rem" /></label>

<section style="margin-top:1rem">
  <h2>局部补刷</h2>
  <label><input type="radio" value="merge" v-model="touch_mode" /> 补刷面积并入墙面净面积换漆</label>
  <label style="margin-left:1rem"><input type="radio" value="separate" v-model="touch_mode" /> 按补刷专用涂布率单列加升数</label>
  <label v-if="touch_mode === 'separate'" style="margin-left:1rem">补刷涂布率 m²/L
    <input v-model.number="touch_coverage" placeholder="同墙面" style="width:6rem" />
  </label>
  <table v-if="blocks.length" style="margin-top:0.5rem">
    <tr><th>宽(m)</th><th>高(m)</th><th>面积(m²)</th><th></th></tr>
    <tr v-for="(b, i) in blocks" :key="i">
      <td><input v-model="b.w" type="number" min="1" step="1" style="width:5rem" /></td>
      <td><input v-model="b.h" type="number" min="1" step="1" style="width:5rem" /></td>
      <td>{{ (Number(b.w) || 0) * (Number(b.h) || 0) }}</td>
      <td><button @click="removeBlock(i)">删除</button></td>
    </tr>
  </table>
  <p style="margin-top:0.5rem"><button @click="addBlock">添加补刷块</button></p>
  <p class="hint">补刷块宽高须为正整数，否则本次估算将被拒绝且不留记录。</p>
</section>

<button @click="run" style="font-size:1.1rem">估算</button>
<p v-if="err" class="hint" style="color:#b3261e">{{ err }}</p>
<p v-if="loaded_run" class="hint">已载入历史记录 #{{ loaded_run }}（钉选参数），重新估算将生成新记录。</p>
<div v-if="out" style="margin-top:1rem">
  <p>墙面净 {{ out.net_m2 }} m² · {{ out.coats }} 遍 @ {{ out.coverage }} m²/L</p>
  <template v-if="out.touch_ups && out.touch_ups.length">
    <p>补刷 {{ out.touch_up_m2 }} m²（{{ out.touch_up_mode === 'merge' ? '并入墙面' : '单列' }}）</p>
    <p>墙面 {{ out.wall_liters }} L · 补刷 {{ out.touch_up_liters }} L ·
      合计 <span class="hero-num">{{ out.total_liters }} L</span></p>
  </template>
  <p v-else>需漆 <span class="hero-num">{{ out.liters }} L</span></p>
</div>
</div></template>
