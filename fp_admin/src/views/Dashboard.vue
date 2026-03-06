<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon users">
              <i class="el-icon-user"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.userCount }}</div>
              <div class="stat-label">用户总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon invoices">
              <i class="el-icon-document"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.invoiceCount }}</div>
              <div class="stat-label">发票总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon recognized">
              <i class="el-icon-success"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.recognizedCount }}</div>
              <div class="stat-label">已识别发票</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon amount">
              <i class="el-icon-coin"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">¥{{ stats.totalAmount }}</div>
              <div class="stat-label">发票总金额</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <div slot="header">
            <span>发票类型分布</span>
          </div>
          <div ref="pieChart" class="chart"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <div slot="header">
            <span>近 7 天发票趋势</span>
          </div>
          <div ref="lineChart" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getUserStats } from '@/api/user'
import { getInvoiceStats } from '@/api/invoice'

export default {
  name: 'Dashboard',
  data() {
    return {
      stats: {
        userCount: 0,
        invoiceCount: 0,
        recognizedCount: 0,
        totalAmount: 0
      },
      pieChart: null,
      lineChart: null
    }
  },
  
  mounted() {
    this.fetchStats()
    this.initCharts()
  },
  
  methods: {
    async fetchStats() {
      try {
        const [userRes, invoiceRes] = await Promise.all([
          getUserStats(),
          getInvoiceStats()
        ])
        
        if (userRes.success) {
          this.stats.userCount = userRes.data.total_users || 0
        }
        
        if (invoiceRes.success) {
          this.stats.invoiceCount = invoiceRes.data.total_invoices || 0
          this.stats.recognizedCount = invoiceRes.data.recognized_invoices || 0
          this.stats.totalAmount = (invoiceRes.data.total_amount || 0).toFixed(2)
        }
      } catch (error) {
        console.error('获取统计数据失败:', error)
      }
    },
    
    initCharts() {
      // 饼图 - 发票类型分布
      this.pieChart = echarts.init(this.$refs.pieChart)
      this.pieChart.setOption({
        tooltip: {
          trigger: 'item'
        },
        legend: {
          orient: 'vertical',
          left: 'left'
        },
        series: [
          {
            name: '发票类型',
            type: 'pie',
            radius: '50%',
            data: [
              { value: 1048, name: '增值税发票' },
              { value: 735, name: '普通发票' },
              { value: 580, name: '电子发票' },
              { value: 484, name: '其他' }
            ],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      })
      
      // 折线图 - 近 7 天趋势
      this.lineChart = echarts.init(this.$refs.lineChart)
      this.lineChart.setOption({
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '发票数量',
            type: 'line',
            areaStyle: {},
            emphasis: {
              focus: 'series'
            },
            data: [120, 132, 101, 134, 90, 230, 210]
          }
        ]
      })
      
      // 响应式调整
      window.addEventListener('resize', () => {
        this.pieChart.resize()
        this.lineChart.resize()
      })
    }
  }
}
</script>

<style scoped lang="scss">
.dashboard {
  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
      padding: 10px;
      
      .stat-icon {
        width: 60px;
        height: 60px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 30px;
        color: #fff;
        margin-right: 15px;
        
        &.users {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        &.invoices {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        &.recognized {
          background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        &.amount {
          background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
      }
      
      .stat-info {
        flex: 1;
        
        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #333;
        }
        
        .stat-label {
          font-size: 14px;
          color: #999;
          margin-top: 5px;
        }
      }
    }
  }
  
  .chart {
    width: 100%;
    height: 300px;
  }
}
</style>
