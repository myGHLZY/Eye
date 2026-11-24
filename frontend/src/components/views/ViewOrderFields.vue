<template>
  <div class="view-fields">
    <template v-if="dedupe">
      <label>去重方式
        <select v-model="spec.method">
          <option value="distinct">完全重复的行只保留一条</option><option value="latest">按字段分组，每组保留最新记录</option>
        </select>
      </label>
    </template>
    <template v-else>
      <label>计算粒度
        <select :value="spec.scope" @change="changeScope($event.target.value)">
          <option value="group">按组汇总（GROUP BY）</option><option value="detail">逐行计算（保留明细）</option>
        </select>
      </label>
      <label>计算方式
        <select v-model="spec.operation">
          <option v-if="grouped" value="summary">仅分组汇总</option>
          <option value="rank">排名（并列占名次）</option><option value="denseRank">连续排名（并列不跳号）</option>
          <option value="runningSum">{{ grouped ? '累计汇总值' : '累计合计' }}</option>
          <option value="runningCount">{{ grouped ? '累计组数' : '累计记录数' }}</option>
        </select>
      </label>
    </template>

    <template v-if="grouped">
      <view-field-checks :value="spec.keys" :fields="fields" label="分组字段（每组一行）" @input="changeGroupKeys" />
      <div class="view-pair">
        <label>汇总方式
          <select v-model="spec.aggregation">
            <option value="sum">合计（SUM）</option><option value="average">平均值（AVG）</option>
            <option value="count">记录数（COUNT）</option><option value="min">最小值（MIN）</option>
            <option value="max">最大值（MAX）</option>
          </select>
        </label>
        <label v-if="spec.aggregation !== 'count'">
          汇总数值字段<view-field-select v-model="spec.metric" :fields="numericFields" />
        </label>
      </div>
      <label>汇总列名<input v-model.trim="spec.summaryAlias" maxlength="64" placeholder="例如 总工时"></label>
      <template v-if="spec.operation !== 'summary'">
        <label>排序依据
          <view-field-select v-model="spec.order" :fields="groupFields" placeholder="汇总值" />
        </label>
        <view-field-checks v-if="groupFields.length > 1" v-model="spec.partitionKeys" :fields="groupFields"
          label="分别计算的字段（可选）" />
      </template>
    </template>

    <template v-else-if="!dedupe || spec.method === 'latest'">
      <view-field-checks v-model="spec.keys" :fields="fields"
        :label="dedupe ? '按哪些字段判定同组' : '分别计算的字段（可选）'" />
      <div class="view-pair">
        <label>{{ dedupe ? '判断最新的字段' : '排序字段' }}
          <view-field-select v-model="spec.order" :fields="fields" />
        </label>
        <label v-if="dedupe || running">并列时的排序字段
          <view-field-select v-model="spec.tie" :fields="tieFields" placeholder="可选，例如唯一编号" />
        </label>
      </div>
      <p v-if="dedupe" class="view-note">保留排序字段最大的记录；字段相同时可用唯一编号决定保留哪条。</p>
    </template>

    <template v-if="!dedupe && spec.operation !== 'summary'">
      <label>排序方向
        <select v-model="spec.direction"><option value="desc">从大到小</option><option value="asc">从小到大</option></select>
      </label>
      <label v-if="!grouped && spec.operation === 'runningSum'">累计数值字段
        <view-field-select v-model="spec.metric" :fields="numericFields" />
      </label>
      <label>{{ grouped ? '计算结果列名' : '新列名' }}<input v-model.trim="spec.alias" maxlength="64" placeholder="例如 名次或累计工时"></label>
    </template>
  </div>
</template>

<script>
import ViewFieldChecks from './ViewFieldChecks.vue'
import ViewFieldSelect from './ViewFieldSelect.vue'
import { numericColumn } from '../../data/viewWorkspace.js'

export default {
  name: 'ViewOrderFields',
  components: { ViewFieldChecks, ViewFieldSelect },
  props: { spec: { type: Object, required: true }, fields: { type: Array, required: true } },
  computed: {
    dedupe() { return this.spec.mode === 'dedupe' },
    grouped() { return !this.dedupe && this.spec.scope === 'group' },
    running() { return ['runningSum', 'runningCount'].includes(this.spec.operation) },
    numericFields() { return this.fields.filter(numericColumn) },
    tieFields() { return this.fields.filter(field => field.name !== this.spec.order) },
    groupFields() { return this.fields.filter(field => this.spec.keys.includes(field.name)) },
  },
  methods: {
    changeScope(scope) {
      this.spec.scope = scope
      this.spec.order = ''
      this.spec.tie = ''
      this.spec.partitionKeys = []
      if (scope === 'detail' && this.spec.operation === 'summary') this.spec.operation = 'rank'
    },
    changeGroupKeys(keys) {
      this.spec.keys = keys
      if (!keys.includes(this.spec.order)) this.spec.order = ''
      this.spec.partitionKeys = keys.length < 2 ? [] : this.spec.partitionKeys.filter(name => keys.includes(name))
    },
  },
}
</script>
