<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style lang="scss">
	/*每个页面公共 css*/
	page {
		background-color: #f5f5f5;
		font-size: 14px;
		line-height: 1.5;
	}
	
	view, text {
		box-sizing: border-box;
	}
	
	/* 通用样式 */
	.container {
		padding: 20rpx;
	}
	
	.card {
		background: #fff;
		border-radius: 16rpx;
		padding: 30rpx;
		margin: 20rpx;
		box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
	}
	
	.btn-primary {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: #fff;
		border: none;
		border-radius: 50rpx;
		font-size: 32rpx;
		padding: 24rpx 48rpx;
	}
</style>
