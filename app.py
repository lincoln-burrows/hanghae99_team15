import os
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from bson import ObjectId

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"
# app.config['UPLOAD_FOLDER'] = "./static/img"

SECRET_KEY = 'SPARTA'


from pymongo import MongoClient
client = MongoClient('mongodb+srv://test:sparta@cluster0.82bho.mongodb.net/Cluster0?retryWrites=true&w=majority')
db = client.dbsparta


@app.route('/')
def home():
    # 쿠키로 부터 토큰 가져오기
    token_receive = request.cookies.get('mytoken')
    # 토큰을 받은 뒤 아래 기능을 수행합니다.
    try:
        # jw토큰 로그인 정보 디코드
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # 현재 로그인 된 id와 일치하는 정보 가져오기
        user_info = db.users.find_one({"username": payload["id"]})
        posts = list(db.posts.find({}))
        # DB에서 가져온 자료를 user.html 페이지에 user_info, posts, status 로 전달
        # 페이지 렌더링, db에서 가져온 로그인 정보, 영화 정보 index 페이지로 전달
        return render_template('index.html', user_info=user_info, posts=posts)
    except jwt.ExpiredSignatureError:

        # 토큰 시간이 완료되면 로그인 페이지로 보냄 msg - 시간이 만료 되었습니다.
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:

        # 토큰이 존재하지 않다면 로그인 페이지로 보냄 msg - 정보가 존재하지 않습니다.
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# login 페이지
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


# login server
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    # hash 값 생성
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    # username = db.users.find_one({"username": username_receive}, {"_id": False})
    # nickname = username["nickname"]
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 회원가입
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지 추가(전종민 2021-11-05)
        "nickname": nickname_receive
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


