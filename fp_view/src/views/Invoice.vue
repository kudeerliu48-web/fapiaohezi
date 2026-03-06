<template>
  <div class="invoice-page">
    <div class="page-header">
      <h1 class="page-title">发票整理</h1>
      <p class="page-desc">智能发票识别与管理</p>
    </div>

    <div class="manual">
      <div class="top">
        <div class="left" style="flex: 2;">
          <div class="glass-card h-full relative">
            <transition name="fade">
              <div v-if="recognizing" class="upload-mask">
                <i class="el-icon-loading"></i>
                <div class="txt">智能识别中，请稍候...</div>
              </div>
            </transition>

            <el-tabs v-model="activeTab" class="invoice-tabs">
              <el-tab-pane label="手动上传" name="upload">
                <div class="panel-inner">
                  <div
                    class="upload-zone"
                    :class="{ 'is-dragover': isDragover, 'has-files': fileList.length }"
                    @dragover.prevent="isDragover = true"
                    @dragleave.prevent="isDragover = false"
                    @drop.prevent="onDrop"
                    @click="onClickUploadZone"
                  >
                    <input ref="fileInput" class="upload-input" type="file" multiple @change="onInputChange" accept="image/*,.pdf" />
                    <div class="upload-icon-wrap">
                      <i class="el-icon-upload upload-icon"></i>
                      <div class="upload-text">
                        <span>拖拽文件到此处 或 <em>点击选择</em></span>
                        <span class="upload-hint">支持 JPG/PNG/PDF (最多 10 张)</span>
                      </div>
                    </div>
                  </div>

                  <div class="action-row">
                    <el-button type="primary" size="medium" round icon="el-icon-top" @click="submitUpload" :loading="uploading" :disabled="!fileList.length">立即上传</el-button>
                    <el-button size="medium" round @click="clearFileList" :disabled="!fileList.length">清空</el-button>
                    <el-button type="success" size="medium" round icon="el-icon-cpu" @click="recognizeSelected" :disabled="recognizing">一键识别</el-button>
                  </div>

                  <div class="server-files">
                    <div class="server-files-title">最近上传 (点击预览)</div>
                    <div class="scroll-list">
                      <div
                        v-for="item in topFiles"
                        :key="item.id"
                        class="server-file-item"
                        :class="{ active: previewItem && previewItem.id === item.id }"
                        @click="previewRow(item)"
                      >
                        <i :class="isPdfName(item.filename) ? 'el-icon-document' : 'el-icon-picture-outline'"></i>
                        <div class="file-info">
                          <span class="name">{{ item.filename }}</span>
                          <span class="time">{{ formatDate(item.upload_time) }}</span>
                        </div>
                        <el-button type="text" icon="el-icon-delete" class="del-btn" @click.stop="deleteRow(item)" />
                      </div>
                      <div v-if="!serverLoading && !serverFileList.length" class="server-files-empty">暂无文件记录</div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="邮箱推送" name="email">
                <div class="panel-inner email-panel">
                  <div class="email-content-wrapper">
                    <el-form :model="emailForm" label-position="top" class="email-form-box">
                      <el-form-item label="抓取范围">
                        <el-select v-model="emailForm.rangeKey" placeholder="请选择范围" style="width: 100%">
                          <el-option label="近7天" value="7d" />
                          <el-option label="近1个月" value="1m" />
                          <el-option label="近3个月" value="3m" />
                          <el-option label="近半年" value="6m" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="电子邮箱">
                        <el-input v-model="emailForm.mailbox" placeholder="请输入邮箱地址" />
                      </el-form-item>
                    <el-form-item label="IMAP 授权码">
                      <el-input
                        ref="authInput"
                        v-model="emailForm.authCode"
                        placeholder="请输入授权码"
                        show-password
                      />
                    </el-form-item>
                    <div class="email-actions">
                      <el-button
                        type="primary"
                        round
                        @click="startEmailPush"
                        :loading="emailPushing"
                      >
                        提取邮件附件
                      </el-button>
                      <el-button
                        type="success"
                        round
                        @click="recognizeSelected"
                        :loading="recognizing"
                        :disabled="!tableList.length"
                      >
                        一键识别
                      </el-button>
                    </div>
                    </el-form>
                  </div>

                  <div class="email-logs-container">
                    <div class="email-logs-title">
                      <span>处理日志</span>
                      <span class="log-count" v-if="emailLogs.length > 0">{{ emailLogs.length }} 条</span>
                    </div>
                    <div class="email-logs-body">
                      <div v-if="!emailLogs.length" class="email-log-empty">
                        <i class="el-icon-document-copy"></i>
                        <span>暂无日志记录</span>
                      </div>
                      <div v-else class="email-logs-stats">
                        <div class="stat-item">
                          <div class="stat-value success">{{ successCount }}</div>
                          <div class="stat-label">成功</div>
                        </div>
                        <div class="stat-item">
                          <div class="stat-value warning">{{ processingCount }}</div>
                          <div class="stat-label">处理中</div>
                        </div>
                        <div class="stat-item">
                          <div class="stat-value danger">{{ failCount }}</div>
                          <div class="stat-label">失败</div>
                        </div>
                        <div class="stat-item">
                          <div class="stat-value info">{{ emailLogs.length }}</div>
                          <div class="stat-label">总计</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 进度条：仅在一键识别阶段显示 -->
                  <div class="email-progress" v-if="recognizing">
                    <el-progress
                      :percentage="emailProgressPercent"
                      :status="emailProgressStatus"
                      :stroke-width="8"
                      :show-text="true"
                    />
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>

        <div class="right" style="flex: 3;">
          <div class="preview-card h-full">
            <div class="preview-header">
              <div class="preview-title">
                <span class="status-dot"></span>
                <span>原件预览</span>
                <span class="filename-tag" v-if="previewItem">{{ previewItem.filename }}</span>
              </div>
              <el-button v-if="previewItem" type="text" icon="el-icon-download" @click="downloadRow(previewItem)">下载原件</el-button>
            </div>
            <div class="preview-body">
              <transition name="el-fade-in">
                <div v-if="previewItem" :key="previewItem.id" class="img-wrapper">
                  <img :src="fileUrl(previewItem)" alt="invoice" />
                </div>
                <div v-else class="empty-preview">
                  <i class="el-icon-monitor"></i>
                  <p>请选择左侧文件进行预览</p>
                </div>
              </transition>
            </div>
          </div>
        </div>
      </div>

      <div class="bottom">
        <div class="white-card list-panel">
          <div class="list-header">
            <h3 class="title">结构化发票清单</h3>
            <div class="tools">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索关键词..."
                prefix-icon="el-icon-search"
                size="small"
                style="width: 240px; margin-right: 12px;"
                clearable
                @input="onSearch"
              />
              <el-button type="success" size="small" icon="el-icon-document" @click="exportExcel">导出 Excel</el-button>
              <el-button type="danger" size="small" icon="el-icon-delete" :disabled="!selectedRows.length" @click="batchDelete">批量删除</el-button>
            </div>
          </div>

          <el-table
            :data="tableList"
            v-loading="tableLoading"
            stripe
            border
            @selection-change="onSelectionChange"
            @row-click="previewRow"
            height="400"
            class="invoice-table"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="invoice_number" label="发票号码" width="160" sortable />
            <el-table-column prop="buyer" label="购买方" show-overflow-tooltip min-width="180" />
            <el-table-column prop="seller" label="销售方" show-overflow-tooltip min-width="180" />
            <el-table-column prop="invoice_amount" label="价税合计" width="120" align="right" sortable>
              <template slot-scope="scope">
                <span class="money-text">{{ formatMoney(scope.row.invoice_amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="开票日期" width="120" align="center" sortable>
              <template slot-scope="scope">
                {{ formatDate(scope.row.invoice_date || scope.row.upload_time) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template slot-scope="scope">
                <el-tag :type="getStatusType(scope.row.recognition_status)" size="small">
                  {{ getStatusText(scope.row.recognition_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template slot-scope="scope">
                <el-button type="text" class="view-btn" @click.stop="previewRow(scope.row)">查看</el-button>
                <el-button type="text" class="red-btn" @click.stop="deleteRow(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              @current-change="onPageChange"
              :current-page="page"
              :page-size="limit"
              layout="total, prev, pager, next"
              :total="total"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { invoiceAPI } from '@/api/invoice'
import { authAPI } from '@/api/auth'

export default {
  name: 'Invoice',
  data() {
    return {
      activeTab: 'upload',
      fileList: [],
      isDragover: false,
      uploading: false,
      serverLoading: false,
      tableLoading: false,
      searchKeyword: '',
      page: 1,
      limit: 10,
      total: 0,
      serverFileList: [],
      tableList: [],
      selectedRows: [],
      previewItem: null,
      recognizing: false,
      recognizeJobId: '',
      emailForm: { rangeKey: '7d', mailbox: '', authCode: '' },
      emailPushing: false,
      emailJobId: '',
      emailStatus: {},
      emailLogs: [],
      emailProgressPercent: 0,
      emailProgressStatus: null,
      emailProgressText: '准备中...',
      // 识别统计
      successCount: 0,
      processingCount: 0,
      failCount: 0,
    }
  },
  computed: {
    topFiles() { return (this.serverFileList || []).slice(0, 20) }
  },
  watch: {
    // 监听识别状态，实时更新统计
    recognizing(newVal) {
      if (newVal) {
        this.updateRecognizeStats();
      }
    },
    // 监听表格数据变化
    tableList() {
      if (this.recognizing) {
        this.updateRecognizeStats();
      }
    }
  },
  async mounted() {
    const uid = this.getUserId();
    console.log('页面加载，用户 ID:', uid);
    if (!uid) {
      console.warn('用户未登录，请先登录');
      // 不自动跳转，让用户看到提示
    } else {
      await this.refreshAll(true);
      await this.initEmailForm();
    }
  },
  methods: {
    getUserId() {
      const user = JSON.parse(localStorage.getItem('user'));
      return user && user.id;
    },
    async initEmailForm() {
      const userId = this.getUserId();
      if (!userId) return;
      try {
        const res = await authAPI.getUserInfo(userId);
        if (res.data.data.email) this.emailForm.mailbox = res.data.data.email;
      } catch (e) { console.error(e) }
    },
    isPdfName(name) { return /\.pdf$/i.test(name || '') },
    formatMoney(v) { return v ? `¥${Number(v).toFixed(2)}` : '-' },
    formatDate(v) { return v ? String(v).slice(0, 10) : '-' },
    getStatusType(status) {
      const types = { 0: 'info', 1: 'success', 2: 'danger' };
      return types[status] || 'info';
    },
    getStatusText(status) {
      const texts = { 0: '待识别', 1: '已识别', 2: '识别失败' };
      return texts[status] || '未知';
    },
    updateRecognizeStats() {
      // 实时更新统计数据
      this.successCount = this.tableList.filter(item => item.recognition_status === 1).length;
      this.processingCount = this.tableList.filter(item => item.recognition_status === 0).length;
      this.failCount = this.tableList.filter(item => item.recognition_status === 2).length;
    },
    fileUrl(row) {
      const uid = this.getUserId();
      const name = row.processed_filename || row.saved_filename;
      const folder = row.processed_filename ? 'processed' : 'uploads';
      return `http://localhost:8000/files/${uid}/${folder}/${encodeURIComponent(name)}`;
    },
    previewRow(row) { this.previewItem = row },
    onClickUploadZone() { 
      const uid = this.getUserId();
      if (!uid) {
        this.$message.error('请先登录');
        return;
      }
      this.$refs.fileInput.click() 
    },
    onDrop(e) {
      this.isDragover = false;
      const files = e.dataTransfer.files;
      for (let i = 0; i < files.length; i++) {
        if (this.fileList.length < 10) this.fileList.push({ name: files[i].name, raw: files[i] });
      }
    },
    onInputChange(e) {
      const files = e.target.files;
      for (let i = 0; i < files.length; i++) {
        if (this.fileList.length < 10) this.fileList.push({ name: files[i].name, raw: files[i] });
      }
      console.log('已选择文件:', this.fileList.map(f => f.name));
      e.target.value = '';
    },
    clearFileList() { this.fileList = [] },
    async submitUpload() {
      const uid = this.getUserId();
      if (!uid) {
        this.$message.error('请先登录');
        return;
      }
      
      if (!this.fileList.length) {
        this.$message.warning('请选择要上传的文件');
        return;
      }
      
      console.log('=== 开始上传 ===');
      console.log('用户 ID:', uid);
      console.log('文件列表:', this.fileList.map(f => ({ name: f.name, size: f.raw.size, type: f.raw.type })));
      
      this.uploading = true;
      try {
        let successCount = 0;
        let failCount = 0;
        
        for (const f of this.fileList) {
          try {
            console.log('上传文件:', f.name);
            const res = await invoiceAPI.uploadFile(uid, f.raw);
            console.log('上传响应:', res.data);
            successCount++;
          } catch (err) {
            console.error(`上传失败 ${f.name}:`, err);
            console.error('错误详情:', err.response?.data);
            failCount++;
          }
        }
        
        console.log('=== 上传完成 ===');
        console.log(`成功：${successCount}, 失败：${failCount}`);
        
        if (successCount > 0) {
          this.$message.success(`上传成功 ${successCount} 个文件`);
          this.clearFileList();
          console.log('开始刷新数据...');
          await this.refreshAll(true);
        } else {
          this.$message.error('所有文件上传失败，请检查后端服务');
        }
      } catch (e) { 
        console.error('上传异常:', e);
        this.$message.error('上传失败：' + (e.response?.data?.message || '网络错误'));
      } finally { 
        this.uploading = false 
      }
    },
    async refreshAll(reset = false) {
      const uid = this.getUserId();
      if (!uid) {
        console.warn('用户未登录，无法加载数据');
        return;
      }
      if (reset) this.page = 1;
      this.serverLoading = this.tableLoading = true;
      try {
        const [fRes, tRes] = await Promise.all([
          invoiceAPI.getInvoices(uid, 1, 50, '', false),
          invoiceAPI.getInvoices(uid, this.page, this.limit, this.searchKeyword, true)
        ]);
        
        console.log('发票 API 返回数据:', fRes.data);
        console.log('已识别发票 API 返回数据:', tRes.data);
        
        // 尝试不同的数据结构
        this.serverFileList = fRes.data?.data?.invoices || fRes.data?.invoices || [];
        this.tableList = tRes.data?.data?.invoices || tRes.data?.invoices || [];
        this.total = tRes.data?.data?.total || tRes.data?.total || 0;
        
        console.log('解析后的数据:', {
          serverFileList: this.serverFileList,
          tableList: this.tableList,
          total: this.total
        });
        
        if (!this.previewItem && this.serverFileList.length > 0) this.previewItem = this.serverFileList[0];
        console.log('数据加载成功:', {
          serverFileList: this.serverFileList.length,
          tableList: this.tableList.length
        });
      } catch (e) {
        console.error('加载数据失败:', e);
        this.$message.error('加载数据失败，请检查后端服务');
      } finally { 
        this.serverLoading = this.tableLoading = false; 
      }
    },
    onSearch() { this.refreshAll(true) },
    onPageChange(p) { this.page = p; this.refreshAll(); },
    onSelectionChange(rows) { this.selectedRows = rows },
    downloadRow(row) { window.open(this.fileUrl(row), '_blank') },
    async deleteRow(row) {
      try {
        await this.$confirm('确定删除吗?', '提示', { type: 'warning' });
        await invoiceAPI.deleteInvoice(this.getUserId(), row.id);
        if (this.previewItem?.id === row.id) this.previewItem = null;
        this.refreshAll();
      } catch (e) {}
    },
    async batchDelete() {
      try {
        await this.$confirm('确定批量删除吗?', '提示', { type: 'warning' });
        await invoiceAPI.batchDeleteInvoices(this.getUserId(), this.selectedRows.map(r => r.id));
        this.refreshAll(true);
      } catch (e) {}
    },
    async exportExcel() {
      try {
        const res = await invoiceAPI.exportInvoicesExcel(this.getUserId(), this.searchKeyword);
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement('a');
        a.href = url; a.download = '发票清单.xlsx'; a.click();
      } catch (e) { this.$message.error('导出失败') }
    },
    async recognizeSelected() {
      const userId = this.getUserId();
      if (!userId) {
        this.$message.error('请先登录');
        return;
      }
      
      if (!this.serverFileList.length) {
        this.$message.warning('没有可识别的发票，请先上传文件');
        return;
      }
      
      this.recognizing = true;
      try {
        // 初始化识别进度
        this.emailProgressPercent = 0;
        this.emailProgressStatus = null;
        this.$message.info('开始批量识别...');
        const res = await invoiceAPI.recognizeUnrecognized(userId);
        this.recognizeJobId = res.data.data.job_id;
        this.pollRecognize();
      } catch (e) { 
        this.recognizing = false;
        console.error('识别失败:', e);
        this.$message.error(e.response?.data?.message || '识别失败，请检查后端服务是否正常');
      }
    },
    async pollRecognize() {
      try {
        const res = await invoiceAPI.getRecognizeStatus(this.recognizeJobId);
        const status = res.data.data.status;
        const logs = res.data.data.logs || [];
        
        // 更新日志
        this.emailLogs = logs;
        
        // 根据完成数量更新进度条
        const completedCount = logs.filter(log => log.includes('✅')).length;
        const totalCount = this.serverFileList.length;
        if (totalCount > 0) {
          this.emailProgressPercent = Math.floor((completedCount / totalCount) * 100);
        }
        
        // 实时更新表格数据
        await this.refreshAll(true);
        
        if (status === 'completed') {
          this.emailProgressPercent = 100;
          this.emailProgressStatus = 'success';
          this.recognizing = false;
          this.$message.success('识别完成！');
          this.refreshAll(true);
        } else if (status === 'error') {
          this.emailProgressStatus = 'exception';
          this.recognizing = false;
          this.$message.error('识别过程出错');
        } else if (status === 'running') {
          // 继续轮询
          setTimeout(() => this.pollRecognize(), 1000);
        }
      } catch (e) {
        console.error('轮询状态失败:', e);
        this.recognizing = false;
      }
    },
    async startEmailPush() {
      if (!this.emailForm.authCode) {
        this.$message.error('请先填写 IMAP 授权码');
        this.$nextTick(() => {
          if (this.$refs.authInput && this.$refs.authInput.focus) {
            this.$refs.authInput.focus();
          }
        });
        return;
      }
      this.emailPushing = true;
      try {
        const res = await invoiceAPI.startEmailPush(this.getUserId(), this.emailForm);
        this.emailJobId = res.data.data.job_id;
        this.pollEmail();
      } catch (e) { this.emailPushing = false; }
    },
    async pollEmail() {
      const res = await invoiceAPI.getEmailPushStatus(this.emailJobId);
      this.emailStatus = res.data.data;
      this.emailLogs = this.emailStatus.logs || [];
      if (this.emailStatus.status === 'completed' || this.emailStatus.status === 'error') {
        this.emailPushing = false; this.refreshAll();
      } else { setTimeout(this.pollEmail, 2000); }
    }
  }
}
</script>

<style lang="scss" scoped>
/* 页面基础设置 */
.invoice-page { padding: 24px; background: #f1f5f9; min-height: 100vh; font-family: -apple-system, sans-serif; }
.page-header { margin-bottom: 24px; .page-title { font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; } .page-desc { font-size: 14px; color: #64748b; margin-top: 4px; } }

/* 核心 Top 布局 */
.manual .top { display: flex; gap: 20px; height: 650px; margin-bottom: 24px; }
.h-full { height: 100%; display: flex; flex-direction: column; }
.relative { position: relative; }

/* 识别遮罩 */
.upload-mask {
  position: absolute; inset: 0; background: rgba(255, 255, 255, 0.85); z-index: 100;
  display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 16px;
  i { font-size: 32px; color: #6366f1; margin-bottom: 12px; }
  .txt { color: #6366f1; font-weight: 700; font-size: 15px; }
}

/* 卡片通用样式 */
.glass-card { background: #fff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05); padding: 20px; }
.preview-card { background: #0f172a; border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; }

/* 内部面板布局 */
.panel-inner { height: 100%; display: flex; flex-direction: column; min-height: 0; }
.panel-inner.email-panel {
  gap: 12px;
  overflow-y: auto;
}

.upload-zone {
  position: relative;
  border: 2px dashed #cbd5e1; background: #f8fafc; border-radius: 12px; padding: 25px; text-align: center; cursor: pointer;
  i { font-size: 30px; color: #6366f1; margin-bottom: 8px; }
  .upload-text { font-size: 14px; color: #475569; em { color: #6366f1; font-style: normal; font-weight: 700; } }
  .upload-hint { display: block; font-size: 12px; color: #94a3b8; margin-top: 4px; }
  &:hover { border-color: #6366f1; background: #f1f7ff; }
}

.upload-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

.action-row { margin: 15px 0; display: flex; gap: 8px; .el-button { flex: 1; } }

/* 文件列表 */
.server-files {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  .server-files-title { font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 10px; }
  .scroll-list {
    flex: 1;
    padding-right: 5px;
    max-height: 260px;
    overflow-y: auto;
  }
}

.server-file-item {
  display: flex; align-items: center; padding: 10px; border-radius: 10px; border: 1px solid #f1f5f9; margin-bottom: 8px; cursor: pointer;
  i { color: #6366f1; margin-right: 12px; font-size: 18px; }
  .file-info { flex: 1; .name { font-size: 13px; font-weight: 600; color: #334155; } .time { font-size: 11px; color: #94a3b8; } }
  .del-btn { display: none; }
  &:hover { background: #f8fafc; .del-btn { display: block; } }
  &.active { border-color: #6366f1; background: #eef2ff; }
}

/* 预览区详细样式 */
.preview-header { padding: 15px 20px; background: rgba(255,255,255,0.04); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); }
.preview-title { display: flex; align-items: center; gap: 10px; color: #fff; font-size: 14px; font-weight: 600; .status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; } .filename-tag { color: #94a3b8; font-weight: 400; font-size: 12px; } }
.preview-body { flex: 1; padding: 20px; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle at center, #1e293b, #0f172a); overflow: hidden; }
.img-wrapper { height: 100%; width: 100%; display: flex; justify-content: center; align-items: center; img { max-width: 100%; max-height: 100%; object-fit: contain; box-shadow: 0 25px 50px rgba(0,0,0,0.5); } }
.empty-preview { text-align: center; color: #475569; i { font-size: 40px; margin-bottom: 10px; opacity: 0.3; } }

/* 底部列表 */
.list-panel { padding: 24px; margin-top: 24px; }
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; .title { font-size: 18px; font-weight: 800; margin: 0; } .tools { display: flex; gap: 10px; } }
.money-text { font-weight: 700; color: #1e293b; font-family: 'Consolas', monospace; }
.red-btn { color: #f87171; }
.view-btn { color: #6366f1; margin-right: 8px; }
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }

/* 发票表格美化 */
.invoice-table {
  .el-table__header th {
    background: #f8fafc !important;
    color: #475569;
    font-weight: 700;
    font-size: 13px;
  }
  .el-table__row:hover {
    background: #f1f5f9 !important;
  }
  .el-table__row--striped {
    background: #fafafa;
  }
}

/* 邮箱表单 */
/* 邮箱表单卡片区域 */
.email-content-wrapper {
  flex-shrink: 0;
}

.email-form-box {
  padding: 14px 18px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f5f3ff 0%, #e0f2fe 50%, #ecfdf3 100%);
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(148, 163, 184, 0.25);
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    right: -40px;
    top: -40px;
    width: 140px;
    height: 140px;
    border-radius: 50%;
    background: radial-gradient(circle at center, rgba(129, 140, 248, 0.35), transparent 60%);
    pointer-events: none;
  }
  &::after {
    content: '';
    position: absolute;
    left: -60px;
    bottom: -60px;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    background: radial-gradient(circle at center, rgba(52, 211, 153, 0.25), transparent 60%);
    pointer-events: none;
  }
  ::v-deep .el-form-item {
    margin-bottom: 10px;
  }
  ::v-deep .el-form-item__label {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
  }
}

/* 邮箱按钮行：两按钮并排且风格统一 */
.email-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  ::v-deep .el-button {
    flex: 1;
    height: 38px;
    padding: 0 12px;
    font-size: 14px;
    font-weight: 600;
  }
  ::v-deep .el-button--primary {
    border-radius: 999px;
  }
  ::v-deep .el-button--success {
    border-radius: 999px;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    border: none;
    color: #fff;
  }
}

/* 邮箱日志小框 */
.email-logs-container {
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 24px rgba(148, 163, 184, 0.3);
  overflow: hidden;
  max-height: 200px;
  display: flex;
  flex-direction: column;
  .email-logs-title {
    padding: 12px 16px;
    background: linear-gradient(90deg, #eef2ff, #e0f2fe);
    font-size: 13px;
    font-weight: 600;
    color: #475569;
    border-bottom: 1px solid #e2e8f0;
    flex-shrink: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    .log-count {
      background: #6366f1;
      color: #fff;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
    }
  }
  .email-logs-body {
    padding: 12px 16px;
    overflow-y: auto;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #64748b;
    flex: 1;
    min-height: 0;
    .email-log-empty {
      text-align: center;
      color: #94a3b8;
      padding: 20px 0;
      i {
        font-size: 32px;
        display: block;
        margin-bottom: 8px;
        opacity: 0.3;
      }
    }
    .email-logs-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      .stat-item {
        text-align: center;
        padding: 12px 8px;
        background: #f8fafc;
        border-radius: 10px;
        transition: all 0.3s;
        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .stat-value {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 4px;
          &.success { color: #22c55e; }
          &.warning { color: #f59e0b; }
          &.danger { color: #ef4444; }
          &.info { color: #6366f1; }
        }
        .stat-label {
          font-size: 11px;
          color: #64748b;
          font-weight: 500;
        }
      }
    }
  }
}

/* 邮箱进度条 */
.email-progress {
  flex-shrink: 0;
  padding: 16px 18px 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 40%, #e0f2fe 100%);
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 24px rgba(129, 140, 248, 0.35);
  .email-progress-title {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 12px;
  }
  .email-progress-detail {
    margin-top: 12px;
    font-size: 12px;
    color: #64748b;
    text-align: center;
  }
  ::v-deep .el-progress-bar__outer {
    background: #e2e8f0;
    border-radius: 6px;
  }
  ::v-deep .el-progress-bar__inner {
    background: #6366f1;
    border-radius: 6px;
  }
  ::v-deep .el-progress__text {
    font-weight: 600;
    color: #1e293b;
    font-size: 13px;
  }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter, .fade-leave-to { opacity: 0; }
</style>