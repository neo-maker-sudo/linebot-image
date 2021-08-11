import os
import secrets
import time
import boto3
from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, ImageSendMessage, StickerMessage,
    FollowEvent, UnfollowEvent, AudioMessage
)


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"

db = SQLAlchemy(app)

s3 = boto3.client('s3',
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
                )
                
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))


bucket = "neo-linebot-image"

class User(db.Model):
    user_id = db.Column(db.String(100), nullable=False, primary_key=True)
    photos = db.relationship("Photo", back_populates="author", cascade="all")

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    author = db.relationship("User", back_populates="photos")

# compare request is from line offical and authenticate access token and secret
@app.route("/callback", methods=['POST'])
def callback():
    # get X-LINE-Signature header value (signature authentication)
    signature = request.headers['X-Line-Signature']

    # get requset body as text 
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
        
    return 'OK'


@handler.add(FollowEvent)
def handle_follow(event):
    user = User(
        user_id=event.source.user_id
    )
    db.session.add(user)
    db.session.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text="Welcome to Neo's lineBot testing char room"
    ))

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    if event.message.keywords == None:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="我無言"
            ))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=
                "1. " + event.message.keywords[0] + " " + \
                "2. " + event.message.keywords[1] + " " + \
                "3. " + event.message.keywords[2]
            ))


@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    curr = event.timestamp
    timeTemp = float(curr/1000)
    result = time.localtime(timeTemp)
    stadardTime = time.strftime("%H", result)
    if stadardTime > "21":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="夜深了，請小聲一點喔~~"
        ))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="哇! 真是美妙的聲音呢"
        ))
    

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    user = User.query.filter_by(user_id=event.source.user_id).first()
    db.session.delete(user)
    db.session.commit()

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    
    random_hex = secrets.token_hex(8)
    filename = random_hex + ".png"
    
    with open(filename, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    s3.upload_file(Bucket=bucket, Filename=filename, Key=filename)

    user = User.query.filter_by(user_id=event.source.user_id).first()

    photo = Photo(
        name="https://d13rqy4yzh3fb6.cloudfront.net/" + filename,
        author=user
    )

    db.session.add(photo)
    
    db.session.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Thank you for your image upload, already save your personal data"
    ))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == "回傳":
        photo = Photo.query.filter_by(user_id=event.source.user_id).order_by(Photo.id.desc()).first()
        if photo == None:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請先上傳圖片，謝謝。備註：如果之前有解除追蹤，照片會全數刪除，請重新上傳。"
            ))
        else:
            line_bot_api.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=photo.name,
                    preview_image_url=photo.name
            ))
    elif event.message.text == "時間":
        curr = event.timestamp
        timeTemp = float(curr/1000)
        result = time.localtime(timeTemp)
        stadardTime = time.strftime("%Y-%m-%d %H:%M:%S", result)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"現在時間為 : {stadardTime}"
            ))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text
        ))


if __name__ == '__main__':
    # db.create_all()
    app.run(port='8888')
