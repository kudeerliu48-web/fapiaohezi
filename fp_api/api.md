## 接口指南
1、任务提交接口：http://14.103.188.30:1200/api/batches/processed-input
   参数：batch_id  #需要传递当条数据的ID
   files #需要上传的文件,webp格式
    返回数据：
    {
	"id": "153806283158691225",
	"created_at": "2026-03-05T01:26:20.839627",
	"status": "prepared",
	"input_mode": "processed_input",
	"pages": [
		{
			"id": "eb1e088b8da146808224c60191f62c6f",
			"batch_id": "153806283158691225",
			"doc_id": "1ee6d22c33e04921b18a05ac763ba963",
			"page_index": 1,
			"status": "prepared",
			"ocr_model": null,
			"llm_model": null,
			"total_time_ms": null,
			"total_tokens": 0,
			"thumb_url": "/data/pages/153806283158691225/eb1e088b8da146808224c60191f62c6f/thumb.webp",
			"input_url": "/data/pages/153806283158691225/eb1e088b8da146808224c60191f62c6f/input.png",
			"processed_url": "/data/pages/153806283158691225/eb1e088b8da146808224c60191f62c6f/processed.webp",
			"manifest_url": "/data/pages/153806283158691225/eb1e088b8da146808224c60191f62c6f/manifest.json",
			"small_text": true,
			"amount_mismatch": false
		}
	]
}


2、开始任务的接口：http://14.103.188.30:1200/api/batches/test-batch-002/run  #post请求
    #test-batch-002  就是batch_id
3、任务结果查询接口：http://14.103.188.30:1200/api/batches/test-batch-002/final-output      #get请求

    返回数据：
    {
	"batch_id": "153806283158691225",
	"status": "completed",
	"input_mode": "processed_input",
	"total_pages": 1,
	"completed_pages": 1,
	"failed_pages": 0,
	"results": [
		{
			"page_id": "eb1e088b8da146808224c60191f62c6f",
			"page_index": 1,
			"status": "completed",
			"ocr_model": "qwen-ocr",
			"llm_model": "skipped",
			"total_time_ms": 25045,
			"total_tokens": 3982,
			"result_json": {
				"invoice_type": "电子发票（普通发票）",
				"invoice_code": null,
				"invoice_number": "26427000000145891963",
				"date": "2026-01-08",
				"buyer_name": "安徽燕之坊食品有限公司",
				"buyer_tax_id": "91340100728526312J",
				"buyer_address_phone": null,
				"buyer_bank_account": null,
				"seller_name": "中国石化销售股份有限公司湖北武汉石油分公司",
				"seller_tax_id": "914201006791228986",
				"seller_address_phone": null,
				"seller_bank_account": null,
				"items": [
					{
						"item_name": "乙醇汽油*92号车用乙醇汽油(E10)(VIB)",
						"specification": "92号",
						"unit": "升",
						"quantity": "27.70780856",
						"unit_price": "7.02653909",
						"amount": "194.69",
						"tax_rate": "13%",
						"tax_amount": "25.31",
						"name": "乙醇汽油*92号车用乙醇汽油(E10)(VIB)"
					}
				],
				"total_amount": "194.69",
				"total_tax": "25.31",
				"total_amount_in_words": "贰佰贰拾圆整",
				"total_amount_in_figures": "220.00",
				"payee": "熊静",
				"reviewer": "谌皋",
				"drawer": "陈钢",
				"remarks": null,
				"service_name": "乙醇汽油*92号车用乙醇汽油(E10)(VIB)"
			},
			"validate_message": "金额校验通过；格式告警: seller_tax_id；已修复 1 处"
		}
	]
}
