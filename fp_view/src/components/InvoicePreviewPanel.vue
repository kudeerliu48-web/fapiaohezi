<template>
  <div class="panel preview-panel">
    <div class="preview-header">
      <span class="preview-title">发票原件</span>
      <span class="preview-sub" v-if="previewItem">{{ previewItem.filename }}</span>
    </div>

    <div class="preview-body" v-if="previewItem">
      <img class="preview-img" :src="fileUrl(previewItem)" alt="invoice" />
    </div>

    <div class="preview-empty" v-else>
      <i class="el-icon-picture-outline"></i>
      <p>请从左侧文件列表选择发票</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InvoicePreviewPanel',
  props: {
    previewItem: {
      type: Object,
      default: null,
    },
    fileUrl: {
      type: Function,
      required: true,
    },
  },
}
</script>
