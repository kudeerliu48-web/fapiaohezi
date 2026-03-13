<template>
  <div class="json-viewer">
    <div class="json-toolbar">
      <span class="json-title">{{ title }}</span>
      <el-button size="mini" type="text" @click="copyJson">复制JSON</el-button>
    </div>
    <pre class="json-content">{{ prettyJson }}</pre>
  </div>
</template>

<script>
export default {
  name: 'JsonViewer',
  props: {
    title: {
      type: String,
      default: 'JSON',
    },
    value: {
      type: [Object, Array, String, Number, Boolean, null],
      default: null,
    },
  },
  computed: {
    prettyJson() {
      if (this.value === null || this.value === undefined || this.value === '') {
        return '{}'
      }
      if (typeof this.value === 'string') {
        try {
          return JSON.stringify(JSON.parse(this.value), null, 2)
        } catch (_) {
          return this.value
        }
      }
      try {
        return JSON.stringify(this.value, null, 2)
      } catch (e) {
        return String(this.value)
      }
    },
  },
  methods: {
    async copyJson() {
      try {
        await navigator.clipboard.writeText(this.prettyJson)
        this.$message.success('JSON 已复制')
      } catch (e) {
        this.$message.error('复制失败，请手动复制')
      }
    },
  },
}
</script>

<style scoped lang="scss">
.json-viewer {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.json-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid #ebeef5;
  background: #f8fafc;
}

.json-title {
  font-size: 12px;
  color: #606266;
}

.json-content {
  margin: 0;
  padding: 10px;
  max-height: 240px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
  color: #303133;
  background: #fbfdff;
}
</style>

