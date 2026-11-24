<template>
  <div class="view-fields">
    <label>来源<view-source-select :value="spec.source" :groups="groups" @input="changeSource" /></label>
    <component :is="fieldsComponent" v-if="fields.length" :key="spec.source + ':' + spec.mode" :spec="spec" :fields="fields" />
  </div>
</template>

<script>
import ViewSourceSelect from './ViewSourceSelect.vue'
import ViewFilterFields from './ViewFilterFields.vue'
import ViewColumnTransformFields from './ViewColumnTransformFields.vue'
import ViewComputeFields from './ViewComputeFields.vue'
import ViewBinFields from './ViewBinFields.vue'
import ViewOrderFields from './ViewOrderFields.vue'
import { newViewSpec } from '../../data/viewWorkspace.js'

const editors = {
  filter: ViewFilterFields, project: ViewColumnTransformFields, compute: ViewComputeFields,
  bin: ViewBinFields, unpivot: ViewColumnTransformFields, dedupe: ViewOrderFields, window: ViewOrderFields,
}

export default {
  name: 'ViewTransformFields',
  components: { ViewSourceSelect },
  props: {
    spec: { type: Object, required: true }, groups: { type: Array, required: true },
    metadata: { type: Object, required: true },
  },
  computed: {
    fields() { return this.metadata[this.spec.source] || [] },
    fieldsComponent() { return editors[this.spec.mode] },
  },
  methods: {
    changeSource(value) {
      Object.assign(this.spec, newViewSpec(this.spec.mode), { source: value })
      this.$emit('source-selected', value)
    },
  },
}
</script>
