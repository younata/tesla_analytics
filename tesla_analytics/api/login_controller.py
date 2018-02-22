import bcrypt
from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_refresh_token_required, get_jwt_identity

from tesla_analytics.models import User

blueprint = Blueprint("LoginController", __name__)


@blueprint.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"error": "Must be JSON"}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)

    if not email:
        return jsonify({"error": "Missing required parameter 'email'"}), 400
    if not password:
        return jsonify({"error": "Missing required parameter 'password'"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Wrong email or password"}), 401

    if bcrypt.checkpw(password.encode("utf-8"), bytes(user.password_hash, "utf-8")):
        access_token = create_access_token(identity=email)
        refresh_token = create_refresh_token(identity=email)
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    return jsonify({"error": "Wrong email or password"}), 401


@blueprint.route('/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    current_user = get_jwt_identity()
    ret = {
        'access_token': create_access_token(identity=current_user)
    }
    return jsonify(ret), 200