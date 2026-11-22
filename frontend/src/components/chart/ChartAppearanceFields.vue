<template>
  <div class="appearance-fields">
    <label class="text-field">
      图表标题
      <input type="text" :value="value.title" :placeholder="automaticTitle" maxlength="60"
        @input="change('title', $event.target.value)">
    </label>
    <label class="text-field">
      横轴名称
      <input type="text" :value="value.xLabel" :placeholder="automaticXLabel" maxlength="60"
        @input="change('xLabel', $event.target.value)">
    </label>
    <label class="text-field">
      纵轴名称
      <input type="text" :value="value.yLabel" :placeholder="automaticYLabel" maxlength="60"
        @input="change('yLabel', $event.target.value)">
    </label>
    <div class="figure-options">
      <label class="checkbox-field">
        <input type="checkbox" :checked="value.showLegend" @change="change('showLegend', $event.target.checked)">
        显示图例
      </label>
      <label class="checkbox-field">
        <input type="checkbox" :checked="value.showValues" @change="change('showValues', $event.target.checked)">
        显示数值
      </label>
    </div>
    <label v-if="value.showLegend && !perBar" class="text-field">
      图例名称
      <input type="text" :value="value.legendLabel" :placeholder="automaticLegend" maxlength="60"
        @input="change('legendLabel', $event.target.value)">
    </label>
    <label v-if="value.showLegend" class="text-field">
      图例标题
      <input type="text" :value="value.legendTitle" maxlength="60"
        @input="change('legendTitle', $event.target.value)">
    </label>
    <label v-if="value.showLegend" class="text-field">
      图例位置
      <select :value="value.legendPosition" @change="change('legendPosition', $event.target.value)">
        <option value="auto">自动</option>
        <option value="top-right">右上角</option>
        <option value="top-left">左上角</option>
        <option value="bottom">图表下方</option>
      </select>
    </label>
  </div>
</template>

<script>
export default {
  name: 'ChartAppearanceFields',
  props: {
    value: { type: Object, required: true },
    automaticTitle: { type: String, default: '' },
    automaticLegend: { type: String, default: '' },
    automaticXLabel: { type: String, default: '' },
    automaticYLabel: { type: String, default: '' },
    perBar: Boolean,
  },
  methods: {
    change(key, value) { this.$emit('change', { [key]: value }) },
  },
}
</script>

<style scoped>
.appearance-fields { display: grid; gap: 7px; font-size: 13px; }
.text-field {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  color: #435774;
}
input[type='text'], select {
  width: 100%;
  box-sizing: border-box;
  height: 30px;
  padding: 4px 7px;
  border: 1px solid #cdd9e9;
  border-radius: 5px;
  color: #172942;
  background: #fff;
  font: inherit;
  text-overflow: ellipsis;
}
.figure-options { display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 3px 0; }
.checkbox-field { display: flex; align-items: center; gap: 5px; cursor: pointer; }
.checkbox-field input { margin: 0; accent-color: #356fe5; }
</style>
