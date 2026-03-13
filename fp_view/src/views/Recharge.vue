<template>
  <div class="recharge-page">
    <div class="page-header">
      <h1 class="page-title">会员充值</h1>
      <p class="page-desc">选择支付方式后，请使用对应 App 扫码完成支付</p>
    </div>

    <el-card class="recharge-card" shadow="hover">
      <div class="pay-method-tabs">
        <div
          v-for="item in payMethods"
          :key="item.key"
          :class="['tab-item', { active: currentMethod === item.key }]"
          @click="currentMethod = item.key"
        >
          <i :class="item.icon" class="tab-icon" />
          <span>{{ item.label }}</span>
        </div>
      </div>

      <div class="qr-section">
        <div class="qr-wrapper">
          <div class="qr-placeholder">
            <i :class="currentMethod === 'wechat' ? 'el-icon-chat-dot-round' : 'el-icon-wallet'" class="qr-icon" />
            <span class="qr-hint">请使用{{ currentMethod === 'wechat' ? '微信' : '支付宝' }}扫码支付</span>
            <div class="qr-fake">
              <div class="qr-grid" aria-hidden="true">
                <span v-for="n in 64" :key="n" class="qr-cell" />
              </div>
            </div>
            <p class="qr-note">支付完成后将自动开通/续期会员</p>
          </div>
        </div>
      </div>

      <div class="amount-tips">
        <i class="el-icon-info" />
        <span>当前为展示页面，未对接支付接口。实际金额与到账以接入支付后为准。</span>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'Recharge',
  data() {
    return {
      currentMethod: 'wechat',
      payMethods: [
        { key: 'wechat', label: '微信支付', icon: 'el-icon-chat-dot-round' },
        { key: 'alipay', label: '支付宝', icon: 'el-icon-wallet' },
      ],
    }
  },
}
</script>

<style lang="scss" scoped>
$primary: #4f46e5;
$primary-light: #818cf8;
$text: #1e293b;
$text-light: #64748b;

.recharge-page {
  max-width: 520px;
  margin: 0 auto;
  padding: 20px 0;
}

.page-header {
  margin-bottom: 24px;
  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: $text;
    margin: 0 0 8px 0;
  }
  .page-desc {
    font-size: 14px;
    color: $text-light;
    margin: 0;
  }
}

.recharge-card {
  border-radius: 16px;
  overflow: hidden;
  padding: 24px;
}

.pay-method-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 28px;

  .tab-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 14px 20px;
    border-radius: 12px;
    border: 2px solid #e2e8f0;
    background: #f8fafc;
    color: $text-light;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;

    .tab-icon {
      font-size: 22px;
    }

    &:hover {
      border-color: $primary-light;
      color: $primary;
      background: rgba($primary, 0.06);
    }

    &.active {
      border-color: $primary;
      background: linear-gradient(135deg, rgba($primary, 0.12) 0%, rgba($primary-light, 0.08) 100%);
      color: $primary;
    }
  }
}

.qr-section {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.qr-wrapper {
  background: #fff;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  padding: 28px;
  text-align: center;
}

.qr-placeholder {
  .qr-icon {
    display: block;
    font-size: 48px;
    color: #cbd5e1;
    margin-bottom: 12px;
  }

  .qr-hint {
    display: block;
    font-size: 15px;
    color: $text;
    font-weight: 600;
    margin-bottom: 20px;
  }

  .qr-fake {
    display: inline-block;
    padding: 16px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-bottom: 16px;
  }

  .qr-grid {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    grid-template-rows: repeat(8, 1fr);
    gap: 2px;
    width: 160px;
    height: 160px;
  }

  .qr-cell {
    background: #1e293b;
    border-radius: 1px;
    min-width: 0;
    min-height: 0;
  }

  .qr-cell:nth-child(4n + 1),
  .qr-cell:nth-child(4n + 3) {
    background: #f1f5f9;
  }

  .qr-note {
    font-size: 13px;
    color: $text-light;
    margin: 0;
  }
}

.amount-tips {
  margin-top: 24px;
  padding: 12px 16px;
  background: #f0f9ff;
  border-radius: 10px;
  font-size: 13px;
  color: #0369a1;
  display: flex;
  align-items: flex-start;
  gap: 8px;

  i {
    margin-top: 2px;
    flex-shrink: 0;
  }
}
</style>
