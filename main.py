from re import A
from flask import Flask, request, abort

from linebot import (
	LineBotApi, WebhookHandler
)
from linebot.exceptions import (
	InvalidSignatureError
)
from linebot.models import (
	MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, VideoSendMessage, StickerSendMessage, AudioSendMessage, TemplateSendMessage, ButtonsTemplate, DatetimePickerTemplateAction, PostbackAction, MessageAction, URIAction, FollowEvent, PostbackTemplateAction, PostbackEvent
)

import os
import datetime
import time
import MySQLdb
from dotenv import load_dotenv
import schedule

app = Flask(__name__)

conn = None

#環境変数取得
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
REMOTE_HOST = os.environ["REMOTE_HOST"]
REMOTE_DB_NAME = os.environ["REMOTE_DB_NAME"]
REMOTE_DB_USER = os.environ["REMOTE_DB_USER"]
REMOTE_DB_PASS = os.environ["REMOTE_DB_PASS"]
REMOTE_DB_TB = os.environ["REMOTE_DB_TB"]

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=['POST'])
def callback():
	# get X-Line-Signature header value
	signature = request.headers['X-Line-Signature']

	# get request body as text
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)

	# handle webhook body
	try:
		handler.handle(body, signature)

	except InvalidSignatureError:
		abort(400)

	return 'OK'

# ボタンの入力を受け取って今まで登録したことがなければinsertして、登録してあればupdateする
@handler.add(PostbackEvent)
def on_postback(event):
	# reply_token = event.reply_token
	event_user_id = event.source.user_id
	profiles = line_bot_api.get_profile(event_user_id)
	event_display_name = profiles.display_name
	input_alarm_time = event.postback.params['time']

	# DBへの保存
	try:
		conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME)
		c = conn.cursor()
		sql = "SELECT * FROM "+REMOTE_DB_TB+" WHERE user_id = '"+event_user_id+"'"
		c.execute(sql)
		ret = c.fetchall()
		if len(ret) == 0:
			attribute = 0
			sql2 = "INSERT INTO "+REMOTE_DB_TB+" VALUES ('"+event_user_id+"', '"+event_display_name+"', '"+input_alarm_time+"', "+str(attribute)+")"
		elif len(ret) == 1:
			sql2 = "UPDATE "+REMOTE_DB_TB+" SET display_name = '"+event_display_name+"', alarm_time = '"+input_alarm_time+"' WHERE user_id = '"+event_user_id+"'"
		c.execute(sql2)
		conn.commit()
		conn.close()
		line_bot_api.push_message(
			to=event_user_id,
			messages=TextSendMessage(text=input_alarm_time + 'に起こすわよ！さっさと寝なさいよ！')
		)
		while True:
			dt = datetime.datetime.now().time()#現在時刻の取得
			now=dt.strftime('%H:%M')
			if now == input_alarm_time:
				line_bot_api.push_message(
					to=event_user_id,
					messages=TextSendMessage(text=input_alarm_time + "よ！早く起きなさい！")
				),
				time.sleep
				break
			time.sleep(1)

	except:
		line_bot_api.push_message(
			to=event_user_id,
			messages=TextSendMessage(text='なんかミスってるよ')
		)

#handle_nessageから呼ばれる
#時間選択アクションを起こす
def make_button():
	message_template = TemplateSendMessage(
		alt_text="アラーム",
		template=ButtonsTemplate(
			text="アラームを設定してください",
			title="アラームを設定",
			image_size="cover",
			thumbnail_image_url="https://i-ogp.pximg.net/c/1200x630_80_a2_g2_u1/img-master/img/2016/05/24/00/00/12/57033368_p0_master1200.jpg",
			actions=[
				DatetimePickerTemplateAction(
					label='time_select',
					data='action=buy&itemid=1',
					mode='time',
					initial='00:00',
					min='00:00',
					max='23:59'
				)
			]
		)
	)
	return message_template

#メッセージが入力されたら
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
	# 基本的にここにコードを書いていきます。
	messages = make_button()
	line_bot_api.reply_message(
		event.reply_token,
		messages
	)

if __name__ == "__main__":
#    app.run()
	port = int(os.getenv("PORT", 5000))
	app.run(host="0.0.0.0", port=port)