# 아이디 중복확인 서버
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# 닉네임 중복확인 서버
@app.route('/sign_up/check_name_dup', methods=['POST'])
def check_name_dup():
    nickname_receive = request.form['nickname_give']
    exists = bool(db.users.find_one({"nickname": nickname_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# DB에 정보 삽입
@app.route('/posting', methods=['POST'])
def posting():
    # 토근 받기
    token_receive = request.cookies.get('mytoken')
    # jwt 토큰이 유효한지 확인
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # 오늘 날짜
    today = datetime.now()
    # 현재 날씨 및 시간
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    # POST 방식으로 전달되는 데이터 받기
    title_receive = request.form["title_give"]
    comment_receive = request.form["comment_give"]
    file = request.files["file_give"]

    # username 하나씩 찾기
    user_info = db.users.find_one({"username": payload["id"]})
    nickname = user_info["nickname"]
    username = user_info["username"]

    # 파일명을 '.' 기준으로 뒤쪽만 받기
    extension = file.filename.split(".")[-1]

    # 파일명 뒤에 현재 날짜 및 시간 붙이기
    filename = f"file - {mytime}"
    # 파일명 뒤에 확장자 넣기
    save_to = f"static/img/{filename}.{extension}"
    # 파일 저장
    file.save(save_to)

    # 문서 생성
    doc = {
        'img_file': f"{filename}.{extension}",
        'nickname': nickname,
        'username': username,
        'title': title_receive,
        'comment': comment_receive
    }
    # 문서 삽입
    db.posts.insert_one(doc)
    # 요청 성공 시 실행되는 메세지
    return jsonify({'msg': '등록 완료!'})

# 포스팅 요청 API
@app.route("/get_posts", methods=['GET'])
def get_posts():
    # 토큰 받기
    token_receive = request.cookies.get('mytoken')
    # 토큰을 받은 뒤 아래 기능을 수행합니다.
    try:
        # jwt 토큰이 유효한지 확인
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 포스팅 목록 받아오기
        posts = list(db.posts.find({}))
        for post in posts:
            # 문자열로 변경
            post["_id"] = str(post["_id"])
        # 성공 시 실행되는 메세지
        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", 'posts': posts})
    # 예외처리하기
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # url 재전송하기
        return redirect(url_for("home"))


# 포스팅 삭제
@app.route("/deleteCard", methods=["DELETE"])
def delete_card():
    # 토큰을 받습니다.
    token_receive = request.cookies.get('mytoken')
    # jwt토큰이 유효한지 확인
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    # db에서 username 하나씩 찾기
    user_info = db.users.find_one({"username": payload["id"]})
    # username 변수 선언
    username = user_info["username"]

    # 변수 전달
    id_value_receive = request.form["id_value_give"]
    # db posts에서 하나씩 찾기
    author_info = db.posts.find_one({"_id": ObjectId(id_value_receive)})
    # id 변수 선언
    author_id = author_info["username"]
    # 파일 이름 변수 선언
    file_name = author_info["img_file"]

    # username과 author_id가 같다면 ObjectId를 이용하여 file 삭제 그렇지 않다면 경고창
    if username == author_id:
        # 조건 만족시 삭제
        db.posts.delete_one({"_id": ObjectId(id_value_receive)})
        # 조건 만족시 이미지 파일 삭제
        os.remove("static/img/" + file_name)
        # 조건 만족시 메시지 리턴
        return jsonify({"msg": "삭제완료!"})
    else:
        # 조건 불충시 메세지 리턴
        return jsonify({"msg": "삭제 권한이 없습니다."})


# 프로필 확인 기능 - index.html 메인 페이지에서 개인 프로필로 페이지 이동 href="/user/{{ user_info.username }}"
@app.route('/user/<username>')
def user(username):
    # 토큰을 받습니다.
    token_receive = request.cookies.get('mytoken')
    # 토큰을 받은 뒤 아래 기능을 수행합니다.
    try:
        # jwt 토큰이 유효한지 확인
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        status = (username == payload["id"])
        # DB에서 users - username 을 찾고 posts 에서 포스팅할 내용을 리스트로 저장
        user_info = db.users.find_one({"username": username}, {"_id": False})
        posts = list(db.posts.find({"username": username}))
        # DB에서 가져온 자료를 user.html 페이지에 user_info, posts, status 로 전달
        return render_template('user.html', user_info=user_info, posts=posts, status=status)
    # jwt 토큰이 유효하지 않을 때.
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # home으로 돌아감.
        return redirect(url_for("home"))


# 프로필 수정 서버
@app.route('/update_profile', methods=['POST'])
def save_img():
    # 토큰을 받습니다.
    token_receive = request.cookies.get('mytoken')
    # 토큰을 받은 뒤 아래 기능을 수행합니다.
    try:
        # jwt 토큰이 유효한지 확인
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # python 기본 함수인 datetime 을 사용해 저장되는 file 에 붙여 파일을 구분
        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

        # user.html 페이지에서 user.js - update_profile()을 수행 후 받아온 결과를 저장
        # username 을 저장하여 받아온 file의 파일명 username으로 저장하도록 설정
        username = payload["id"]
        name_receive = request.form["name_give"]
        about_receive = request.form["about_give"]
        # 변경하기위해 받아온 nickname 과 profile_info를 db에 저장
        new_doc = {
            "nickname": name_receive,
            "profile_info": about_receive
        }
        # 받은 파일이 있을 시 아래 기능을 수행
        if 'file_give' in request.files:
            # 전달받은 파일을 file 에 저장
            file = request.files["file_give"]
            # 업로드 된 파일이 안전한지 확인
            filename = secure_filename(file.filename)
            # filename에서 . 없이 확장자만 추출
            extension = filename.split(".")[-1]
            # filename에 datetime으로 만든 시간 추가
            filename = f"file - {mytime}"
            # file 저장 경로 지정
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/" + file_path)
            # profile 사진의 이름과 경로를 doc에 저장
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({'username': payload['id']}, {'$set': new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    # jwt 토큰이 유효하지 않을 때.
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # home으로 돌아감
        return redirect(url_for("home"))

# @app.route('/update_post', methods=['POST'])
# def save_post():
#     # 토큰을 받습니다.
#     token_receive = request.cookies.get('mytoken')
#     # 토큰을 받은 뒤 아래 기능을 수행합니다.
#     try:
#         # jwt 토큰이 유효한지 확인
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#
#         # python 기본 함수인 datetime 을 사용해 저장되는 file 에 붙여 파일을 구분
#         today = datetime.now()
#         mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
#
#         # user.html 페이지에서 user.js - update_profile()을 수행 후 받아온 결과를 저장
#         # username 을 저장하여 받아온 file의 파일명 username으로 저장하도록 설정
#         username = payload["id"]
#         title_receive = request.form["title_give"]
#         comment_receive = request.form["comment_give"]
#         # 변경하기위해 받아온 nickname 과 profile_info를 db에 저장
#         new_doc = {
#             "title": title_receive,
#             "comment": comment_receive
#         }
#         # 받은 파일이 있을 시 아래 기능을 수행
#         if 'file_give' in request.files:
#             # 전달받은 파일을 file 에 저장
#             file = request.files["file_give"]
#             extension = file.filename.split(".")[-1]
#
#             # 파일명 뒤에 현재 날짜 및 시간 붙이기
#             filename = f"file - {mytime}"
#             # 파일명 뒤에 확장자 넣기
#             save_to = f"static/img/{filename}.{extension}"
#             # 파일 저장
#             file.save(save_to)
#             # file 저장 경로 지정
#             file_path = f"img/{username}.{extension}"
#             file.save("./static/" + file_path)
#             # profile 사진의 이름과 경로를 doc에 저장
#             new_doc["img"] = filename
#             new_doc["img_file"] = file_path
#         db.posts.update_one({'username': payload['id']}, {'$set': new_doc})
#         return jsonify({"result": "success", 'msg': '수정완료'})
#     # jwt 토큰이 유효하지 않을 때.
#     except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
#         # home으로 돌아감
#         return redirect(url_for("home"))

@app.route('/update_like', methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 좋아요 수 변경
        user_info = db.users.find_one({"username": payload["id"]})
        post_id_receive = request.form["post_id_give"]
        type_receive = request.form["type_give"]
        action_receive = request.form["action_give"]
        doc = {
            "post_id": post_id_receive,
            "username": user_info["username"],
            "type": type_receive
        }
        if action_receive == "like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents({"post_id": post_id_receive, "type": type_receive})
        return jsonify({"result": "success", 'msg': 'updated', "count": count})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)