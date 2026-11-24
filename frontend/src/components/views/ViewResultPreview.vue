<template>
  <div class="result">
    <div v-if="result.columns?.length" class="result-scroll">
      <table>
        <thead><tr><th v-for="column in result.columns" :key="column.name" scope="col">{{ column.name }}</th></tr></thead>
        <tbody>
          <tr v-for="(row, index) in result.rows" :key="index">
            <td v-for="(value, col) in row" :key="col">{{ value ?? 'NULL' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="result.rows && !result.rows.length" class="view-note">当前查询没有返回记录。</p>
    <p v-else-if="result.truncated" class="view-note">显示前 20 行。</p>
    <details v-if="result.query" :open="!result.columns">
      <summary>查询 SQL</summary>
      <pre>{{ result.query }}</pre>
    </details>
  </div>
</template>

<script>
export default {
  name: 'ViewResultPreview',
  props: { result: { type: Object, required: true } },
}
</script>

<style scoped>
.result { display: grid; gap: 9px; min-width: 0; }
.result-scroll { overflow: auto; max-height: 340px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { padding: 7px 9px; text-align: left; border: 1px solid #dde6f0; overflow-wrap: anywhere; }
th { position: sticky; top: 0; background: #eff4f9; }
summary { color: #285a98; cursor: pointer; }
pre { overflow: auto; margin: 8px 0 0; padding: 10px; border-radius: 6px; background: #f0f4f9; font-size: 12px; }
</style>
