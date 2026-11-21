from flask import jsonify


def ok(data):
    return jsonify(data=data)
