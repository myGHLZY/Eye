from flask import Blueprint, request
from werkzeug.exceptions import RequestEntityTooLarge

from app.service.point_cloud import (
    MAX_FILE_BYTES, PointCloudError, PointCloudLimitError, UnsupportedPointCloudFormat, preview_point_cloud,
)
from app.util.response import error_response, ok

blueprint = Blueprint("point_cloud", __name__, url_prefix="/api/point-clouds")


@blueprint.post("/preview")
def point_cloud_preview():
    request.max_content_length = MAX_FILE_BYTES + 64 * 1024
    request.max_form_parts = 2
    try:
        files = request.files.getlist("file")
        if len(files) != 1 or not files[0].filename:
            return error_response(400, "POINT_CLOUD_FILE_REQUIRED", "请上传一个点云文件。")
        file = files[0]
        result = preview_point_cloud(file.stream, file.filename)
    except RequestEntityTooLarge:
        return error_response(413, "POINT_CLOUD_TOO_LARGE", "单个点云文件最多支持 128 MiB。")
    except PointCloudLimitError as error:
        return error_response(413, "POINT_CLOUD_TOO_LARGE", str(error))
    except UnsupportedPointCloudFormat as error:
        return error_response(415, "UNSUPPORTED_POINT_CLOUD_FORMAT", str(error))
    except PointCloudError as error:
        return error_response(400, "INVALID_POINT_CLOUD", str(error))
    response = ok(result)
    response.headers["Cache-Control"] = "no-store"
    return response
